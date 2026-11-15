"""The two table formats the rehearsal can play: the regional's and the Finals'. Plain data, no imports, so the
rehearsal (prep venv), the round runner (kit venv, locally and on Modal) and the kit builder all read the same thing.

  regional: 8 players, 2,000 chips, blinds 10/20 .. 2000/4000 (no antes), as at Bay Area on 6 Nov.
  finals:   6 players, 6,000 chips, blinds and antes 10/20/4 .. 2000/4000/800, the organizers' `finals` defaults
            (finals_pack/prep/PORTAL_FINDINGS_14NOV.md, section 1). Both: 20 hands a level, 250-hand cap,
            50/30/20, 1 ms a decision, 100 ms time bank.

`rules(table, variant)` is a TableRules dict (poker_engine.table.rules_from_dict) for a round's field file.
"""

REGIONAL_BLINDS = [(10, 20, 0), (20, 40, 0), (30, 60, 0), (50, 100, 0), (80, 160, 0), (125, 250, 0), (200, 400, 0),
                   (300, 600, 0), (500, 1000, 0), (800, 1600, 0), (1200, 2400, 0), (2000, 4000, 0)]
FINALS_BLINDS = [(10, 20, 4), (20, 40, 8), (30, 60, 12), (50, 100, 20), (80, 160, 32), (125, 250, 50),
                 (200, 400, 80), (300, 600, 120), (500, 1000, 200), (800, 1600, 320), (1200, 2400, 480),
                 (2000, 4000, 800)]

TABLES = {
    "regional": {"players": 8, "starting_stack": 2000, "blinds": REGIONAL_BLINDS},
    "finals": {"players": 6, "starting_stack": 6000, "blinds": FINALS_BLINDS},
}
COMMON = {"hands_per_level": 20, "hand_cap": 250, "payouts": [50, 30, 20], "decision_ms": 1, "time_bank_ms": 100}


def rules(table: str, variant: str) -> dict:
    t = TABLES[table]
    return {"variant": variant, "players": t["players"], "starting_stack": t["starting_stack"],
            "blinds": [list(b) for b in t["blinds"]], **COMMON}


def blinds_text(table: str) -> str:
    """'10/20/4, 20/40/8, ...' (finals) or '10/20, 20/40, ...' (regional)."""
    return ", ".join("/".join(str(x) for x in (b if b[2] else b[:2])) for b in TABLES[table]["blinds"])


def format_rows(table: str) -> str:
    """The Format page's "One table" rows."""
    t = TABLES[table]
    first = t["blinds"][0]
    start = f"{first[0]} / {first[1]}" + (f" / {first[2]} ante" if first[2] else "")
    rows = [("Players", str(t["players"])), ("Starting stack", f"{t['starting_stack']:,} chips"),
            ("Starting blinds" + (" and ante" if first[2] else ""), start)]
    if first[2]:
        rows.append(("Blinds and antes (small / big / ante)", blinds_text(table) + " (the last level repeats)"))
        rows.append(("Antes", "Every player posts the ante every hand"))
    rows += [("Blind increases", f"Every {COMMON['hands_per_level']} hands"), ("Hand cap", str(COMMON["hand_cap"])),
             ("Decision time", f"{COMMON['decision_ms']} ms, plus a {COMMON['time_bank_ms']} ms time bank per table")]
    return "\n".join(["| | |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows])


WORDS = {6: "six", 8: "eight"}
