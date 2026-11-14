# AWS on Sunday: recommendation and proposed text for finals_pack

> **Shelved on 14 November 2026.** The AWS credits could not be obtained before the Finals, so this tooling was
> never run on AWS and is **not used on Sunday**: the team stays on Modal (`cloud/nl_modal.py`, and the Sunday
> bundle as written). Everything below was tested on local machines only. Kept for a later event.

Status 14 Nov 06:15 PT: the tooling works end to end on local test machines (push, build, sharded run, gather,
failure handling). **Not measured on AWS yet**: nobody has signed in, so the quotas, the real throughput and the
minute-0 drill are unknown. The "Measured" section below gets filled in when the proof run happens.

## Recommendation

**Backup, becoming primary only if two conditions hold by Sunday 09:00 PT:**
1. the EC2 quota is at least 192 vCPUs (one c7a.48xlarge), and
2. the proof run below matched Modal's results and beat its wall time.

Until both hold, Modal stays the only compute, exactly as `finals_pack` says today. Why not primary right away:
Modal is rehearsed and the tester's prompts are written for it, while AWS has never run a real table for us.
New accounts often start at 5 vCPUs, and the increase can take hours.

Why it is worth having:
- **No 80-container cap and no app-creation rate limit.** That rate limit cost a rehearsal a round.
- **Warm machines.** A run is processes on a box that is already up: no container start and no image build.
  Modal's 4,000-table run spent 103 s of wall time on about 40 s of play, waiting on starts and the slowest shard.
- **The tester's target fits.** "20,000 tables for 3-4 candidates in 5 minutes" needs 200-270 tables a second. The
  only Modal figure measured so far is about 50 a second. One c7a.48xlarge has 192 physical cores; the per-core speed
  is measured below.
- **The credits pay.** Two c7a.48xlarge for 6 hours cost about $120 at list price.

Risks on the day, with their fixes:

| Risk | Fix |
|---|---|
| Venue Wi-Fi blocks port 22 | `export AVALON_SSH_PORT=443` |
| The laptop's IP changes | handled: every command re-opens SSH to the new IP |
| Venue rotates IPs per connection | `AVALON_SSH_CIDR`, or a phone hotspot |
| `aws login` expires (12 h at most) | sign in on Sunday morning, not Saturday night |
| No capacity in a zone | `up` tries every zone, then fall back to `--type c7i.48xlarge` |

GPUs: no. Nothing on Sunday trains a network, and the kit installs CPU-only torch.

## Sunday timeline (if AWS is in play)

| When | Who | What |
|---|---|---|
| ~T-2h before minute 0 | Dylan, any tab | `aws login --region us-west-2`, then `python3 scripts/fleet/fleet.py check` |
| ~T-90 min | Dylan | `python3 scripts/fleet/fleet.py up --count 2` (≈2 min). Then warm the install cache with the regional kit: `python3 scripts/fleet/fleet.py push ~/Documents/GitHub/nolimit-live/starter-kit:warm-kit && python3 scripts/fleet/fleet.py build warm-kit`. The Finals kit's requirements are probably the same pinned versions, so its build at minute 0 is mostly cached |
| minute 0, once the kit is in `starter-kit/` | tester (via RESEARCH) | `fleet.py push starter-kit && fleet.py build starter-kit` (about a minute) |
| build hour and windows | tester | `fleet.py push bot candidates rig`, then `run --detach`, later `collect` |
| after the last round | Dylan | `python3 scripts/fleet/fleet.py down`, then `status` shows nothing. The deadline (23:00) and the 2-hour idle rule stop anything that was missed |

**The one command the tester runs** (after `push`):
```bash
AVALON_RESULTS=rig/out/fleet python3 scripts/fleet/fleet.py run --detach --name v3-vs-v2 --items 20000 --merge tables 'starter-kit/.venv/bin/python rig/compare.py LIVE CAND --field F --seed S --tables {count} --first-table {first} --out {out}'
```
then `AVALON_RESULTS=rig/out/fleet python3 scripts/fleet/fleet.py collect v3-vs-v2 --merge tables` →
`rig/out/fleet/v3-vs-v2.json`. This only asks one thing of `rig/compare.py`: it plays a table range from a fixed
seed and writes a JSON with a `tables` list.

## Proposed text changes (for the lead; nothing under finals_pack/ was edited)

**0. Files.** Copy `cloud/aws/fleet.py` and `cloud/aws/userdata.sh` to `finals_pack/scripts/fleet/`. They are
infrastructure only (no poker code), so the event rule allows them. Add `rig/out/fleet/` to `.gitignore`.

**1. `finals_pack/CLAUDE.md` §4, rule 8: replace with**
> 8. **Compute: Modal, and the AWS fleet if Dylan started one.** Modal: one app per purpose (deploy once and call it
> many times, or one `modal run` that fans out with `.map`). Never launch several `modal run`s at once: the workspace
> has an app-creation rate limit, and a rehearsal lost a round to it. Shared cap: 80 containers. AWS fleet
> (`scripts/fleet/fleet.py`, instances of 192 cores, paid by credits): only `tester` runs on it, one run at a time
> (`run --detach`, later `collect`); `status` is free; never `up`, `down` or `setup` unless a human asks.

**2. `finals_pack/CLAUDE.md` §7, CPU bullet: change "go to Modal (one app per purpose)" to**
> go to the AWS fleet when `python3 scripts/fleet/fleet.py status` shows instances (through `tester`), else to
> Modal (one app per purpose)

**3. `finals_pack/.claude/agents/tester.md`, build hour: replace the `**Modal:**` bullet with**
> - **Compute.** `python3 scripts/fleet/fleet.py status` first. **If it lists instances** (the AWS fleet, 192 cores
>   each, started by Dylan before minute 0), use it first. At minute 0, once the kit is in `starter-kit/`, run
>   `fleet.py push starter-kit && fleet.py build starter-kit` (about a minute). Write `rig/compare.py` so one call plays
>   a table range: `--tables N --first-table F --seed S --out FILE`, writing JSON with a `tables` list. Before
>   each run, `fleet.py push bot candidates rig`. Then
>   `AVALON_RESULTS=rig/out/fleet python3 scripts/fleet/fleet.py run --detach --name <x> --items 20000 --merge tables 'starter-kit/.venv/bin/python rig/compare.py ... --seed S --tables {count} --first-table {first} --out {out}'`,
>   and later the same with `collect <x> --merge tables` (`rig/out/fleet/<x>.json`). One run at a time; a failed
>   shard fails the run loudly (`<x>.partial.json`). If SSH fails, try `AVALON_SSH_PORT=443` once. If it still
>   fails, tell your spawner "fleet unreachable" and use Modal.
> - **Modal** (when there is no fleet, or as overflow): one app `avalon-rig` ... *(the current text, unchanged)*

**4. `finals_pack/START.md`**
- Saturday night, step 2, add: `aws` signed in once (`aws login --region us-west-2`), and
  `python3 scripts/fleet/fleet.py check` shows the account, a quota of at least 192 vCPUs and the envelope.
- "Sunday, 2-3 hours before the start": add a paragraph after the table:
  > **AWS fleet (if it passed Saturday's checks):** in any tab, `aws login --region us-west-2`, then
  > `python3 scripts/fleet/fleet.py up --count 2`, then warm it:
  > `python3 scripts/fleet/fleet.py push ~/Documents/GitHub/nolimit-live/starter-kit:warm-kit && python3 scripts/fleet/fleet.py build warm-kit`.
  > After the last round: `python3 scripts/fleet/fleet.py down`.
- "When something goes wrong", add a row: | AWS fleet unreachable (tester says so) | `export AVALON_SSH_PORT=443` in the session's tab, or tell RESEARCH "no fleet, Modal only" |

## Measured

*(to be filled in by the proof run: the regional kit and bots, the same field and table counts as `cloud/README.md`
(4,000 tables, v10/v9s/v6/v3b ×2), tables per minute, $ per 1,000 tables, and the minute-0 drill: fleet up, fresh
kit pushed and built, first 1,000 tables back)*
