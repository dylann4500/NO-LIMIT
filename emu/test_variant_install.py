"""Local check (no Modal) that a mock Finals variant is installed wherever the rehearsal needs it.

  prep/.venv/bin/python emu/test_variant_install.py [variant]      # default turn_draw_holdem

Builds the run's mock kit (emu/variants/make_kit.py) in a temp dir, gives a team its kit copy the
way rehearsal.py does (run_team.kit_files), then checks with the starter kit's Python:
  1. load_variant(<variant>) works with the team's kit, and the engine is the kit's own;
  2. a 2-seat table plays a few hands with the kit's example bots (cloud/kit_match.py);
  3. a 2-entry round on the round runner (emu/tournament.py play + merge) writes downloads;
  4. the upload test plays the variant with that kit;
  5. the Modal round image would hold the module (modal_rounds with EMU_KIT; no app is created);
  6. the portal pages carry the cooldown and the Format page renders.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMU = ROOT / "emu"
KITPY = str(ROOT / "starter-kit" / ".venv" / "bin" / "python")
sys.path[:0] = [str(EMU), str(EMU / "teams"), str(EMU / "variants")]
import run_team  # noqa: E402
from make_kit import kit_env  # noqa: E402
from pilot import upload_test  # noqa: E402


def main() -> None:
    variant = sys.argv[1] if len(sys.argv) > 1 else "turn_draw_holdem"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp).resolve()
        build = tmp / "kit_build"
        subprocess.run([KITPY, str(EMU / "variants" / "make_kit.py"), variant, str(build)], check=True,
                       stdout=subprocess.DEVNULL)
        kit = tmp / "team" / "kit"
        run_team.kit_files(kit, EMU / "variants" / f"{variant}.md", build)
        assert (kit / "sdk/engine/src/poker_engine/variants" / f"{variant}.py").is_file()
        env = kit_env(kit)

        # 1. load_variant from the team's kit
        r = subprocess.run([KITPY, "-c", "import poker_engine; from poker_engine.variant import load_variant; "
                            f"load_variant({variant!r}); print(poker_engine.__file__)"],
                           env=env, capture_output=True, text=True, check=True)
        engine = Path(r.stdout.split()[-1]).resolve()
        assert engine.is_relative_to(kit.resolve()), engine
        print(f"1. load_variant({variant}) ok from {engine.relative_to(tmp)}")

        # 2. a 2-seat table with the kit's examples
        out = tmp / "match.json"
        subprocess.run([KITPY, str(ROOT / "cloud/kit_match.py"), "--variant", variant, "--tables", "2",
                        "--hand-cap", "15", "--copies", "1", "--out", str(out),
                        str(kit / "examples/check_or_fold"), str(kit / "examples/min_raiser")],
                       env=env, check=True, capture_output=True, text=True)
        res = json.loads(out.read_text())
        assert res["rules"]["variant"] == variant, res["rules"]
        decs = sum(sum(t["decisions"].values()) for t in res["tables"])
        fails = sum(sum(t["failures"].values()) for t in res["tables"])
        assert decs > 0, res["tables"]
        print(f"2. 2-seat tables: {len(res['tables'])} played, {decs} decisions, {fails} failed")

        # 3. the round runner (tournament.py) with the run kit, 2 entries
        field = {"name": "test", "rules": {"variant": variant, "players": 8},
                 "entries": [{"team": "avalon", "bot": str(kit / "examples/min_raiser")},
                             {"team": "other", "bot": str(kit / "examples/check_or_fold")}]}
        (tmp / "field.json").write_text(json.dumps(field))
        subprocess.run([KITPY, str(EMU / "tournament.py"), "play", "--field", str(tmp / "field.json"), "--seed", "t",
                        "--first-iteration", "0", "--iterations", "2", "--out", str(tmp / "shard0"),
                        "--concurrency", "2"], env=kit_env(build), check=True, capture_output=True)
        subprocess.run([KITPY, str(EMU / "tournament.py"), "merge", "--field", str(tmp / "field.json"),
                        "--round", "1", "--out", str(tmp / "round"), str(tmp / "shard0")],
                       env=kit_env(build), check=True, capture_output=True)
        summary = json.loads((tmp / "round" / "round.json").read_text())
        dls = sorted(p.name for p in (tmp / "round" / "downloads").rglob("*.gz"))
        assert set(summary["scores"]) == {"avalon", "other"} and dls, (summary, dls)
        print(f"3. round runner: scores {', '.join(f'{t} {v['points']:.1f}' for t, v in summary['scores'].items())}; "
              f"{len(dls)} download files")

        # 4. the upload test in the variant
        t = upload_test(kit / "examples/check_or_fold", variant, build)
        assert t["ok"], t
        print(f"4. upload test in {variant}: ok ({t['decisions']} decisions)")

        # 5. the Modal round image's SDK (no app is created)
        r = subprocess.run([sys.executable, "-c", "import modal_rounds as m; print(m.KIT); "
                            f"print(m.image_has_variant({variant!r}))"],
                           env={**os.environ, "EMU_KIT": str(build), "PYTHONPATH": str(EMU)},
                           capture_output=True, text=True, check=True)
        assert Path(r.stdout.split()[0]) == build, r.stdout
        print(f"5. Modal round image: built from the run kit, has {variant}.py")

        # 6. portal pages: cooldown and Format rendering
        run_team.portal_files(tmp / "portal", "Turn draw", "rules here", cooldown=45)
        fmt = (tmp / "portal" / "format.md").read_text()
        assert "once every 45 seconds" in fmt and "{{" not in fmt
        import portal_server
        html = portal_server.md_html(fmt)
        assert "<table>" in html and "<h2>Turn draw</h2>" in html and "45 seconds" in html
        print("6. portal: cooldown on the Format page; Format renders")
    print("all checks passed")


if __name__ == "__main__":
    main()
