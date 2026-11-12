# Finals preparation studies (2026-11-12)

Reports, scripts and small text outputs from the strategy studies, copied out of a temporary folder so
they can be re-run. `docs/EVIDENCE_TABLE.md` grades what each finding does and does not justify.

| Folder | Question | Start with |
|---|---|---|
| `clone_field/` | Can stand-in bots fitted from one download predict how our bots score? | `REPORT.md`, then `lib/fit_clones.py`, `lib/simrun.py` |
| `adaptation/` | How much did real teams change between rounds, against a seat, within a table? | `REPORT.md`; `extract*.py` then `q1.py`...`q5.py`, `boston.py`; `res_*.txt` are the full tables |
| `identity/` | What identifies a team, and what would hiding cost and buy? | `REPORT.md`; `extract.py`, `recog.py`, `mask.py`, `q4.py` |
| `redteam/` | Where does the plan assume opponents are fixed or unaware? | `REPORT.md`; `chk.py`, `an.py`, `adapt.py` |
| `metagame/` | Which styles beat which, in fields of clones; does the response chain converge or cycle? | `REPORT.md`; `mrun.py`, `arch.py`, `an1.py`...`an5.py`, `modal_app.py` |
| `literature/` | Strategy families, their counters and the counters to those | `REPORT.md` (sources linked inside) |

To reproduce: hand histories go in `data/hands/` (see `data/README.md`); run with
`starter-kit/.venv/bin/python -I <script>` from the study's folder. Extraction outputs (pickles, 10 GB+)
are not kept; the extractors rebuild them. Scripts contain absolute paths from the machine they ran on.
Not here yet: the simulator ordering test (still running).
Never commit hand histories or per-table extracts.
