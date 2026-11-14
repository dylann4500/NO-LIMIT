# The portal in Dylan's signed-in browser (14 November, evening Pacific)

Read-only pass in one new Chrome tab, closed afterwards. Only navigation links, the competition switcher and display
tabs (Standings/Teams, Bot/Build box/Members) were clicked. Nothing was uploaded, activated, saved, claimed or sent.
No page contained text addressed to an AI or assistant.

## 1. Dashboard and competitions

- `/tournament` lands on the Bay Area dashboard (148 teams, 127 bots ready, 6 scored rounds, avalon 6 of 148).
- **No announcement banner** on any page visited (dashboard, Format, Getting started, team, rounds, RedZone,
  leaderboard), in either competition.
- The **Competition** switcher lists two competitions: **Bay Area** and **Finals**. Selecting Finals switches the
  sidebar to it (this may also be remembered as the browser's current competition).

## 2. The Finals competition (visible to the account, not yet to the API key)

- Competition id **`2f3668a3-3649-408a-b3ea-1d0021671f4b`**; avalon's Finals team id
  **`2342bf56-c044-44a1-943f-1256e1f6da84`** (different from the Bay Area team id `9785bcf3-...`).
- Dashboard: **21 teams**, 0 bots ready, 0 scored rounds, "Not ranked yet", "No rounds yet". Rounds page: 0 rounds.
  Leaderboard: "The leaderboard starts when the first scored round finishes." RedZone: "REDZONE WILL BEGIN HERE
  AUTOMATICALLY."
- **Teams (21)**: 0_o GTO Slop (1/2 members), 2 Curry, AEPi AK, avalon, AZ (1/2), BHTG, Claude Mythos 5.5, Cold Decks,
  Du-o, Hold Em Trophies, Hotwheels, Lemonade, LLinusLLoveBot, Magnus RLsen, Pluto, Poker is all you need, Preesh,
  sandylikesfrogs, Situational Awareness (1/2), Team 72, Team 123. Bay Area regulars present: 2 Curry, Lemonade, AZ,
  sandylikesfrogs, Team 72, avalon, Team 123 (Bay Area ranks 1-7).
- **Format page (Finals)** — the variant is not announced ("The organizers announce this competition's poker variant
  when the event starts. Its rules and starter kit appear here then, and uploads open."). Otherwise the page is
  word-for-word the Bay Area template:
  - One table: **8 players, 2,000 chips, blinds 10/20, blinds rise every 20 hands, hand cap 250.** No antes listed.
  - Default payouts **50/30/20**, 4th-8th 0; at the hand cap survivors split the remaining points by ICM on stacks.
  - "Default scored round schedule for new rounds": 6 rounds, Build ends, then +20 ... +100 min, weights 1x-6x.
  - 60-minute build; rounds 20 min apart; at least 5,000 iterations a scored round; practice about 1,000 iterations
    every 10 min during the build; final score = sum of round score x "its saved multiplier. The weighting setting
    applies when a new round starts; started rounds keep their multipliers."
  - Bots: "Each upload becomes your active bot once it is ready, unless a newer upload is already active. You can
    switch back to any earlier ready upload." Snapshot at each round's start; no active bot = forfeit, zero; freeze
    pauses uploads and changes; default decision allowance 1 ms; 50 MB upload default.
  - Fairness: random seats each iteration; fillers never score; "Fields smaller than eight play short tables."
    Countback tie-break, nothing by chance.
  - Regionals and finals: regionals in Boston, Stanford and Pittsburgh; five teams from each plus five wildcards;
    "Finals use the same tournament format with a different poker variant."
  - **No mention** of culling, luck correction, a final/held round, a held leaderboard, resampling or antes.
- **Getting started (Finals)** — identical to the Bay Area page except:
  - New block at top: **"Claim $300 in OpenAI credits"**, two separate claim buttons, **$50** and **$250** (not
    clicked).
  - Checklist: "Downloaded the starter kit" has no download link yet (Bay Area shows "download it again").
  - Still says scored rounds play "thousands of 8-player sit-and-go tables" and `play` should fill "the 8 seats a
    round uses".
  - Same: 30 s upload cooldown; upload test = heads-up, up to 20 hands, 1 ms, no time bank, reject at >10% failed
    decisions; passing upload **becomes active automatically** unless frozen or ended; 100 ms per-table time bank,
    emptied by a timeout, full again next table; failed decision = check/fold or the variant's automatic choice; 64 KB
    memory; hand-history download (full or subset) after each round; "A round may draw payouts per table, so read
    payouts rather than assuming 50/30/20."
- **Team page (Finals avalon)**:
  - Bot tab: "Uploads open when the event starts and its variant is announced." Active bot "None yet". "Your newest
    upload that passes its test match becomes active; choose an earlier bot here to play it instead." 0 submissions.
  - **Build box tab: already assigned** — machine `finals-team-6`, `ssh ubuntu@35.171.160.164`; "Your account's SSH
    keys open this machine." (Opening time not shown.)
  - Members: Samuel Choi and Dylan Nguyen, 2 of 2; school field empty, "It locks when the first scored round starts."

## 3. Bay Area pages today vs. the 6 Nov captures and the Boston extract

Format (vs `nolimit-live/prep/docs/portal_format.md`, 6 Nov morning):

| 6 Nov | Today |
|---|---|
| "Select a ready upload as your active bot. An upload alone does not activate it." | "Each upload becomes your active bot once it is ready, unless a newer upload is already active. You can switch back to any earlier ready upload." |
| "Final score is the sum of each round score multiplied by its weight. The last round contributes 6 of the 21 total weight units." | "...multiplied by its saved multiplier. The weighting setting applies when a new round starts; started rounds keep their multipliers." |
| "Default scored round schedule" | "Default scored round schedule for new rounds" |
| Regionals "at Harvard/MIT, Stanford and CMU" | "in Boston, Stanford and Pittsburgh" |
| Variant placeholder | Bay Area variant rules (three hole cards, discard/expose), bot interface, hand-history notes, prize statistics (Empty Bluffer, Shover, Calling Station) |

Everything else on Format is unchanged (8 players, 2,000, 10/20, every 20 hands, cap 250, 50/30/20, ICM at cap,
1 ms, fillers, countback). Today's Bay Area Format matches the Boston extract's wording on activation and saved
multipliers.

Getting started (vs `portal_getting_started.md`): the text is the same, sentence for sentence (30 s cooldown, test
match, automatic activation, 100 ms bank, failed decisions, hand-history download). Only additions: the "download it
again" kit link. No credits block on the Bay Area page; the Finals page offers $300 ($50 + $250) where Boston offered
$50.

Bay Area team page: active bot v10.zip ("Your next upload that passes its test match takes over."), 15 submissions
(one rejected agent.py); **no Build box tab any more** (Bot, Performance, Members only).

No page, Bay Area or Finals, mentions culling, luck correction, a held final round, a held leaderboard or a table
size other than 8.

## 4. Against the working assumption "6 players, 6,000 chips, antes, 250-hand cap, 50/30/20"

- **Contradicts (as displayed defaults):** Finals Format shows **8 players, 2,000 chips, 10/20 with no ante**; Getting
  started says 8-player tables. This is the shared template and the variant is unannounced; rounds can override, and
  the code's `finals` defaults (6 / 6,000 / antes) apply only per round in the organizer's queue. Treat `state.config`
  as the truth.
- **Confirms:** hand cap **250**, payouts **50/30/20** default, blinds every 20 hands.
- **Not shown anywhere:** antes, 6-max, time bank changes, final-round hold, culling.

## 5. Not seen or not clicked

- Variant, RULES.md, kit, round queue for the Finals (not published yet). Build-box opening time.
- Not clicked: credit claim buttons, Upload, Change (active bot), Rename team, glyph, School Save/Clear, New chat,
  Message/Pin buttons, the account menu (holds settings, keys and sign-out), Performance tabs, hand-history downloads.
- Chats: sidebar showed "No conversations yet." on the Bay Area view; not opened further.
