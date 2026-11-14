# cloud/aws/: an EC2 fleet for simulations, evals and tests

> **Shelved on 14 November 2026.** The AWS credits could not be obtained before the Finals, so this tooling was
> never run on AWS and is **not used on Sunday**: the team stays on Modal (`cloud/nl_modal.py`, and the Sunday
> bundle as written). Everything below was tested on local machines only. Kept for a later event.

Big x86 instances (default `c7a.48xlarge`: 192 physical cores, Python 3.12, `uv`) reached over SSH. You push folders,
build the kit's environment, and run one command fanned out over every core of every instance. Results come back
in `cloud/results/`, in the same shape `cloud/nl_modal.py` writes. One stdlib Python file (`fleet.py`) plus the
AWS CLI, `ssh` and `rsync`. It contains no poker code (event rule: infrastructure only).

**Safety, built in:** every resource is tagged `Project=avalon-nl`. Each instance terminates itself at the agreed
deadline (default Sunday 15 Nov 23:00 Pacific) or after 120 minutes with no fleet command and an idle CPU, and its
disk goes with it. SSH is open only to this laptop's current IP. `up` refuses anything past the agreed envelope
(`~/.avalon-aws/envelope.json`), and a budget alert emails at 50% and 100% of gross spend. The kit and bots travel
only over SSH to our own instances: no buckets, no images. Hand histories (`hands-*.jsonl*`, `hand-history/`,
`data/rounds`) are never copied.

## Where this stands (14 Nov, 06:10 PT)

Built and tested on local Ubuntu 24.04 machines: push, build, sharded runs, gathering, failed-shard handling,
queuing, and the minute-0 drill. Nothing has run on AWS yet: nobody has signed in. The steps left, in order:

1. Dylan: `aws login --region us-west-2`, and a yes to the quota requests and the envelope (proposed: us-west-2,
   at most 4 instances / 768 vCPUs / $40 an hour, everything off by Sunday 23:00 PT, budget alert at $300 to an
   address he names).
2. `python3 cloud/aws/fleet.py check`, then `quotas --request` and `setup ...` (steps 2-3 below).
3. Proof run, from a checkout with `starter-kit/` (the main checkout): `cloud/aws/proof.sh 1` (about 10 minutes,
   about $2). Then fill in the "Measured" section of `SUNDAY.md` and decide primary or backup there.
4. `python3 cloud/aws/fleet.py down` unless the instance is wanted for more prep.

`SUNDAY.md` has the recommendation, the Sunday timeline and the text proposed for `finals_pack`.

## Steps, in order (a tired person can follow these)

All commands run from the repo root.

**1. Sign in (Dylan, in Terminal; once per 12 hours).**
```bash
aws login --region us-west-2
```
Sign in in the browser with the account that holds the credits. If you use IAM Identity Center, run
`aws configure sso` instead. Then check:
```bash
python3 cloud/aws/fleet.py check
```
It prints the account, the vCPU quotas, today's price and spot prices, the zones offering the type, the envelope
and anything running. Read-only.

**2. Quotas (once; can take hours, so do it first).** New accounts often start at 5 vCPUs.
```bash
python3 cloud/aws/fleet.py quotas            # show
python3 cloud/aws/fleet.py quotas --request  # file: 768 vCPUs on-demand + spot standard, 64 GPU (G/VT)
```
`quotas` again shows each request's status (`CASE_OPENED`, `APPROVED`, ...). Large increases sometimes become a
support case; the Service Quotas console shows it under "Quota request history".

**3. Setup and envelope (once, after Dylan's yes).**
```bash
python3 cloud/aws/fleet.py setup --email <alert address> --budget-usd 300 \
  --vcpus 768 --instances 4 --usd-h 40 --deadline 2026-11-15T23:00-08:00 --agreed "Dylan, <time>: <his words>"
```
This makes the SSH key pair (the private key stays at `~/.ssh/avalon-nl-aws`), the security group (SSH from this
IP only), the budget alert (gross cost, with credits *excluded*, or it would never fire) and the envelope file.
Add `--dry-run` before `setup` to see the AWS calls without making them.

**4. Start instances.**
```bash
python3 cloud/aws/fleet.py up --count 1                 # on-demand c7a.48xlarge; ~2 minutes to ready
python3 cloud/aws/fleet.py up --count 2 --spot          # cheaper; can be taken back at 2 minutes' notice
python3 cloud/aws/fleet.py up --count 1 --type c7a.16xlarge   # 64 cores, if the quota is still small
```
It tries each zone until it gets capacity, then waits until SSH answers and first-boot setup is done.

**5. Push and build.** `SRC[:DEST]`: `DEST` lands under `~/w/` on every instance, and defaults to the path as given.
```bash
python3 cloud/aws/fleet.py push starter-kit bots cloud    # regional layout; ~1 s for these
python3 cloud/aws/fleet.py push /elsewhere/kit:starter-kit  # a folder from elsewhere, placed at ~/w/starter-kit
python3 cloud/aws/fleet.py build starter-kit    # .venv from requirements.txt, then sdk/* editable (one resolve)
```
Re-push after every bot edit; `rsync` sends only what changed. `build --cmd '...'` runs a different build.

**6. Run.** The command runs in `~/w` once per shard; `{first}`/`{count}` cut `--items` into ranges, `{out}` is the
file each shard must write, and `{shard}`/`{shards}` are also there (as `$FIRST` `$COUNT` `$OUT` `$SHARD` too).
By default each instance runs vCPUs/2 shards at once (`--cores-per-shard`, `--per-host`) and the items are spread
over all slots (`--per-shard` to fix the size). **Use one `--seed` for every shard**, or the shards play different
deals.
```bash
python3 cloud/aws/fleet.py run --name v10_field --items 4000 --merge tables \
  'starter-kit/.venv/bin/python cloud/kit_match.py bots/v10 bots/v10 bots/v9s bots/v9s bots/v6 bots/v6 bots/v3b bots/v3b --seed s1 --tables {count} --first-table {first} --out {out}'
```
Keep the command on one line: each line of it runs as its own shell command.
- It prints progress, then gathers every shard's file into `cloud/results/<name>/out/`, logs into `.../log/`, and with
  `--merge tables` writes `cloud/results/<name>.json`: the `tables` lists joined and sorted, `elapsed_s` summed,
  `bot_stderr` joined, plus `wall_s`, `shard_elapsed_s` and the fleet. That is the shape `nl_modal.py` writes.
- **A failed shard fails the run loudly:** exit 1, the first five failing logs printed, and the merge goes to
  `<name>.partial.json`, never `<name>.json`.
- `--detach` starts the run and returns; `collect <name> --merge tables` waits and gathers later. Agents use this
  (never block a turn). Only one run at a time per fleet (`--force` to share the cores).
- Anything else: `python3 cloud/aws/fleet.py sh 'uptime; df -h ~'`.

**7. Look, then stop.**
```bash
python3 cloud/aws/fleet.py status      # instances, $/h, $ so far, load, recent runs
python3 cloud/aws/fleet.py down        # terminate everything this tool started (or --fleet NAME)
```
If the laptop dies, nothing keeps billing past the deadline. If you are not sure, run `status`: it lists
everything tagged `Project=avalon-nl` in the region.

## When something goes wrong

| Symptom | Fix |
|---|---|
| `Not signed in` / `ExpiredToken` | `aws login --region us-west-2` again (sessions last up to 12 h) |
| `VcpuLimitExceeded` on `up` | quota still low: `quotas` shows it; use a smaller `--type`, or Modal |
| `InsufficientInstanceCapacity` in every zone | `--type c7i.48xlarge` or `c6a.48xlarge` (also x86), or `--spot` off/on |
| SSH times out at a venue | the network blocks port 22: `export AVALON_SSH_PORT=443` (instances listen on both) |
| SSH refused after a Wi-Fi change | every command re-opens the security group to the new IP; if the venue rotates IPs per connection, `export AVALON_SSH_CIDR=<venue range>/24`, or use a phone hotspot |
| every decision fails, `No module named eval7` | an ARM instance: the kit installs eval7 on x86_64 only. Keep to c7a/c7i/c6a |
| a run looks stuck | `sh 'ls ~/runs/<name>/log | wc -l; tail -3 ~/runs/<name>/log/*.log'` |

## Local test without AWS (how this was checked)

`AVALON_FLEET_HOSTS="ubuntu@127.0.0.1:2201,ubuntu@127.0.0.1:2202"` makes every command use those SSH hosts instead of
EC2 (for example two Ubuntu 24.04 containers running sshd with `~/.ssh/avalon-nl-aws.pub` authorized). The 14 Nov
check pushed the regional kit, built it, and ran kit example bots and a failing-shard case through `run`/`collect`.
On ARM containers the regional bots fail every decision (no eval7 wheel), which is why EC2 stays on x86.

## Why this design (14 Nov comparison)

| | Big instances over SSH (this) | AWS Batch / ECS on EC2 | Fargate | Modal (today's tool) |
|---|---|---|---|---|
| Set-up before Sunday | an hour (done) + quota wait | compute env, queue, job definition, ECR image, 3 IAM roles: a day to trust | same, and 16 vCPU per task max | done, rehearsed |
| New kit at minute 0 to first result | push 1 s + build ~1 min + run | rebuild image, push to ECR, jobs pull it: several minutes | same plus slower task starts | image rebuild ~2-3 min, then run |
| Per-run overhead | ~1 s (processes on a warm box) | container scheduling, tens of seconds | 30-90 s task start | container start + slowest shard (4,000 tables: 103 s wall for ~40 s of work) |
| Ceiling | quota (768 vCPU asked) | quota | quota | team cap 80 containers, app-creation rate limit |
| Event-day failure modes | venue blocks SSH (443 fallback), IP changes (auto-fixed), quota/capacity | all of these plus image/role mistakes | same | Modal outage/rate limit; known from rehearsals |
| Price | c7a.48xlarge $9.85/h on-demand = $0.051 per core-hour; spot less; **paid by credits** | same EC2 price | ~2x per vCPU | $0.047 per physical core-hour + memory, paid by us |

GPUs do not help: the load is CPU-bound Python (the kit's engine, pokerkit, bot processes), with no tensor maths
in a simulation. A GPU instance helps only if someone trains a neural network, and the kit's requirements install
CPU-only torch. The GPU quota request exists only to keep that door open.

Graviton (`c8g`, ARM) is cheaper per core, but the kit installs `eval7` only on x86_64, so the regional bots break
there. Stay on x86.
