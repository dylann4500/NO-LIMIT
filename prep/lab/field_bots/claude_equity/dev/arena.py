"""Run lab/field_kit/play.py with extra sparring seat kinds (dev/sparring.py) and optional extra bot dirs.
usage: arena.py <bot_dir> [play.py args...] [--extra name=path/to/bot_dir ...]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "lab", "field_kit"))
sys.path.insert(0, HERE)
import play  # noqa: E402  (play.py puts the simulator and fake SDK on sys.path)
import sparring  # noqa: E402

for name, cls in sparring.KINDS.items():
    play.EXAMPLES[name] = (lambda cls=cls: play.Plat([cls()]))
argv = []
args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == "--extra":
        name, path = args[i + 1].split("=", 1)
        A = play.load_agent(path, "extra_" + name)
        play.EXAMPLES[name] = (lambda A=A: play.Plat([A(), A()]))
        i += 2
    else:
        argv.append(args[i])
        i += 1
sys.argv = [sys.argv[0]] + argv
play.main()
