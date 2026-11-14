"""The clock's schedule: defaults match the old fixed format; a longer build, a different gap and a pinned (late) round
move every later step, stage label and deadline window. Run: python tests/eval/unit_schedule.py hub"""
import sys
sys.path.insert(0, sys.argv[1])
import hub as H

fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name); cond or fails.append(name)

U = 60
s = {"start": 0.0, "scored": 6, "scale": 1.0}
check("default rounds at 60, 80, ..., 160", H.round_starts(s) == [(60 + 20 * k) * U for k in range(6)])
check("default practices at 20/30/40/50", [H.build_ts(s, m) for m in (20, 30, 40, 50)] == [20 * U, 30 * U, 40 * U, 50 * U])
old = lambda m: "Build" if m < 20 else f"Practice {int((m - 20) // 10) + 1}" if m < 60 else None
check("default stage labels unchanged", all(H.stage_of(s, m * U) == (old(m) or H.stage_of(s, m * U)) for m in range(0, 60)))
check("stage after round 1: Round 1 then Round 1.5", H.stage_of(s, 65 * U) == "Round 1" and H.stage_of(s, 71 * U) == "Round 1.5")
check("no Round 6.5", H.stage_of(s, 175 * U) == "Round 6")
b = dict(s, build=90, gap=30)
check("90-min build, 30-min gap", H.round_starts(b)[:3] == [90 * U, 120 * U, 150 * U])
check("practice marks follow the end of a longer build", H.build_ts(b, 20) == 50 * U and H.build_ts(b, 50) == 80 * U)
check("v1 deadline stays at minute 10", H.build_ts(b, 10) == 10 * U)
check("stage at minute 45 of a 90-min build is Build", H.stage_of(b, 45 * U) == "Build")
p = dict(s, round_at={"3": 110 * U})   # round 3 ten minutes late
rs = H.round_starts(p)
check("pinned round 3 late: 1-2 unchanged, 3-6 shifted 10 min", rs == [60 * U, 80 * U, 110 * U, 130 * U, 150 * U, 170 * U])
check("practice before round 3 follows the pin", H.practice_ts(p, 2) == 100 * U)
check("stage 'Round 2' stays until the moved practice", H.stage_of(p, 95 * U) == "Round 2" and H.stage_of(p, 101 * U) == "Round 2.5")
check("round_ts out of range is None", H.round_ts(p, 7) is None and H.round_ts(None, 1) is None)
print("FAILED:", [f for f in fails] or "none")
sys.exit(1 if fails else 0)
