"""finalize.py FIELD EPS BETA : write standalone kit bot folders FIELD/kit_teams/<slug>/ whose
params.json carries the calibrated cells (adj.json), strength maps (cdf.json), eps and beta, so
each folder runs under poker-agent play / cloud/kit_match.py / emu/tournament.py unchanged."""
import json, os, shutil, sys
field, eps, beta = sys.argv[1], float(sys.argv[2]), [0.0] + [float(x) for x in sys.argv[3].split(",")]
F = json.load(open(os.path.join(field, "field.json")))
cdf = json.load(open(os.path.join(field, "cdf.json")))
adj = json.load(open(os.path.join(field, "adj.json")))
out = os.path.join(field, "kit_teams")
shutil.rmtree(out, ignore_errors=True)
emu = {"name": "clone field from " + F["source"], "rules": {"variant": "flop_discard_reveal", "players": 8}, "entries": []}
for e in F["entries"]:
    src = os.path.join(field, e["folder"])
    dst = os.path.join(out, os.path.basename(e["folder"]))
    shutil.copytree(src, dst)
    p = json.load(open(os.path.join(src, "params.json")))
    p["fitted_cells"] = p["cells"]
    p["cells"] = adj.get(e["team"], p["cells"])
    p["cdf"], p["eps"], p["beta"] = cdf, eps, beta
    json.dump(p, open(os.path.join(dst, "params.json"), "w"))
    emu["entries"].append({"team": e["team"], "bot": dst})
json.dump(emu, open(os.path.join(field, "emu_field.json"), "w"), indent=1)
print(len(F["entries"]), "folders ->", out)
