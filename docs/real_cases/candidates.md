# Candidates (run 2 of the fixed queries)

168 distinct hits from docs/real_cases/search_20261029_run2; 75 passed the mechanical screen and are decided by hand below. Rules: `scripts/real_case_screen.py`. A hit found by several queries is listed once, at its first position.

| first seen | hit | type | license | decision | reason |
|---|---|---|---|---|---|
| Q1#1 (also Q2#1) | [ucgmsim/velocity_modelling#64](https://github.com/ucgmsim/velocity_modelling/pull/64) Drop the pandas<3.0 upper bound | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q1#2 (also Q2#10) | [jojacobsen/openpls-engine#58](https://github.com/jojacobsen/openpls-engine/pull/58) chore(deps): bump pandas to 3.0 | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q1#3 | [holoviz/panel#8904](https://github.com/holoviz/panel/pull/8904) compat: Handle pandas 3.1 deprecations in Tabulator | PR | BSD-3-Clause | inspect | passes the mechanical screen |
| Q1#4 (also Q3#3) | [catalyst-cooperative/pudl#5719](https://github.com/catalyst-cooperative/pudl/pull/5719) :panda_face: EIA-923 explicit and dtype-stable transform fixes | PR | MIT | inspect | passes the mechanical screen |
| Q1#5 | [pmorissette/bt#576](https://github.com/pmorissette/bt/pull/576) Fix chained-assignment pattern in positions/outlays/get_transactions | PR | MIT | inspect | passes the mechanical screen |
| Q1#6 (also Q2#16) | [Nixtla/datasetsforecast#115](https://github.com/Nixtla/datasetsforecast/pull/115) fix(phm2008): assign clipped RUL instead of chained inplace clip | PR | MIT | inspect | passes the mechanical screen |
| Q1#7 | [dtcenter/METplotpy#592](https://github.com/dtcenter/METplotpy/pull/592) Feature #591 remove unused dependencies | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q1#8 | [vahidlesani/vivasignals-pro#4](https://github.com/vahidlesani/vivasignals-pro/pull/4) R30: spot horizons, low-TF MTF base, clean charts, handoff | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q1#9 | [pandas-dev/pandas#70131](https://github.com/pandas-dev/pandas/pull/70131) DOC: fix broken examples and inaccurate claims in user guide and docst | PR | BSD-3-Clause | rejected | C3/C4: documentation, test or CI change only |
| Q1#10 | [catalyst-cooperative/pudl#5664](https://github.com/catalyst-cooperative/pudl/pull/5664) :panda_face: EIA-923 explicit and dtype-stable transform fixes | PR | MIT | inspect | passes the mechanical screen |
| Q1#11 | [Alek050/databallpy#344](https://github.com/Alek050/databallpy/issues/344) Fix for Pandas 3.0 | issue | MIT | inspect | passes the mechanical screen |
| Q1#12 | [amirge118/agentsForStocks#34](https://github.com/amirge118/agentsForStocks/pull/34) chore(deps): upgrade pandas 2.2.3 → 3.1.0 | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q1#13 | [berntpopp/kidney-genetics-db#403](https://github.com/berntpopp/kidney-genetics-db/pull/403) chore(deps): update backend dependencies | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q1#14 | [nassim0014/kinz-secure-commerce-hub#38](https://github.com/nassim0014/kinz-secure-commerce-hub/pull/38) chore(deps): bump pandas from 2.2.1 to 3.0.5 in /src/api | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q1#15 (also Q2#2, Q6#1) | [owid/etl#6994](https://github.com/owid/etl/pull/6994) Enable pandas 3 behavior (Copy-on-Write, str dtype) | PR | MIT | inspect | passes the mechanical screen |
| Q1#16 | [m-beau/pixelmap#41](https://github.com/m-beau/pixelmap/pull/41) chore: drop Python 3.10 support | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q1#17 | [ghammad/pyActigraphy#173](https://github.com/ghammad/pyActigraphy/issues/173) Bug in Roenneberg_AoT algorithm for detection of inactivity period | issue | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q1#18 | [catalyst-cooperative/pudl#5665](https://github.com/catalyst-cooperative/pudl/pull/5665) :panda_face: Use dtype-safe assignments and transforms | PR | MIT | inspect | passes the mechanical screen |
| Q1#19 | [RamonRDR/python-study-guide#73](https://github.com/RamonRDR/python-study-guide/pull/73) Start Phase 9 with pandas | PR | MIT | inspect | passes the mechanical screen |
| Q1#20 | [salk-ee/salk_toolkit#82](https://github.com/salk-ee/salk_toolkit/pull/82) Migrate to pandas 3.0 + dependency review | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q1#21 | [dtcenter/METcalcpy#485](https://github.com/dtcenter/METcalcpy/pull/485) Feature remove unused deps | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q1#22 | [jldbc/pybaseball#500](https://github.com/jldbc/pybaseball/pull/500) Fix FutureWarning in team_results.py | PR | MIT | inspect | passes the mechanical screen |
| Q1#23 (also Q3#9) | [NicolasReyrolle/TrackTales#341](https://github.com/NicolasReyrolle/TrackTales/issues/341) refactor: Adapt and optimize codebase for Pandas 3.0.5 | issue | NOASSERTION | inspect | license unclear (NOASSERTION), check by hand |
| Q1#24 | [winter-telescope/mirar#1144](https://github.com/winter-telescope/mirar/pull/1144) Bump astropy to >=7.2.0 and pandas to >=3.0.0 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q1#25 | [dgunning/edgartools#938](https://github.com/dgunning/edgartools/issues/938) 6.0: raise the Python floor to 3.11 (the pandas floor stays at 2.0) | issue | MIT | inspect | passes the mechanical screen |
| Q1#26 | [trellumhq/trellum#73](https://github.com/trellumhq/trellum/pull/73) Build large reports in a third of the memory: pandas 3 and category te | PR | AGPL-3.0 | rejected | C2: license AGPL-3.0 is not MIT/BSD/Apache |
| Q1#27 | [Vandermiet/Beaver_Choice_Paper#18](https://github.com/Vandermiet/Beaver_Choice_Paper/issues/18) 101 — Runnable skeleton: install pydantic-ai, fix the starter, stub th | issue | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q1#28 | [halon176/h-crypto-price-bot#148](https://github.com/halon176/h-crypto-price-bot/pull/148) Update pandas requirement from <3.0.0,>=2.2.2 to >=2.2.2,<4.0.0 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q1#29 | [ansible/metrics-utility#431](https://github.com/ansible/metrics-utility/pull/431) AAP-75305 - chore: upgrade pandas to 3.0 and openpyxl to 3.1.5 with co | PR | Apache-2.0 | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q1#30 | [visikai/ohlc-toolkit#68](https://github.com/visikai/ohlc-toolkit/pull/68) ⬆️ Update pandas requirement from <3.0.0,>=2.3.0 to >=2.3.0,<4.0.0 | PR | NOASSERTION | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#3 | [braydio/RSAssistant#144](https://github.com/braydio/RSAssistant/pull/144) chore(deps): bump pandas from 2.2.3 to 3.0.6 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#4 | [openvax/vaxrank#659](https://github.com/openvax/vaxrank/issues/659) Raise minimum supported pandas to 3.0 | issue | Apache-2.0 | inspect | passes the mechanical screen |
| Q2#5 | [lucasrodes/whatstk#187](https://github.com/lucasrodes/whatstk/pull/187) Fix the small known bugs and turn the type checker back on (#177) | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q2#6 | [openvax/topiary#496](https://github.com/openvax/topiary/issues/496) Raise minimum supported pandas to 3.0 | issue | Apache-2.0 | inspect | passes the mechanical screen |
| Q2#7 | [tech-pw/cryo#312](https://github.com/tech-pw/cryo/pull/312) chore(deps): update pandas requirement from >=2.0.0 to >=3.0.6 | PR | Apache-2.0 | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#8 (also Q3#4) | [phenobarbital/querysource#637](https://github.com/phenobarbital/querysource/pull/637) feat(pandas3-migration): FEAT-161 — Migrate to pandas >= 3.0 | PR | BSD-3-Clause | inspect | passes the mechanical screen |
| Q2#9 | [openvax/mhctools#611](https://github.com/openvax/mhctools/issues/611) Raise minimum supported pandas to 3.0 | issue | Apache-2.0 | inspect | passes the mechanical screen |
| Q2#11 | [W-Thurston/dsbf#47](https://github.com/W-Thurston/dsbf/pull/47) chore(deps): bump pandas from 2.3.1 to 3.0.6 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#12 | [kokjz/fpl-predict#5](https://github.com/kokjz/fpl-predict/pull/5) Bump pandas from 2.2.3 to 3.0.6 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#13 | [w4bo/data-governance-demo#28](https://github.com/w4bo/data-governance-demo/pull/28) chore(deps): update dependency pandas to v3 | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q2#14 | [rjwalters/kicad-tools#6359](https://github.com/rjwalters/kicad-tools/pull/6359) chore(deps): update dependency pandas to v3 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#15 | [googleapis/google-cloud-python#18619](https://github.com/googleapis/google-cloud-python/pull/18619) chore(deps): update dependency pandas to v3 | PR | Apache-2.0 | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#17 | [Bhargavvvv2912/renovate-check-age-of-empires-api#39](https://github.com/Bhargavvvv2912/renovate-check-age-of-empires-api/pull/39) Update dependency pandas to v3 | PR | BSD-3-Clause | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#18 | [TanNhatCMS/jarvis#17](https://github.com/TanNhatCMS/jarvis/pull/17) chore(deps): update dependency pandas to v3 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#19 | [vincenttisseront/bastion-app#426](https://github.com/vincenttisseront/bastion-app/pull/426) chore(deps): update dependency pandas to v3 - autoclosed | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q2#20 | [softagram/sgraph#209](https://github.com/softagram/sgraph/pull/209) Bump pandas from 2.3.3 to 3.0.6 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#21 | [diaoyunxi/price-comparator-tracker#133](https://github.com/diaoyunxi/price-comparator-tracker/pull/133) chore(deps): bump pandas from 2.2.1 to 3.0.6 | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#22 | [lnccbrown/LANfactory#139](https://github.com/lnccbrown/LANfactory/issues/139) Drift on pandas 3.x breaks Copy-on-Write in trainers | issue | MIT | inspect | passes the mechanical screen |
| Q2#23 | [FZJ-IEK3-VSA/FINE#863](https://github.com/FZJ-IEK3-VSA/FINE/pull/863) Update dependency pandas to v3 | PR | NOASSERTION | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#24 | [Unsquared2/quantstats#2](https://github.com/Unsquared2/quantstats/pull/2) Fix benchmark=None crash and pandas 3.0 copy_on_write deprecation | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q2#25 | [openvax/topiary#509](https://github.com/openvax/topiary/pull/509) Require pandas 3 across the supported Python matrix | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q2#26 | [FukaseDaichi/trader#35](https://github.com/FukaseDaichi/trader/pull/35) Bump pandas from 2.3.3 to 3.1.0 | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q2#27 | [bcgov/wps#5867](https://github.com/bcgov/wps/pull/5867) fix(deps): update dependency pandas to v3 | PR | Apache-2.0 | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q2#28 (also Q6#9) | [Radeq2137/leasing-analytics-dbt#5](https://github.com/Radeq2137/leasing-analytics-dbt/pull/5) Add engineering guidelines (Python, pandas, data engineering) | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q2#29 | [eschombu/superleaf#4](https://github.com/eschombu/superleaf/pull/4) superleaf 1.0.0: require pandas 3, accept pd.col expressions | PR | MIT | inspect | passes the mechanical screen |
| Q2#30 | [DevenGaikwad/MatCount#10](https://github.com/DevenGaikwad/MatCount/pull/10) chore(deps): update pandas requirement from <3,>=2.2 to >=3.0.6,<4 | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q3#1 (also Q6#2) | [geopandas/pyogrio#711](https://github.com/geopandas/pyogrio/pull/711) TST: update test_write_read_datetime_tz_objects expected strings for p | PR | MIT | rejected | C3/C4: documentation, test or CI change only |
| Q3#2 | [catalyst-cooperative/pudl#5721](https://github.com/catalyst-cooperative/pudl/pull/5721) :panda_face: Fix EIA null-handling regressions from pandas 3.0 | PR | MIT | inspect | passes the mechanical screen |
| Q3#5 | [pyjanitor-devs/pyjanitor#1801](https://github.com/pyjanitor-devs/pyjanitor/issues/1801) Date conversion tests fail on pandas 3.1: to_datetime returns datetime | issue | MIT | inspect | passes the mechanical screen |
| Q3#6 | [stefan-jansen/zipline-reloaded#334](https://github.com/stefan-jansen/zipline-reloaded/pull/334) BUG: Preserve csvdir metadata dtypes when concatenating empty frames | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q3#7 | [stranske/Trend_Model_Project#6103](https://github.com/stranske/Trend_Model_Project/pull/6103) fix(monte-carlo): count adjacent regime transitions positionally | PR | MIT | inspect | passes the mechanical screen |
| Q3#8 | [Sage-Bionetworks/synapsePythonClient#1471](https://github.com/Sage-Bionetworks/synapsePythonClient/pull/1471) [SYNPY-1933] Updated pandas to use 3.x | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q3#10 | [wkddkw/crypto-quant#6](https://github.com/wkddkw/crypto-quant/pull/6) 修复测试对真实数据的隐式依赖并添加 CI | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q3#11 | [pandas-dev/pandas#65308](https://github.com/pandas-dev/pandas/issues/65308) BUG: pyarrow engine timestamp conversion fails when doing pd.read_csv | issue | BSD-3-Clause | inspect | passes the mechanical screen |
| Q3#12 | [hulacon/word2psy#4](https://github.com/hulacon/word2psy/pull/4) Fix silent defects found in a bug-hunting pass | PR | MIT | inspect | passes the mechanical screen |
| Q3#13 | [jsonpickle/jsonpickle#619](https://github.com/jsonpickle/jsonpickle/pull/619) Rebuild numpy scalars from their declared dtype | PR | BSD-3-Clause | inspect | passes the mechanical screen |
| Q3#14 | [pandas-dev/pandas#53643](https://github.com/pandas-dev/pandas/issues/53643) BUG: Timedelta with non-ns unit does not add correctly to stdlib datet | issue | BSD-3-Clause | inspect | passes the mechanical screen |
| Q3#15 | [ashribad2005/sih-trustgraph-2026#2](https://github.com/ashribad2005/sih-trustgraph-2026/pull/2) Member 1:AI part is completed | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q3#16 | [DASDAE/dascore#949](https://github.com/DASDAE/dascore/pull/949) Require pandas 3, and convert only the times a row states | PR | NOASSERTION | inspect | license unclear (NOASSERTION), check by hand |
| Q3#17 | [muntherhasan1/scprs-analysis#24](https://github.com/muntherhasan1/scprs-analysis/pull/24) Upgrade pandas to 3.x (lift the deliberate 2.x hold) | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q3#18 (also Q4#4) | [RadwanSusan/RAD-Trading#72](https://github.com/RadwanSusan/RAD-Trading/pull/72) [Aikido] Fix 9 security issues in numpy, scipy, werkzeug and 4 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q3#19 | [RadwanSusan/RAD-Trading#53](https://github.com/RadwanSusan/RAD-Trading/pull/53) [Aikido] Fix 7 security issues in fastjsonschema, numpy, werkzeug and  | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q3#20 | [wdm0006/git-pandas#75](https://github.com/wdm0006/git-pandas/issues/75) [autopilot] Support pandas 3.x: lift the <3.0.0 cap and fix the two ca | issue | BSD-3-Clause | inspect | passes the mechanical screen |
| Q3#21 | [deepaihealth/expert-work#1122](https://github.com/deepaihealth/expert-work/pull/1122) chore(sandbox-image): 依赖一次性扫清——8 个包,weasyprint+pydyf 成对升,pandas 上 3.0 | PR | AGPL-3.0 | rejected | C2: license AGPL-3.0 is not MIT/BSD/Apache |
| Q3#22 | [pandas-dev/pandas#66709](https://github.com/pandas-dev/pandas/issues/66709) BUG: to_json(date_format="epoch") ignores date_unit for datetime-likes | issue | BSD-3-Clause | inspect | passes the mechanical screen |
| Q3#23 | [MingoDynasty/Corporate-Serf-Dashboard#151](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/151) chore(deps): refresh dependency floors and correct pandas-stubs | PR | AGPL-3.0 | rejected | C2: license AGPL-3.0 is not MIT/BSD/Apache |
| Q3#24 | [pmrv/fleche#1004](https://github.com/pmrv/fleche/issues/1004) Digesting a DataFrame with an object column of arrays raises (hash_pan | issue | BSD-3-Clause | inspect | passes the mechanical screen |
| Q3#25 | [DASDAE/dascore#960](https://github.com/DASDAE/dascore/pull/960) Hold every annotation cell in the type it reads back as | PR | NOASSERTION | inspect | license unclear (NOASSERTION), check by hand |
| Q3#26 | [tamnd/firepanda-compat#8](https://github.com/tamnd/firepanda-compat/issues/8) The scoreboard: per section, with coverage beside it | issue | Apache-2.0 | inspect | passes the mechanical screen |
| Q3#27 | [tim1016/learn-ai#920](https://github.com/tim1016/learn-ai/pull/920) feat: establish temporal authority | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q3#28 | [cognitedata/indsl#639](https://github.com/cognitedata/indsl/pull/639) fix: resolve pandas 3 DatetimeIndex-to-int64 unit regression | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q3#29 | [pastas/pastas#1268](https://github.com/pastas/pastas/issues/1268) Very bad fit when unit of DatetimeIndex of oseries is not us (micro-se | issue | MIT | inspect | passes the mechanical screen |
| Q3#30 | [ziagl888/Kythera#229](https://github.com/ziagl888/Kythera/pull/229) fix(replay): RUB2 skew root-caused to the measurement window, not fund | PR | MIT | inspect | passes the mechanical screen |
| Q4#1 | [asmahani/ogboost#1](https://github.com/asmahani/ogboost/issues/1) OverflowError out of nowhere | issue | MIT | inspect | passes the mechanical screen |
| Q4#2 (also Q5#6) | [brendan-m-murphy/pytensor#4](https://github.com/brendan-m-murphy/pytensor/pull/4) Numpy 2 updates | PR | NOASSERTION | inspect | license unclear (NOASSERTION), check by hand |
| Q4#3 | [CNES/georastertools#35](https://github.com/CNES/georastertools/pull/35) Update for compatibility with numpy v1 and numpy v2 | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q4#5 | [nodetool-ai/nodetool-core#982](https://github.com/nodetool-ai/nodetool-core/pull/982) Bolt: [performance improvement] | PR | AGPL-3.0 | rejected | C2: license AGPL-3.0 is not MIT/BSD/Apache |
| Q4#6 | [RadwanSusan/RAD-Trading#67](https://github.com/RadwanSusan/RAD-Trading/pull/67) [Aikido] Fix 10 security issues in numpy, platformdirs, scipy and 5 mo | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#7 | [opendatahub-io/notebooks#2864](https://github.com/opendatahub-io/notebooks/issues/2864) TrustyAI notebook: Verify compatibility with NumPy 2.3 and Pandas 2.3  | issue | Apache-2.0 | inspect | passes the mechanical screen |
| Q4#8 | [RadwanSusan/RAD-Trading#73](https://github.com/RadwanSusan/RAD-Trading/pull/73) [Aikido] Fix 11 security issues in fsspec, werkzeug, numpy and 5 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#9 | [RadwanSusan/RAD-Trading#62](https://github.com/RadwanSusan/RAD-Trading/pull/62) [Aikido] Fix 8 security issues in numpy, scipy, werkzeug and 4 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#10 | [janosh/matbench-discovery#325](https://github.com/janosh/matbench-discovery/pull/325) Clean up site tests and diatomics tooling | PR | MIT | inspect | passes the mechanical screen |
| Q4#11 | [RadwanSusan/RAD-Trading#70](https://github.com/RadwanSusan/RAD-Trading/pull/70) [Aikido] Fix 14 security issues in urllib3, tornado, numpy and 6 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#12 | [DeebotUniverse/client.py#524](https://github.com/DeebotUniverse/client.py/pull/524) Update numpy requirement from <2.0,>=1.23.2 to >=1.23.2,<3.0 | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q4#13 | [numpy/numpy#21261](https://github.com/numpy/numpy/issues/21261) BUG: Bitshift operations on scalar integers change type to int64 or fa | issue | NOASSERTION | inspect | license unclear (NOASSERTION), check by hand |
| Q4#14 | [RadwanSusan/RAD-Trading#66](https://github.com/RadwanSusan/RAD-Trading/pull/66) [Aikido] Fix 9 security issues in numpy, scipy, werkzeug and 4 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#15 | [RadwanSusan/RAD-Trading#58](https://github.com/RadwanSusan/RAD-Trading/pull/58) [Aikido] Fix 8 security issues in numpy, scipy, werkzeug and 4 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#16 | [RadwanSusan/RAD-Trading#74](https://github.com/RadwanSusan/RAD-Trading/pull/74) [Aikido] Fix 9 security issues in numpy, scipy, werkzeug and 4 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#17 | [cupy/cupy#9982](https://github.com/cupy/cupy/pull/9982) core: bool.conj() promotes to int8 (match NumPy 2.x) | PR | MIT | inspect | passes the mechanical screen |
| Q4#18 | [block-hczhai/pyblock3-preview#19](https://github.com/block-hczhai/pyblock3-preview/issues/19) `SZ.from_flat()` raises `RuntimeWarning: overflow` and returns wrong r | issue | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q4#19 | [RadwanSusan/RAD-Trading#68](https://github.com/RadwanSusan/RAD-Trading/pull/68) [Aikido] Fix 11 security issues in jupyterlab, numpy, scipy and 5 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#20 | [RadwanSusan/RAD-Trading#60](https://github.com/RadwanSusan/RAD-Trading/pull/60) [Aikido] Fix 8 security issues in numpy, scipy, werkzeug and 4 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#21 | [RadwanSusan/RAD-Trading#71](https://github.com/RadwanSusan/RAD-Trading/pull/71) [Aikido] Fix 11 security issues in jupyterlab, numpy, scipy and 5 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#22 | [cupy/cupy#9983](https://github.com/cupy/cupy/pull/9983) test_ndarray_complex_ops: drop identity assert from test_conj_pass | PR | MIT | inspect | passes the mechanical screen |
| Q4#23 | [RadwanSusan/RAD-Trading#64](https://github.com/RadwanSusan/RAD-Trading/pull/64) [Aikido] Fix 18 security issues in anyio, urllib3, tornado and 8 more | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#24 | [sparlit/EQATS#313](https://github.com/sparlit/EQATS/pull/313) [Aikido] Fix security issue in numpy via major version upgrade from 1. | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#25 | [sank29mane/growin-app#432](https://github.com/sank29mane/growin-app/pull/432) ⚡ Bolt: Vectorize market impact slippage calculation | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#26 | [n24q02m/hull#93](https://github.com/n24q02m/hull/pull/93) fix(deps): update numpy to >=2.5.4,<2.6 - autoclosed | PR | Apache-2.0 | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q4#27 | [kejhy93/ProteinFolding#180](https://github.com/kejhy93/ProteinFolding/pull/180) Update dependency numpy to v2.5.4 | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q4#28 | [baneeishaque/attentive-gan-derainnet#1699](https://github.com/baneeishaque/attentive-gan-derainnet/pull/1699) Scheduled daily dependency update on Monday | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q4#29 | [achrafarbounper/ThinkTuning#36](https://github.com/achrafarbounper/ThinkTuning/pull/36) [Aikido] Fix security issue in numpy via major version upgrade from 1. | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q4#30 | [baneeishaque/attentive-gan-derainnet#1698](https://github.com/baneeishaque/attentive-gan-derainnet/pull/1698) Scheduled daily dependency update on Saturday | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q5#1 | [Solafune-Inc/solafune-tools#32](https://github.com/Solafune-Inc/solafune-tools/pull/32) fix: Upgrade Pillow to 13.0.0 for CVE-2026-112400 | PR | MIT | inspect | passes the mechanical screen |
| Q5#2 | [NeuralEnsemble/python-neo#1883](https://github.com/NeuralEnsemble/python-neo/issues/1883) biocam gain calculation bug when using numpy >= 2.0.0. | issue | BSD-3-Clause | inspect | passes the mechanical screen |
| Q5#3 | [pytorch/pytorch#200880](https://github.com/pytorch/pytorch/pull/200880) [funcol] Support avg reduce_scatter and product all_reduce backward | PR | NOASSERTION | inspect | license unclear (NOASSERTION), check by hand |
| Q5#4 | [kornia/kornia#5253](https://github.com/kornia/kornia/pull/5253) fix(filters)!: guided_blur subsample accepts sizes not divisible by su | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q5#5 | [huggingface/lerobot#4948](https://github.com/huggingface/lerobot/pull/4948) perf(streaming): cut sidecar build memory by 91% | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q5#7 | [pandas-dev/pandas#48867](https://github.com/pandas-dev/pandas/issues/48867) BUG/API: setting behavior inserting negative numbers in np.uint/nullab | issue | BSD-3-Clause | inspect | passes the mechanical screen |
| Q5#8 | [AIcrowd/flopscope#168](https://github.com/AIcrowd/flopscope/pull/168) fix(einsum)!: apply the caller's casting rule to out=, as numpy does | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q5#9 | [tmolteno/disko#30](https://github.com/tmolteno/disko/pull/30) Bump the python-minor-patch group across 1 directory with 14 updates | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#10 | [edithatogo/tobac#26](https://github.com/edithatogo/tobac/pull/26) fix(deps): update scientific stack qualification | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q5#11 | [edithatogo/tobac#19](https://github.com/edithatogo/tobac/pull/19) fix(deps): update scientific stack qualification | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q5#12 | [rmems/grok-ozempic#142](https://github.com/rmems/grok-ozempic/pull/142) Add ordered Grok-1 text input manifest validation (v1) | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q5#13 | [pytorch/pytorch#190092](https://github.com/pytorch/pytorch/pull/190092) Add c10::safe_conv (strict, integer-only) and c10::unsafe_wrapping_con | PR | NOASSERTION | inspect | license unclear (NOASSERTION), check by hand |
| Q5#14 | [umutaktepe/AeroTools#2093](https://github.com/umutaktepe/AeroTools/pull/2093) Bug #12345 Scheduled daily dependency update on Monday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#15 | [umutaktepe/AeroTools#2092](https://github.com/umutaktepe/AeroTools/pull/2092) Bug #12345 Scheduled daily dependency update on Saturday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#16 | [umutaktepe/AeroTools#2091](https://github.com/umutaktepe/AeroTools/pull/2091) Bug #12345 Scheduled daily dependency update on Thursday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#17 | [umutaktepe/AeroTools#2090](https://github.com/umutaktepe/AeroTools/pull/2090) Bug #12345 Scheduled daily dependency update on Tuesday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#18 | [icohangar-ops/Practice_Radar#2](https://github.com/icohangar-ops/Practice_Radar/pull/2) [Aikido] Fix 4 security issues in requests, numpy | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q5#19 | [umutaktepe/AeroTools#2089](https://github.com/umutaktepe/AeroTools/pull/2089) Bug #12345 Scheduled daily dependency update on Sunday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#20 | [umutaktepe/AeroTools#2088](https://github.com/umutaktepe/AeroTools/pull/2088) Bug #12345 Scheduled daily dependency update on Friday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#21 | [umutaktepe/AeroTools#2087](https://github.com/umutaktepe/AeroTools/pull/2087) Bug #12345 Scheduled daily dependency update on Wednesday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#22 | [umutaktepe/AeroTools#2086](https://github.com/umutaktepe/AeroTools/pull/2086) Bug #12345 Scheduled daily dependency update on Monday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#23 | [umutaktepe/AeroTools#2085](https://github.com/umutaktepe/AeroTools/pull/2085) Bug #12345 Scheduled daily dependency update on Saturday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#24 | [Sagargupta16/stock-market-prediction#58](https://github.com/Sagargupta16/stock-market-prediction/pull/58) chore(deps): update monthly dependencies | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q5#25 | [umutaktepe/AeroTools#2084](https://github.com/umutaktepe/AeroTools/pull/2084) Bug #12345 Scheduled daily dependency update on Thursday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#26 | [Itqan-community/Munajjam#114](https://github.com/Itqan-community/Munajjam/pull/114) feat(transcription): add FastConformer CTC alignment | PR | MIT | inspect | passes the mechanical screen |
| Q5#27 | [umutaktepe/AeroTools#2083](https://github.com/umutaktepe/AeroTools/pull/2083) Bug #12345 Scheduled daily dependency update on Tuesday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#28 | [baneeishaque/attentive-gan-derainnet#1657](https://github.com/baneeishaque/attentive-gan-derainnet/pull/1657) Scheduled daily dependency update on Saturday | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q5#29 | [umutaktepe/AeroTools#2082](https://github.com/umutaktepe/AeroTools/pull/2082) Bug #12345 Scheduled daily dependency update on Sunday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q5#30 | [umutaktepe/AeroTools#2081](https://github.com/umutaktepe/AeroTools/pull/2081) Bug #12345 Scheduled daily dependency update on Friday | PR | GPL-3.0 | rejected | C2: license GPL-3.0 is not MIT/BSD/Apache |
| Q6#3 | [mazino2d/caketool#16](https://github.com/mazino2d/caketool/pull/16) fix: pandas 3 compatibility in encoder and tests | PR | MIT | inspect | passes the mechanical screen |
| Q6#4 | [pyjanitor-devs/pyjanitor#1745](https://github.com/pyjanitor-devs/pyjanitor/pull/1745) Preserve object dtype in conditional-join result columns | PR | MIT | inspect | passes the mechanical screen |
| Q6#5 | [capitalone/locopy#389](https://github.com/capitalone/locopy/pull/389) fix: support pandas 3.0 dtype changes, add tox matrix for pandas versi | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q6#6 | [jmineau/PYSTILT#269](https://github.com/jmineau/PYSTILT/pull/269) test: read STILT-R's CSV dumps without read_csv(float_precision=), dep | PR | MIT | rejected | C3/C4: documentation, test or CI change only |
| Q6#7 | [cuinfoscience/INFO-Missing-Manual#51](https://github.com/cuinfoscience/INFO-Missing-Manual/pull/51) Name pandas 3's str dtype alongside pandas 2's object | PR | MIT | inspect | passes the mechanical screen |
| Q6#8 | [pyathena-dev/PyAthena#885](https://github.com/pyathena-dev/PyAthena/pull/885) Require pandas 3.0 and pyarrow 22.0 | PR | MIT | inspect | passes the mechanical screen |
| Q6#10 | [sourabh1996/sourabh1996.github.io#13](https://github.com/sourabh1996/sourabh1996.github.io/pull/13) Numerical Computing and Data Analysis: all lessons written | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q6#11 | [PyPSA/linopy#924](https://github.com/PyPSA/linopy/issues/924) spec: grouped operators crash on string labels under pandas 3.0 (Arrow | issue | MIT | inspect | passes the mechanical screen |
| Q6#12 | [rubengura/Optimizing_Public_Transportation#8](https://github.com/rubengura/Optimizing_Public_Transportation/pull/8) Bump pandas from 2.3.3 to 3.0.6 in /producers | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q6#13 | [ydvSajal/repoMl#1](https://github.com/ydvSajal/repoMl/pull/1) chore(repo): project skeleton, placeholder modules, pinned requirement | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q6#14 | [WindWang2/webgis-ai-agent#1494](https://github.com/WindWang2/webgis-ai-agent/pull/1494) build(deps): update pandas requirement from <3.0.0,>=2.2.2 to >=2.2.2, | PR | MIT | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q6#15 | [NVIDIA-BioNeMo/bionemo-recipes#1744](https://github.com/NVIDIA-BioNeMo/bionemo-recipes/pull/1744) Fix pandas 3.0 breakage in evo2_phage_gen unit tests and evo2_megatron | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q6#16 | [hamedbh/piicleaner#79](https://github.com/hamedbh/piicleaner/pull/79) Support Python 3.11–3.15: upgrade pyo3 to 0.29 and drop 3.10 | PR | MIT | inspect | passes the mechanical screen |
| Q6#17 | [guillermo-navas-palencia/optbinning#400](https://github.com/guillermo-navas-palencia/optbinning/pull/400) Fix categorical variable detection under pandas >= 3.0 | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q6#18 | [jhkirby2001-collab/Procurement-ai-tools#21](https://github.com/jhkirby2001-collab/Procurement-ai-tools/pull/21) Fix Spend Report render crash under pandas 3.0 (new str dtype) | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q6#19 | [MaxHalford/sorobn#51](https://github.com/MaxHalford/sorobn/pull/51) Support pandas 3, fix chow_liu on compacted numeric columns | PR | MIT | inspect | passes the mechanical screen |
| Q6#20 | [YosefLab/Cassiopeia#290](https://github.com/YosefLab/Cassiopeia/pull/290) Fix pandas 3.0 / numpy 2 compatibility | PR | MIT | inspect | passes the mechanical screen |
| Q6#21 | [meteostat/meteostat#303](https://github.com/meteostat/meteostat/pull/303) fix: pandas 3.0+ compatibility | PR | MIT | inspect | passes the mechanical screen |
| Q6#22 | [scverse/anndata#2669](https://github.com/scverse/anndata/pull/2669) Backport PR #2629: feat: Store dask arrays matching dask chunk size | PR | BSD-3-Clause | inspect | passes the mechanical screen |
| Q6#23 | [UT-Computational-NE/rocksteady#109](https://github.com/UT-Computational-NE/rocksteady/issues/109) Pandas4Warning in test_regression's golden comparison; the FutureWarni | issue | BSD-3-Clause | inspect | passes the mechanical screen |
| Q6#24 | [explorerhq/sql-explorer#711](https://github.com/explorerhq/sql-explorer/pull/711) Fix CI: pin ruff, make type inference tests pandas 3 compatible | PR | NOASSERTION | inspect | license unclear (NOASSERTION), check by hand |
| Q6#25 | [jwalcutt/risk-scoring-service#43](https://github.com/jwalcutt/risk-scoring-service/pull/43) Bump pandas from 2.3.3 to 3.0.5 | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q6#26 | [isteven/agentic-data-analysis#23](https://github.com/isteven/agentic-data-analysis/pull/23) feat(data): add live data.gov.sg API client with pagination + retry | PR | none | rejected | C2: license none is not MIT/BSD/Apache |
| Q6#27 | [selimfirat/pysad#191](https://github.com/selimfirat/pysad/pull/191) build: bump pandas from 2.2.3 to 2.3.3 | PR | BSD-3-Clause | rejected | C4: dependency bump or automated update, no project code fix in the title |
| Q6#28 | [ludwig-ai/ludwig#4203](https://github.com/ludwig-ai/ludwig/pull/4203) fix: pandas 3 compatibility | PR | Apache-2.0 | inspect | passes the mechanical screen |
| Q6#29 | [cram2/cognitive_robot_abstract_machine#597](https://github.com/cram2/cognitive_robot_abstract_machine/pull/597) Recognize pandas string dtype in infer_variables_from_dataframe | PR | LGPL-3.0 | rejected | C2: license LGPL-3.0 is not MIT/BSD/Apache |
| Q6#30 | [guillermo-navas-palencia/optbinning#399](https://github.com/guillermo-navas-palencia/optbinning/issues/399) BinningProcess misclassifies string columns as numerical | issue | Apache-2.0 | inspect | passes the mechanical screen |

## Decisions on the hits marked `inspect`

Read in the order of the table above (first-seen position). `finalist` = needs the code at the parent of the fix commit before any decision on C3 and C5-C6; `open` = could not be decided from the pages; `(decided from the title)` = the page was not opened.

| first seen | hit | decision | reason |
|---|---|---|---|
| Q1#3 | holoviz/panel#8904 | rejected | C1,C3: pandas 3.1 deprecations; several functions; bokeh and vega dependencies |
| Q1#4 | catalyst-cooperative/pudl#5719 | rejected | C3: four modules, disjoint functions; failures described as errors |
| Q1#5 | pmorissette/bt#576 | rejected | C6: the old code still gives the correct result, only a ChainedAssignmentError warning |
| Q1#6 | Nixtla/datasetsforecast#115 | finalist | silent loss of clip(inplace=True) under copy-on-write; C3 open (class method PHM2008.load), needs the code |
| Q1#7 | dtcenter/METplotpy#592 | rejected | C4: removes warning filters and unused code, no silent-result fix |
| Q1#10 | catalyst-cooperative/pudl#5664 | rejected | C3: several PUDL-internal functions; pandas 3.0 attribution not shown |
| Q1#11 | Alek050/databallpy#344 | open | issue body is empty, no fix pull request named; C4 cannot be verified yet |
| Q1#15 | owid/etl#6994 | rejected | C3: migration across many ETL steps, not one function |
| Q1#18 | catalyst-cooperative/pudl#5665 | finalist-weak | silent no-op of group.license_id_ferc1.update under copy-on-write; C3 open (PUDL internals), needs the code |
| Q1#19 | RamonRDR/python-study-guide#73 | rejected | C4: teaching material, not a fix |
| Q1#20 | salk-ee/salk_toolkit#82 | finalist | _reconcile_categories silently skipped str columns under pandas 3; C3 open, needs the code |
| Q1#21 | dtcenter/METcalcpy#485 | rejected | C4: removes unused dependencies |
| Q1#22 | jldbc/pybaseball#500 | finalist | chained replace(inplace=True) in team_results (FutureWarning on 2.x, silent no-op on 3.0); C3 open, needs the code |
| Q1#23 | NicolasReyrolle/TrackTales#341 | rejected | C2,C3: license not stated; project-wide refactor issue |
| Q1#25 | dgunning/edgartools#938 | rejected | C4: raises the Python floor |
| Q2#4 | openvax/vaxrank#659 | rejected | C4: support-policy issue, no code |
| Q2#6 | openvax/topiary#496 | rejected | C4: support-policy issue, no code |
| Q2#8 | phenobarbital/querysource#637 | open | page shows commit titles only (transforms.py copy-on-write fix); code not visible |
| Q2#9 | openvax/mhctools#611 | rejected | C4: support-policy issue, no code |
| Q2#22 | lnccbrown/LANfactory#139 | rejected | C6: loud ValueError (read-only array) |
| Q2#25 | openvax/topiary#509 | rejected | C4: dependency floor and test cleanup |
| Q2#29 | eschombu/superleaf#4 | rejected | C4: requires pandas 3, performance change only |
| Q3#2 | catalyst-cooperative/pudl#5721 | rejected | C3: four modules |
| Q3#5 | pyjanitor-devs/pyjanitor#1801 | rejected | C1: pandas 3.1 resolution change, dates identical |
| Q3#6 | stefan-jansen/zipline-reloaded#334 | rejected | C6: loud TypeError; several functions |
| Q3#7 | stranske/Trend_Model_Project#6103 | rejected | C1: silent but caused by index alignment in crosstab, not by a 3.0 or NumPy 2.0 release-note entry |
| Q3#8 | Sage-Bionetworks/synapsePythonClient#1471 | finalist | convert_dtypes_to_json_serializable: Int64 with missing values becomes Float64 on pandas 3; C3 open, needs the code |
| Q3#11 | pandas-dev/pandas#65308 | rejected | maintainer: not a bug; pandas issue, not upgraded third-party code |
| Q3#12 | hulacon/word2psy#4 | rejected | C1: silent defects are not tied to a 3.0 release-note entry; the pandas 3 failure raises |
| Q3#13 | jsonpickle/jsonpickle#619 | rejected | C1: cause is dtype.type(value) unit inference, not a 3.0 or 2.0 change |
| Q3#14 | pandas-dev/pandas#53643 | rejected | pandas' own bug |
| Q3#16 | DASDAE/dascore#949 | rejected | C2,C6: license not stated; blank-cell bug raised |
| Q3#20 | wdm0006/git-pandas#75 | rejected | C6: both failures are loud (TypeError, AttributeError) |
| Q3#22 | pandas-dev/pandas#66709 | rejected | pandas' own bug |
| Q3#24 | pmrv/fleche#1004 | rejected | C6,C1: raises; reported on pandas 2.3.3 |
| Q3#25 | DASDAE/dascore#960 | rejected | C1,C2: not tied to pandas 3.0; license not stated |
| Q3#26 | tamnd/firepanda-compat#8 | rejected | C4: reporting feature |
| Q3#28 | cognitedata/indsl#639 | finalist | DatetimeIndex to int64 unit regression, silently wrong numbers (matches the datetime resolution note); C3 open (indsl helpers), needs the code |
| Q3#29 | pastas/pastas#1268 | finalist-weak | silent wrong fit when index unit is not ns; fix PR 1269 touches Model.residuals and get_sample; C3 open |
| Q3#30 | ziagl888/Kythera#229 | finalist-weak | open_time.astype('int64')/1e9 silently 1000x smaller; fix applied at four sites; C3 open |
| Q4#1 | asmahani/ogboost#1 | rejected | C6: OverflowError (loud) |
| Q4#2 | brendan-m-murphy/pytensor#4 | rejected | C2,C3: license unclear; broad NumPy 2 update |
| Q4#3 | CNES/georastertools#35 | rejected | C4: test precision changes only |
| Q4#7 | opendatahub-io/notebooks#2864 | rejected | C4: compatibility audit, no fix |
| Q4#10 | janosh/matbench-discovery#325 | rejected | C4: no silent-result fix described |
| Q4#13 | numpy/numpy#21261 | rejected | NumPy's own issue from 2022 |
| Q4#17 | cupy/cupy#9982 | rejected | CuPy library code mirroring a NumPy 2.4.5 regression |
| Q4#22 | cupy/cupy#9983 | rejected | C4: test change only (decided from the title) |
| Q5#1 | Solafune-Inc/solafune-tools#32 | rejected | C4: Pillow security upgrade (decided from the title) |
| Q5#2 | NeuralEnsemble/python-neo#1883 | rejected | C3: one line inside a BiocamRawIO method that reads HDF5 files |
| Q5#3 | pytorch/pytorch#200880 | rejected | C1,C2: unrelated to the release notes (decided from the title); license not machine-identified |
| Q5#4 | kornia/kornia#5253 | rejected | C1: unrelated to the release notes (decided from the title) |
| Q5#5 | huggingface/lerobot#4948 | rejected | C4: performance change (decided from the title) |
| Q5#7 | pandas-dev/pandas#48867 | rejected | pandas API issue from 2022, not an upgrade break (decided from the title) |
| Q5#10 | edithatogo/tobac#26 | rejected | C4: dependency qualification update (decided from the title) |
| Q5#11 | edithatogo/tobac#19 | rejected | C4: dependency qualification update (decided from the title) |
| Q5#12 | rmems/grok-ozempic#142 | rejected | C4: new feature (decided from the title) |
| Q5#13 | pytorch/pytorch#190092 | rejected | C1,C2: C++ helper, unrelated (decided from the title) |
| Q5#26 | Itqan-community/Munajjam#114 | rejected | C4: new feature (decided from the title) |
| Q6#3 | mazino2d/caketool#16 | finalist-weak | FeatureEncoder skipped str columns via select_dtypes under pandas 3; class method, C3 open, needs the code |
| Q6#4 | pyjanitor-devs/pyjanitor#1745 | rejected | C3: pyjanitor internals, helper at three call sites |
| Q6#5 | capitalone/locopy#389 | finalist | find_column_type_pandas silently typed date columns as varchar on pandas 3; localized function, C3 open, needs the code |
| Q6#7 | cuinfoscience/INFO-Missing-Manual#51 | rejected | C4: documentation (decided from the title) |
| Q6#8 | pyathena-dev/PyAthena#885 | rejected | C4: dependency floors, tests and docs |
| Q6#11 | PyPSA/linopy#924 | rejected | C6: TypeError (loud); many functions |
| Q6#16 | hamedbh/piicleaner#79 | rejected | C4: Python version support and pyo3 upgrade (decided from the title) |
| Q6#17 | guillermo-navas-palencia/optbinning#400 | rejected | C6: crash downstream, not silent |
| Q6#19 | MaxHalford/sorobn#51 | rejected | C6: TypeError (loud) |
| Q6#20 | YosefLab/Cassiopeia#290 | rejected | C6: every listed failure raised |
| Q6#21 | meteostat/meteostat#303 | rejected | C6,C3: crashes; several files and a project helper |
| Q6#22 | scverse/anndata#2669 | rejected | C1: unrelated backport (decided from the title) |
| Q6#23 | UT-Computational-NE/rocksteady#109 | rejected | C6: warning policy, results unchanged (decided from the title) |
| Q6#24 | explorerhq/sql-explorer#711 | rejected | C4: CI and test only, outputs identical on both versions; license not stated |
| Q6#28 | ludwig-ai/ludwig#4203 | rejected | C6,C3: loud TypeError; several places |
| Q6#30 | guillermo-navas-palencia/optbinning#399 | rejected | C6: issue behind #400, crash |
