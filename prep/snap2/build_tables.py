"""Regenerate a variant's starting-hand table. usage: POKER_VARIANT=x python build_tables.py"""
import pk
if __name__ == "__main__":
    secs, n = pk.build_table()
    print(f"{pk.VARIANT}: {n} hand classes in {secs:.1f}s, wrote {pk._TABLE_PATH}")
