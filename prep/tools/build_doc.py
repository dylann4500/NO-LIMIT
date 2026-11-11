#!/usr/bin/env python3
"""Assemble docs/BUILD_PROMPT.md from the template, the real source files and the real parameters."""
import json, os, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "lab"))
FILES = ["lab/event_config.json", "lab/pk.py","lab/engine.py", "lab/field.py", "lab/hero.py", "lab/strength.py", "lab/methods.py", "lab/run.py", "lab/mtune.py", "lab/tune_event.py", "lab/exploit_loop.py",
         "lab/make_bot.py", "lab/build_tables.py", "lab/nash_hu.py", "lab/test_bot.py", "lab/test_engine.py", "lab/test_parity.py",
         "make_submission.sh", "benchmark/slumbot_client.py", "rehearsal/README.md", "rehearsal/kit/agent.py", "rehearsal/kit/simulate.py", "rehearsal/kit/rules_card.json", "rehearsal/kit/my_bot_template.py", "rehearsal/solution/adapted_bot.py",
         "lab/tuned_final.json", "lab/tuned_blend.json", "lab/tuned_lookup.json", "lab/tuned_meta1.json", "lab/tuned_meta3.json", "lab/tuned_mcblend.json", "lab/exploit_0.json", "lab/exploit_1.json", "lab/exploit_2.json", "lab/exploit_3.json",
         "lab/table_holdem.json", "lab/strength_holdem.json", "lab/nash_hu_holdem.json"]
LANG = {".py": "python", ".sh": "bash", ".json": "json", ".md": "markdown"}
import pk
mu = json.load(open(os.path.join(R, "lab/tuned_final.json")))["mu"]
order = sorted(mu)
rows = ["| Parameter | Value |", "|---|---|"] + [f"| `{k}` | {mu[k]:.4g} |" for k in order]
RK = "AKQJT98765432"
grid = ["| |" + "|".join(RK) + "|", "|---|" + "---|" * 13]
for i, a in enumerate(RK):
    cells = []
    for j, b in enumerate(RK):
        ra, rb = 12 - i, 12 - j
        if i == j: h = [ra * 4, ra * 4 + 1]
        elif i < j: h = [ra * 4, rb * 4]
        else: h = [rb * 4, ra * 4 + 1]
        cells.append(f"{pk.pct(h):.2f}")
    grid.append(f"|**{a}**|" + "|".join(cells) + "|")
n = json.load(open(os.path.join(R, "lab/nash_hu_holdem.json")))
nt = ["| Stack (BB) | SB jams | BB calls |", "|---|---|---|"] + [f"| {s} | {a:.1%} | {b:.1%} |" for s, a, b in n["summary"]]
nt.append("\nPer-hand maximum depths are in `lab/nash_hu_holdem.json`.")
parts = []
for f in FILES:
    src = open(os.path.join(R, f), encoding="utf-8").read().rstrip("\n")
    assert "````" not in src or f.endswith(".md"), f
    parts.append(f"<!-- FILE: {f} -->\n````{LANG.get(os.path.splitext(f)[1], '')}\n{src}\n````\n")
t = open(os.path.join(R, "docs/prompt_template.md"), encoding="utf-8").read()
t = t.replace("{{PARAMS_TABLE}}", "\n".join(rows)).replace("{{PCT_GRID}}", "\n".join(grid)).replace("{{NASH_TABLE}}", "\n".join(nt))
t = t.replace("{{EXTRACTOR}}", open(os.path.join(R, "tools/extract.py")).read().rstrip()).replace("{{FILES}}", "\n".join(parts))
open(os.path.join(R, "docs/BUILD_PROMPT.md"), "w", encoding="utf-8").write(t)
print("wrote docs/BUILD_PROMPT.md", len(t) // 1024, "KB", len(FILES), "files")
