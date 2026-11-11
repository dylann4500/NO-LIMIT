# Data

The tournament hand histories live in `data/hands/` on the machine that ran the event. They are **not in git**: each scored-round file is 260-275 MB (over GitHub's 100 MB file limit), and they contain other teams' play. Back them up separately. The originals were downloaded to `~/Downloads/`.

Format: line 1 is a header (`tournament_id`, `you` = our entry id, `entries` = every team's entry id and name). After that come pairs of lines: one table record (seats, payouts, every hand's events, stacks and ICM point equity before and after) and one `you` record (our three dealt cards per hand, kept/discarded cards, and `automatic`, the decisions the platform made for us after a failure). Event semantics are in `research/post_event/round6_attribution/extract.py`'s docstring.

## Scored rounds (about 20,150 tables each, avalon at every table)

| Round | Weight | Bot | File | Our points/table |
|---|---|---|---|---|
| 1 | ×1 | v3b | `hands-3e3dcc02-ca4f-48c5-9acb-6c0e3a32c10e.jsonl.gz` | 18.10 |
| 2 | ×2 | v5r | `hands-547666b1-3877-4bac-9925-17e1e78134da.jsonl.gz` | 16.73 |
| 3 | ×3 | v6 | `hands-260d2303-7878-4df1-867e-05f8d2a10d01.jsonl.gz` | 19.05 |
| 4 | ×4 | v7 | `hands-250d256c-6794-4e24-957e-c258286fc25b.jsonl.gz` | 18.26 |
| 5 | ×5 | v9s | `hands-2390e159-4598-4771-a21c-3326b7a18e68.jsonl.gz` | 17.95 |
| 6 | ×6 | v10 | `hands-729b67f6-dc91-4a48-9ad7-f5f62fb79941.jsonl.gz` | 17.53 |

The mapping was verified by recomputing our points per table from each file (all within 0.03 of the official score). Each scored file also has a `-first-1000` sample downloaded a few minutes earlier, except round 6.

## Practice rounds (30,850 tables, avalon at every table)

All eight files list the same 148 entries, avalon included, so they are practice rounds of our tournament. (An earlier note in `research/competitors/REPORT.md` guessed two of them were other tournaments; the entry lists say otherwise.) Listed by download time on 2026-11-06; which practice round each one is was not recorded.

| Downloaded | Tables | File |
|---|---|---|
| 18:42 | 1,042 | `hands-5da6d631-2bcf-4fe2-9e7a-01b9e8ecac75.jsonl.gz` |
| 18:53 | 2,589 | `hands-af2a0969-cd0a-4124-875b-84ff690a2a6d.jsonl.gz` |
| 19:08 | 10,393 | `hands-bd8406dc-0f95-4cd3-8015-7ef8acf3898c.jsonl.gz` |
| 19:18 | 12,797 | `hands-4d1fe6fb-7336-4745-bfb4-cd0e565fb552.jsonl.gz` (+ `-first-1000`) |
| 19:55 | 1,004 | `hands-74eb2fd7-8ade-46fb-8e6a-6a099170b812.jsonl.gz` |
| 20:15 | 1,007 | `hands-4acb36cf-7869-47d6-b4e7-e5de8e634956.jsonl.gz` |
| 20:35 | 1,005 | `hands-925e7be1-31e3-4101-af96-fcb2f78bad37.jsonl.gz` |
| 20:57 | 1,013 | `hands-13040f56-85d7-4be5-9421-d929abd48da8.jsonl.gz` |

**Total:** 120,947 scored-round tables + 30,850 practice tables = 151,797 tables (the `-first-1000` files are subsets and not counted). Each table runs about 90 hands; the scored rounds alone hold about 10.9 million hands dealt to us.

## Other local data not in git

- `~/Documents/GitHub/pokerbot/league/` (1.4 GB): generated league and self-play output from pre-event training. Regenerable with the scripts in `prep/lab/`.
