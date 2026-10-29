#!/usr/bin/env python3
"""Run a command under Linux Landlock (standard library only; used by patchpilot.sandbox on Linux).

    python -I -S landlock_exec.py [--ro PATH]... [--rw PATH]... [--netns] [--report] -- CMD ARG...

Landlock needs no privileges: after restrict_self the process and its children can only read the --ro paths, read and
write the --rw paths, and (kernel ABI 4 or later) cannot bind or connect any TCP port. With ABI 6 or later they also
cannot send signals to processes outside the restriction or connect to abstract unix sockets of the parent. Everything
not listed is denied, so the home directory and the repository are unreachable unless a path under them is listed.
--netns additionally moves the process into an empty network namespace (user namespace plus network namespace),
which also blocks UDP and other protocols; if the kernel refuses, the process continues without it (--report says so).
Exit code 126 if Landlock is not available: nothing is run unrestricted.
"""
import ctypes
import os
import stat
import sys

SYS_CREATE, SYS_ADD, SYS_RESTRICT = 444, 445, 446  # same numbers on x86-64 and arm64
EXECUTE, WRITE_FILE, READ_FILE, READ_DIR = 1 << 0, 1 << 1, 1 << 2, 1 << 3
REFER, TRUNCATE, IOCTL_DEV = 1 << 13, 1 << 14, 1 << 15
NET_BIND_TCP, NET_CONNECT_TCP = 1 << 0, 1 << 1
SCOPE_ABSTRACT_UNIX, SCOPE_SIGNAL = 1 << 0, 1 << 1
CLONE_NEWUSER, CLONE_NEWNET = 0x10000000, 0x40000000


class RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64), ("handled_access_net", ctypes.c_uint64),
                ("scoped", ctypes.c_uint64)]


class PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def die(code: int, msg: str):
    sys.stderr.write("landlock_exec: " + msg + "\n")
    sys.exit(code)


def main(argv: list) -> None:
    ro, rw, netns, report = [], [], False, False
    i = 0
    while i < len(argv) and argv[i] != "--":
        a = argv[i]
        if a == "--ro":
            ro.append(argv[i + 1]); i += 2
        elif a == "--rw":
            rw.append(argv[i + 1]); i += 2
        elif a == "--netns":
            netns = True; i += 1
        elif a == "--report":
            report = True; i += 1
        else:
            die(2, f"unknown option {a}")
    cmd = argv[i + 1:]
    if not cmd:
        die(2, "no command after --")

    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long

    abi = libc.syscall(ctypes.c_long(SYS_CREATE), ctypes.c_void_p(None), ctypes.c_size_t(0), ctypes.c_uint32(1))
    if abi < 1:
        die(126, f"Landlock is not available on this kernel (errno {ctypes.get_errno()}); not running the command")

    fs_all = (1 << 13) - 1  # EXECUTE .. MAKE_SYM (ABI 1)
    if abi >= 2:
        fs_all |= REFER
    if abi >= 3:
        fs_all |= TRUNCATE
    if abi >= 5:
        fs_all |= IOCTL_DEV

    got_netns = False
    if netns:
        uid, gid = os.getuid(), os.getgid()
        if libc.unshare(ctypes.c_int(CLONE_NEWUSER | CLONE_NEWNET)) == 0:
            try:
                with open("/proc/self/setgroups", "w") as f:
                    f.write("deny")
                with open("/proc/self/uid_map", "w") as f:
                    f.write(f"{uid} {uid} 1")
                with open("/proc/self/gid_map", "w") as f:
                    f.write(f"{gid} {gid} 1")
                got_netns = True
            except OSError as e:
                die(126, f"network namespace was created but the id maps failed ({e}); not running the command")

    attr = RulesetAttr()
    attr.handled_access_fs = fs_all
    if abi >= 4:
        attr.handled_access_net = NET_BIND_TCP | NET_CONNECT_TCP
    if abi >= 6:
        attr.scoped = SCOPE_ABSTRACT_UNIX | SCOPE_SIGNAL
    rfd = libc.syscall(ctypes.c_long(SYS_CREATE), ctypes.byref(attr), ctypes.c_size_t(ctypes.sizeof(attr)), ctypes.c_uint32(0))
    if rfd < 0:
        die(126, f"landlock_create_ruleset failed (errno {ctypes.get_errno()})")

    ro_dir = (EXECUTE | READ_FILE | READ_DIR) & fs_all
    ro_file = (EXECUTE | READ_FILE) & fs_all
    rw_dir = fs_all
    rw_file = (EXECUTE | READ_FILE | WRITE_FILE | TRUNCATE | IOCTL_DEV) & fs_all
    for paths, rd, rf in ((ro, ro_dir, ro_file), (rw, rw_dir, rw_file)):
        for p in paths:
            try:
                pfd = os.open(p, os.O_PATH | os.O_CLOEXEC)
            except OSError:
                continue  # a listed path that does not exist simply grants nothing
            try:
                rule = PathBeneath(rd if stat.S_ISDIR(os.fstat(pfd).st_mode) else rf, pfd)
                r = libc.syscall(ctypes.c_long(SYS_ADD), ctypes.c_int(rfd), ctypes.c_int(1), ctypes.byref(rule), ctypes.c_uint32(0))
                if r != 0:
                    die(126, f"landlock_add_rule failed for {p} (errno {ctypes.get_errno()})")
            finally:
                os.close(pfd)

    if libc.prctl(ctypes.c_int(38), ctypes.c_ulong(1), ctypes.c_ulong(0), ctypes.c_ulong(0), ctypes.c_ulong(0)) != 0:
        die(126, "prctl(NO_NEW_PRIVS) failed")
    if libc.syscall(ctypes.c_long(SYS_RESTRICT), ctypes.c_int(rfd), ctypes.c_uint32(0)) != 0:
        die(126, f"landlock_restrict_self failed (errno {ctypes.get_errno()})")
    os.close(rfd)
    if report:
        sys.stderr.write(f"landlock_exec: abi={abi} netns={int(got_netns)}\n")
    os.execv(cmd[0], cmd)


if __name__ == "__main__":
    main(sys.argv[1:])
