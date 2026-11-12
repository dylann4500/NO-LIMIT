# Our regional
- Opponents were recognisable from their exact bet sizes: with last round's profiles we could name most
  seats within 20 hands. Plan: embed a profile per team (sizes, fold to re-raise, fold to bets by street)
  built from the downloads, score each seat against the profiles as hands go by, blend with live counts.
- Per-seat counters at the table: fold to re-raise, fold to bet by street, how often a seat bets when
  checked to. Exploit the big gaps only.
- Teams change bots every round, so rebuild profiles from the newest download each window.
- If stuck mid-table after two rounds: a fresh rewrite in parallel, switch if it tests better.
