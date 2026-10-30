"""Differential check on generated inputs (standard library only).

Oracle   : the ORIGINAL code running on the OLD library version.
Candidate: the PATCHED code running on the NEW (and also the OLD) library version.

Inputs are mutated from seed probes with a seeded PRNG, so a run is reproducible and costs no model tokens.
Two tiers:
  core - numbers stay inside the value range seen in the seeds; any divergence fails the check.
  wide - numbers may leave that range; divergences are only reported, because out-of-contract
         inputs (for example 300 in a uint8 array) can legitimately differ between versions.
Probes where the oracle itself raised are skipped (undefined behavior, nothing to preserve).

Generator versions: a case folder may carry "gen": 2 in case.json (written by make_case from 2026-10-29 on). Version 2 adds
  - aligned lists: list fields of one object that have the same length are changed together (same row dropped,
    duplicated, reversed or truncated in every column), so a table given as columns stays a table;
  - date-aware strings: ISO dates and timestamps stay valid (shifted by a random amount, same format), and a whole
    column can get fractional seconds of 3, 6 or 9 digits (milliseconds to nanoseconds).
Without the key the behavior is exactly the earlier one, so recorded runs stay reproducible.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import random
import re
import sys
from pathlib import Path

from patchpilot import sandbox

TOKEN = re.compile(r"\d+|\D+")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:([ T])(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?)?$")
FRAC_WIDTHS = (3, 6, 9)
# Kept small on purpose: a wide integer can land in a size parameter (count, range) and a huge one
# would exhaust memory, which this local runner cannot limit.
WIDE_INTS = [0, 1, -1, 255, 256, 65535, 65536]
MIN_VALID = 20  # fewer valid probes than this -> verdict WEAK (check too thin to trust)


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Gen:
    def __init__(self, seeds: list, seed: int, v2: bool = False):
        self.rng = random.Random(seed)
        self.v2 = v2
        self.leaves: dict = {}  # path -> numbers and strings seen there
        self.elems: dict = {}   # list path -> elements seen there (any type)
        self.maxlen: dict = {}  # list path -> longest list seen
        self.tier = "core"
        for s in seeds:
            self._index(s, "")
        # A path can hold mixed types (rows like ["a", 1]); ranges use its numbers, string pools use its strings.
        self.ranges = {}
        for p, vs in self.leaves.items():
            nums = [x for x in vs if _num(x)]
            if nums:
                self.ranges[p] = (min(nums), max(nums))

    def _index(self, v, path: str) -> None:
        if isinstance(v, dict):
            for k, x in v.items():
                self._index(x, f"{path}.{k}")
        elif isinstance(v, list):
            p = path + "[]"
            self.maxlen[p] = max(self.maxlen.get(p, 0), len(v))
            for x in v:
                self.elems.setdefault(p, []).append(x)
                self._index(x, p)
        elif _num(v) or isinstance(v, str):
            self.leaves.setdefault(path, []).append(v)

    def mut(self, v, path: str):
        r = self.rng
        if isinstance(v, bool):
            return v if r.random() < 0.8 else not v
        if _num(v):
            return self.mut_num(v, path)
        if isinstance(v, str):
            return self.mut_str(v, path)
        if isinstance(v, dict):
            if self.v2:
                keys = [k for k, x in v.items() if isinstance(x, list)]
                if len(keys) >= 2 and len({len(v[k]) for k in keys}) == 1 and len(v[keys[0]]) > 0:
                    return self.mut_aligned(v, path, keys)
            return {k: (self.mut(x, f"{path}.{k}") if r.random() < 0.6 else x) for k, x in v.items()}
        if isinstance(v, list):
            return self.mut_list(v, path + "[]")
        return v

    # ---- generator v2 ----
    def parse_date(self, s):
        m = DATE_RE.match(s) if isinstance(s, str) else None
        if not m:
            return None
        y, mo, d, sep, hh, mi, ss, frac = m.groups()
        try:
            dt = _dt.datetime(int(y), int(mo), int(d), int(hh or 0), int(mi or 0), int(ss or 0))
        except ValueError:
            return None
        return dt, sep, hh is not None, frac

    def fmt_date(self, dt, sep, has_time, frac):
        s = dt.strftime("%Y-%m-%d")
        if has_time:
            s += (sep or " ") + dt.strftime("%H:%M:%S")
            if frac:
                s += "." + frac
        return s

    def rand_digits(self, k: int) -> str:
        return "".join(self.rng.choice("0123456789") for _ in range(k))

    def jitter_date(self, s: str) -> str:
        p = self.parse_date(s)
        if p is None:
            return s
        dt, sep, has_time, frac = p
        r = self.rng
        if has_time:
            dt = dt + _dt.timedelta(seconds=r.randint(-1, 1) * r.choice([1, 60, 3600, 86400, 86400 * 30]))
        else:
            dt = dt + _dt.timedelta(days=r.randint(-30, 30))
        return self.fmt_date(dt, sep, has_time, frac)

    def with_frac(self, s: str, width: int) -> str:
        p = self.parse_date(s)
        if p is None:
            return s
        dt, sep, has_time, _ = p
        return self.fmt_date(dt, sep or " ", True, self.rand_digits(width))

    def mut_aligned(self, d: dict, path: str, keys: list):
        r = self.rng
        cols = {k: list(d[k]) for k in keys}
        cap = max(32, max(self.maxlen.get(f"{path}.{k}[]", 0) for k in keys))
        for _ in range(r.randint(1, 2)):
            n = len(cols[keys[0]])
            op = r.choice(["mutate", "mutate", "mutate", "drop", "dup", "reverse", "grow", "trunc", "single",
                           "datefrac", "datefrac"])
            if op == "mutate":
                for k in keys:
                    cols[k] = [self.mut(x, f"{path}.{k}[]") if r.random() < 0.5 else x for x in cols[k]]
            elif op == "drop" and n > 1:
                i = r.randrange(n)
                cols = {k: c[:i] + c[i + 1:] for k, c in cols.items()}
            elif op == "dup" and n and n < cap:
                i, j = r.randrange(n), r.randrange(n + 1)
                cols = {k: c[:j] + [c[i]] + c[j:] for k, c in cols.items()}
            elif op == "reverse":
                cols = {k: c[::-1] for k, c in cols.items()}
            elif op == "grow" and n < cap:
                for k in keys:
                    pool = self.elems.get(f"{path}.{k}[]") or cols[k]
                    cols[k] = cols[k] + [self.mut(r.choice(pool), f"{path}.{k}[]")]
            elif op == "trunc" and n > 1:
                m = r.randint(1, n)
                cols = {k: c[:m] for k, c in cols.items()}
            elif op == "single" and n:
                i = r.randrange(n)
                cols = {k: [c[i]] for k, c in cols.items()}
            elif op == "datefrac":
                w = r.choice(FRAC_WIDTHS)
                for k in keys:
                    if cols[k] and all(self.parse_date(x) is not None for x in cols[k]):
                        cols[k] = [self.with_frac(x, w) for x in cols[k]]
        return {k: (cols[k] if k in cols else (self.mut(x, f"{path}.{k}") if r.random() < 0.6 else x))
                for k, x in d.items()}

    def mut_num(self, v, path: str):
        r = self.rng
        lo, hi = self.ranges.get(path, (v, v))
        if self.tier == "wide" and isinstance(v, int) and r.random() < 0.7:
            return r.choice(WIDE_INTS + [hi * 10 ** r.randint(1, 2)])
        pick = r.random()
        if isinstance(v, float):
            return r.choice([lo, hi, round(r.uniform(lo, hi), 6)])
        zero = [0] if lo > 0 else []
        ilo, ihi = math.ceil(lo), math.floor(hi)  # a field seen as int and as float has float bounds
        cands = [lo, hi, r.randint(ilo, ihi) if ilo <= ihi else v, min(hi, v + 1), max(lo, v - 1)] + zero
        return r.choice(cands) if pick < 0.9 else v

    def mut_str(self, v: str, path: str):
        r = self.rng
        if self.v2 and self.parse_date(v) is not None:
            return self.jitter_date(v)
        pool = [x for x in self.leaves.get(path, []) if isinstance(x, str)] or [v]
        c = r.random()
        if c < 0.35:
            return self.cross(v, r.choice(pool))
        if c < 0.8:
            return self.digits(v)
        return r.choice(pool)

    def cross(self, a: str, b: str) -> str:
        ta, tb = TOKEN.findall(a), TOKEN.findall(b)
        n = self.rng.choice([len(ta), len(tb)])
        out = []
        for i in range(n):
            cands = [t[i] for t in (ta, tb) if i < len(t)]
            cands = [t for t in cands if t.isdigit() == cands[0].isdigit()]
            out.append(self.rng.choice(cands))
        return "".join(out)

    def digits(self, s: str) -> str:
        toks = TOKEN.findall(s)
        idx = [i for i, t in enumerate(toks) if t.isdigit()]
        if not idx:
            return s
        i = self.rng.choice(idx)
        t = toks[i]
        mode = self.rng.choice(["rand", "zeros", "nines", "inc", "dec"])
        if mode == "rand":
            new = "".join(self.rng.choice("0123456789") for _ in t)
        elif mode == "zeros":
            new = "0" * len(t)
        elif mode == "nines":
            new = "9" * len(t)
        elif mode == "inc":
            new = str(int(t) + 1).zfill(len(t))
        else:
            new = str(max(0, int(t) - 1)).zfill(len(t))
        toks[i] = new
        return "".join(toks)

    def mut_list(self, v: list, path: str):
        r = self.rng
        out = list(v)
        cap = max(32, self.maxlen.get(path, 0))
        for _ in range(r.randint(1, 2)):
            op = r.choice(["mutate", "mutate", "drop", "dup", "shuffle", "grow", "trunc", "single", "empty"])
            if op == "mutate":
                out = [self.mut(x, path) if r.random() < 0.5 else x for x in out]
            elif op == "drop" and out:
                out.pop(r.randrange(len(out)))
            elif op == "dup" and out and len(out) < cap:
                out.insert(r.randrange(len(out) + 1), r.choice(out))
            elif op == "shuffle" and len({type(x) for x in out}) <= 1:  # never swap fields of a mixed row
                r.shuffle(out)
            elif op == "grow" and len(out) < cap and self.elems.get(path):
                out.append(self.mut(r.choice(self.elems[path]), path))
            elif op == "trunc" and out:
                out = out[: r.randint(0, len(out))]
            elif op == "single" and out:
                out = [r.choice(out)]
            elif op == "empty" and r.random() < 0.3:
                out = []
        return out


def generate(seeds: list, n: int = 200, seed: int = 0, wide_frac: float = 0.25, v2: bool = False) -> list:
    g = Gen(seeds, seed, v2)
    seen = {json.dumps(s, sort_keys=True) for s in seeds}
    out: list = []
    tries = 0
    while len(out) < n and tries < n * 30:
        tries += 1
        g.tier = "wide" if g.rng.random() < wide_frac else "core"
        p = g.mut(g.rng.choice(seeds), "")
        k = json.dumps(p, sort_keys=True)
        if k in seen:
            continue
        seen.add(k)
        out.append({"tier": g.tier, "probe": p})
    return out


def _run(case_dir: Path, files: dict | None, python, probes: list, timeout_s: float = 120):
    ws = sandbox.workspace(case_dir, exclude=sandbox.ANSWER_KEYS + (sandbox.HIDDEN_INPUTS,))
    try:
        for rel, content in (files or {}).items():
            (ws / rel).write_text(content)
        (ws / "gen_inputs.json").write_text(json.dumps(probes))
        r = sandbox.run(python, ["run_case.py", "gen_inputs.json"], ws, timeout_s=timeout_s)
    finally:
        sandbox.cleanup(ws)
    if r.returncode != 0:
        return None, f"exit {r.returncode}: {r.stderr[-300:]}"
    try:
        res = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None, "output is not JSON"
    if not isinstance(res, list) or len(res) != len(probes):
        return None, "output length mismatch"
    return res, ""


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def differential(case_dir, old_py, new_py, patched_files: dict | None = None, *, n: int = 200,
                 seed: int = 0, seed_files=("inputs.json", "hidden_inputs.json"), gen: int | None = None) -> dict:
    case_dir = Path(case_dir)
    seeds: list = []
    for name in seed_files:
        p = case_dir / name
        if p.exists():
            seeds.extend(json.loads(p.read_text()))
    if not seeds:
        return {"verdict": "RUN_ERROR", "reason": "no seed inputs"}
    gen_v = 1
    cj = case_dir / "case.json"
    if cj.exists():
        try:
            gen_v = int(json.loads(cj.read_text()).get("gen", 1))
        except (ValueError, TypeError, AttributeError):
            gen_v = 1
    if gen is not None:
        gen_v = gen
    gen = generate(seeds, n=n, seed=seed, v2=gen_v >= 2)
    probes = [g["probe"] for g in gen]

    # Core and wide probes run in separate processes: a wide probe that hangs or crashes must not
    # take the core verdict down with it (wide results are informational only).
    valid = core_div = wide_div = 0
    examples: list = []
    wide_error = ""
    for tier, timeout_s in (("core", 120), ("wide", 30)):
        part = [g for g in gen if g["tier"] == tier]
        if not part:
            continue
        pr = [g["probe"] for g in part]
        oracle, e0 = _run(case_dir, None, old_py, pr, timeout_s)
        cand_new, e1 = _run(case_dir, patched_files, new_py, pr, timeout_s)
        cand_old, e2 = _run(case_dir, patched_files, old_py, pr, timeout_s)
        if oracle is None or cand_new is None or cand_old is None:
            if tier == "core":
                return {"verdict": "RUN_ERROR", "reason": e0 or e1 or e2, "generated": len(probes)}
            wide_error = e0 or e1 or e2
            continue
        for i, g in enumerate(part):
            o = oracle[i]
            if isinstance(o, dict) and "error" in o:
                continue
            if tier == "core":
                valid += 1
            for where, got in (("patched@new", cand_new[i]), ("patched@old", cand_old[i])):
                if _same(got, o):
                    continue
                if tier == "core":
                    core_div += 1
                else:
                    wide_div += 1
                examples.append({"tier": tier, "where": where, "probe": g["probe"], "expected": o, "got": got})
    examples.sort(key=lambda e: (e["tier"] != "core", len(json.dumps(e["probe"]))))
    verdict = "DIVERGENCE" if core_div else ("WEAK" if valid < MIN_VALID else "PASS")
    return {"verdict": verdict, "generated": len(probes), "valid": valid,
            "skipped_oracle_error": sum(g["tier"] == "core" for g in gen) - valid, "core_divergences": core_div,
            "wide_divergences": wide_div, "wide_error": wide_error, "examples": examples[:3], "seed": seed, "gen": gen_v}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Differential check; without --attempt it measures the ORIGINAL code.")
    ap.add_argument("case_dir")
    ap.add_argument("old_python")
    ap.add_argument("new_python")
    ap.add_argument("--attempt", help="runs/<dir>/attempt_N.json whose 'files' are the candidate patch")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    files = json.loads(Path(a.attempt).read_text()).get("files") if a.attempt else None
    print(json.dumps(differential(a.case_dir, a.old_python, a.new_python, files, n=a.n, seed=a.seed),
                     indent=2, default=str))
