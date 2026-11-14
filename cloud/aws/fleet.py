#!/usr/bin/env python3
"""A small EC2 fleet for CPU-bound test runs: big instances over SSH, a process pool on each.

Infrastructure only: it starts machines, copies folders, runs a command on every core and brings
files back. Nothing in it knows about poker. Python standard library + the AWS CLI + ssh/rsync.

  python3 cloud/aws/fleet.py check                      # sign-in, quotas, prices, what is running (read-only)
  python3 cloud/aws/fleet.py setup --email X            # once: key pair, security group, budget alert
  python3 cloud/aws/fleet.py up --count 2               # start instances (c7a.48xlarge, 192 cores each)
  python3 cloud/aws/fleet.py push PATH[:DEST] ...       # copy folders to ~/w/DEST on every instance
  python3 cloud/aws/fleet.py build starter-kit          # make DEST/.venv from its requirements.txt (+ sdk/*)
  python3 cloud/aws/fleet.py run --name R --items 4000 'CMD with {first} {count} {out}'
  python3 cloud/aws/fleet.py sh 'uptime'                # any command on every instance
  python3 cloud/aws/fleet.py status
  python3 cloud/aws/fleet.py down                       # terminate everything this tool started

Every instance carries the tag Project=avalon-nl, powers itself off (= terminates) at the deadline or
after --idle-min minutes unused, and accepts SSH only from this laptop's current IP.
The envelope Dylan agreed lives in ~/.avalon-aws/envelope.json; `up` refuses to go past it.
README.md (same folder) is the walk-through.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Results land here: $AVALON_RESULTS, else ./cloud/results when run from this repo's root, else ./fleet-results.
RESULTS = Path(os.environ.get("AVALON_RESULTS") or
               ("cloud/results" if Path("cloud").is_dir() else "fleet-results")).resolve()
STATE = Path.home() / ".avalon-aws"
KEY = Path.home() / ".ssh" / "avalon-nl-aws"
KEY_NAME = "avalon-nl"
SG_NAME = "avalon-nl-ssh"
BUDGET_NAME = "avalon-nl"
PROJECT = "avalon-nl"
REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-west-2"
UBUNTU_AMI_PARAM = "/aws/service/canonical/ubuntu/server/24.04/stable/current/{arch}/hvm/ebs-gp3/ami-id"
QUOTAS = {  # EC2 quota codes (vCPUs) and what they cover
    "L-1216C47A": "on-demand standard (A,C,D,H,I,M,R,T,Z)",
    "L-34B43A08": "spot standard (A,C,D,H,I,M,R,T,Z)",
    "L-DB2E81BA": "on-demand G and VT (GPU)",
    "L-3819A6DF": "spot G and VT (GPU)",
}
# Never copied to an instance (same spirit as cloud/nl_modal.py NEVER): hand histories, venvs, caches.
NEVER = [".venv", "__pycache__", "*.pyc", ".DS_Store", "hand-history", "hands-*.jsonl*", "*.jsonl.gz",
         "data/rounds", ".git", "results"]
SSH_PORT = os.environ.get("AVALON_SSH_PORT", "22")  # 443 when the network blocks 22 (instances listen on both)
TEST_HOSTS = os.environ.get("AVALON_FLEET_HOSTS", "")  # "user@host:port,..." skips EC2 (local tests only)
DRY = False


# ---------------------------------------------------------------- small helpers

def say(msg: str) -> None:
    print(msg, flush=True)


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def aws(*args: str, mutate: bool = False, check: bool = True, region: str = "") -> dict | list | str:
    """Run the AWS CLI and return parsed JSON. With --dry-run, mutating calls are printed, not run."""
    cmd = ["aws", *args, "--output", "json", "--region", region or REGION]
    if mutate and DRY:
        say("DRY-RUN would run: " + " ".join(shlex.quote(c) for c in cmd))
        return {}
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        if check:
            die(f"{' '.join(cmd[:3])}: {p.stderr.strip()[-1500:]}")
        return {"_error": p.stderr.strip()}
    return json.loads(p.stdout) if p.stdout.strip() else {}


def envelope() -> dict:
    f = STATE / "envelope.json"
    if not f.exists():
        die(f"No spending envelope in {f}. Dylan agrees one first; see cloud/aws/README.md step 3.")
    return json.loads(f.read_text())


def my_ip() -> str:
    with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=10) as r:
        return r.read().decode().strip()


# ---------------------------------------------------------------- instances

def instances(states=("pending", "running")) -> list[dict]:
    """This tool's instances (tag Project=avalon-nl), oldest first."""
    if TEST_HOSTS:
        out = []
        for i, spec in enumerate(TEST_HOSTS.split(",")):
            user_host, _, port = spec.partition(":")
            out.append({"id": f"test{i}", "ip": user_host.split("@")[-1], "user": user_host.split("@")[0],
                        "port": port or "22", "type": "test", "vcpus": int(os.environ.get("AVALON_TEST_VCPUS", "4")),
                        "state": "running", "fleet": "test", "price": 0.0, "launched": None, "deadline": "",
                        "spot": False})
        return out
    data = aws("ec2", "describe-instances", "--filters", f"Name=tag:Project,Values={PROJECT}",
               f"Name=instance-state-name,Values={','.join(states)}")
    out = []
    for res in data.get("Reservations", []):
        for inst in res["Instances"]:
            tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
            cpu = inst.get("CpuOptions", {})
            out.append({
                "id": inst["InstanceId"], "ip": inst.get("PublicIpAddress", ""), "user": "ubuntu", "port": SSH_PORT,
                "type": inst["InstanceType"], "vcpus": cpu.get("CoreCount", 0) * cpu.get("ThreadsPerCore", 1),
                "state": inst["State"]["Name"], "fleet": tags.get("Fleet", "?"),
                "price": float(tags.get("PriceUSDh", "0") or 0), "launched": inst["LaunchTime"],
                "deadline": tags.get("Deadline", ""), "spot": inst.get("InstanceLifecycle") == "spot",
                "az": inst["Placement"]["AvailabilityZone"],
            })
    return sorted(out, key=lambda x: x["launched"] or "")


def on_demand_price(itype: str) -> float:
    """Linux on-demand $/h in REGION from the AWS Price List API (0.0 if it cannot be read)."""
    loc = {"us-west-2": "US West (Oregon)", "us-east-1": "US East (N. Virginia)", "us-east-2": "US East (Ohio)",
           "us-west-1": "US West (N. California)"}.get(REGION)
    if not loc:
        return 0.0
    filters = [f"Type=TERM_MATCH,Field={k},Value={v}" for k, v in (
        ("instanceType", itype), ("location", loc), ("operatingSystem", "Linux"), ("tenancy", "Shared"),
        ("preInstalledSw", "NA"), ("capacitystatus", "Used"))]
    data = aws("pricing", "get-products", "--service-code", "AmazonEC2", "--filters", *filters,
               check=False, region="us-east-1")
    for item in (data.get("PriceList") or []) if isinstance(data, dict) else []:
        for term in json.loads(item)["terms"]["OnDemand"].values():
            for dim in term["priceDimensions"].values():
                usd = float(dim["pricePerUnit"]["USD"])
                if usd > 0:
                    return usd
    return 0.0


def spot_prices(itype: str) -> dict[str, float]:
    data = aws("ec2", "describe-spot-price-history", "--instance-types", itype,
               "--product-descriptions", "Linux/UNIX", "--start-time",
               dt.datetime.now(dt.timezone.utc).isoformat(), check=False)
    return {p["AvailabilityZone"]: float(p["SpotPrice"]) for p in (data.get("SpotPriceHistory") or [])} \
        if isinstance(data, dict) else {}


def vcpus_of(itype: str) -> tuple[int, str]:
    data = aws("ec2", "describe-instance-types", "--instance-types", itype)
    t = data["InstanceTypes"][0]
    return t["VCpuInfo"]["DefaultVCpus"], t["ProcessorInfo"]["SupportedArchitectures"][0]


# ---------------------------------------------------------------- ssh / rsync

def ssh_base(h: dict) -> list[str]:
    STATE.mkdir(exist_ok=True)
    return ["ssh", "-p", h["port"], "-i", str(KEY), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={STATE / 'known_hosts'}",
            "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4",
            "-o", "ControlMaster=auto", "-o", f"ControlPath={Path.home() / '.ssh'}/avalon-cm-%C",
            "-o", "ControlPersist=600", "-o", "LogLevel=ERROR"]


def ssh(h: dict, command: str, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run `command` (bash) on host h. Every call marks the host as in use for the idle watchdog."""
    remote = "touch /var/tmp/avalon-last-use 2>/dev/null; " + command
    return subprocess.run([*ssh_base(h), f"{h['user']}@{h['ip']}", "bash -lc " + shlex.quote(remote)],
                          capture_output=True, text=True, timeout=timeout)


def on_all(hosts: list[dict], fn, *args):
    with cf.ThreadPoolExecutor(max(1, len(hosts))) as ex:
        return list(ex.map(lambda h: fn(h, *args), hosts))


def rsync_to(h: dict, src: Path, dest: str) -> subprocess.CompletedProcess:
    sh_cmd = " ".join(shlex.quote(x) for x in ssh_base(h))
    excl = [a for pat in NEVER for a in ("--exclude", pat)]
    srcs = f"{src}/" if src.is_dir() else str(src)
    target = f"{h['user']}@{h['ip']}:w/{dest}" + ("/" if src.is_dir() else "")
    subprocess.run([*ssh_base(h), f"{h['user']}@{h['ip']}", f"mkdir -p w/{shlex.quote(str(Path(dest).parent))}"],
                   capture_output=True)
    return subprocess.run(["rsync", "-az", "--delete", *excl, "-e", sh_cmd, srcs, target],
                          capture_output=True, text=True)


def rsync_from(h: dict, remote: str, local: Path) -> subprocess.CompletedProcess:
    local.mkdir(parents=True, exist_ok=True)
    sh_cmd = " ".join(shlex.quote(x) for x in ssh_base(h))
    return subprocess.run(["rsync", "-az", "-e", sh_cmd, f"{h['user']}@{h['ip']}:{remote}/", f"{local}/"],
                          capture_output=True, text=True)


def ready_hosts(require: bool = True) -> list[dict]:
    hosts = [h for h in instances(("running",)) if h["ip"]]
    if require and not hosts:
        die("No running fleet instances. Start some with: python3 cloud/aws/fleet.py up --count 1")
    if not TEST_HOSTS:
        allow_my_ip()
    return hosts


# ---------------------------------------------------------------- network + account setup

def default_vpc() -> tuple[str, list[dict]]:
    vpcs = aws("ec2", "describe-vpcs", "--filters", "Name=is-default,Values=true")["Vpcs"]
    if not vpcs:
        die(f"No default VPC in {REGION}. Create one: aws ec2 create-default-vpc --region {REGION}")
    vpc = vpcs[0]["VpcId"]
    subnets = aws("ec2", "describe-subnets", "--filters", f"Name=vpc-id,Values={vpc}",
                  "Name=default-for-az,Values=true")["Subnets"]
    return vpc, sorted(subnets, key=lambda s: s["AvailabilityZone"])


def security_group(create: bool = False) -> str:
    vpc, _ = default_vpc()
    found = aws("ec2", "describe-security-groups", "--filters", f"Name=group-name,Values={SG_NAME}",
                f"Name=vpc-id,Values={vpc}")["SecurityGroups"]
    if found:
        return found[0]["GroupId"]
    if not create:
        die("No security group yet: run `python3 cloud/aws/fleet.py setup` first.")
    sg = aws("ec2", "create-security-group", "--group-name", SG_NAME, "--vpc-id", vpc, "--description",
             "avalon-nl fleet: SSH from the team laptop only", "--tag-specifications",
             f"ResourceType=security-group,Tags=[{{Key=Project,Value={PROJECT}}}]", mutate=True)
    return sg.get("GroupId", "sg-DRYRUN")


def allow_my_ip() -> None:
    """SSH ingress (ports 22 and 443) = exactly this laptop's current IP, or AVALON_SSH_CIDR if set.
    Venue Wi-Fi changes the IP; every command that connects re-checks and swaps the rule."""
    sg = security_group()
    want = os.environ.get("AVALON_SSH_CIDR") or my_ip() + "/32"
    perms = aws("ec2", "describe-security-groups", "--group-ids", sg)["SecurityGroups"][0]["IpPermissions"]
    for port in (22, 443):
        current = [r["CidrIp"] for p in perms if p.get("FromPort") == port for r in p.get("IpRanges", [])]
        if current == [want]:
            continue
        for cidr in current:
            if cidr != want:
                aws("ec2", "revoke-security-group-ingress", "--group-id", sg, "--protocol", "tcp", "--port",
                    str(port), "--cidr", cidr, mutate=True)
        if want not in current:
            aws("ec2", "authorize-security-group-ingress", "--group-id", sg, "--protocol", "tcp", "--port",
                str(port), "--cidr", want, mutate=True)
            say(f"SSH port {port} now open to {want} only.")


def cmd_setup(a) -> None:
    ident = aws("sts", "get-caller-identity")
    account = ident["Account"]
    if not KEY.exists():
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "avalon-nl-aws", "-f", str(KEY)], check=True,
                       capture_output=True)
        say(f"Made SSH key {KEY} (stays on this laptop).")
    keys = aws("ec2", "describe-key-pairs", "--filters", f"Name=key-name,Values={KEY_NAME}")["KeyPairs"]
    if not keys:
        aws("ec2", "import-key-pair", "--key-name", KEY_NAME, "--public-key-material",
            f"fileb://{KEY}.pub", "--tag-specifications",
            f"ResourceType=key-pair,Tags=[{{Key=Project,Value={PROJECT}}}]", mutate=True)
        say(f"Imported public key as EC2 key pair {KEY_NAME}.")
    say(f"Security group {security_group(create=True)}.")
    if not DRY:
        allow_my_ip()
    if a.email:
        budgets = aws("budgets", "describe-budgets", "--account-id", account, check=False)
        if not any(b["BudgetName"] == BUDGET_NAME for b in (budgets.get("Budgets") or [])):
            budget = {"BudgetName": BUDGET_NAME, "BudgetLimit": {"Amount": str(a.budget_usd), "Unit": "USD"},
                      "TimeUnit": "MONTHLY", "BudgetType": "COST",
                      # Gross cost: with credits included the net is ~$0 and the alert would never fire.
                      "CostTypes": {"IncludeCredit": False, "IncludeRefund": False, "IncludeTax": True}}
            subs = [{"SubscriptionType": "EMAIL", "Address": a.email}]
            notes = [{"Notification": {"NotificationType": kind, "ComparisonOperator": "GREATER_THAN",
                                       "Threshold": pct, "ThresholdType": "PERCENTAGE"}, "Subscribers": subs}
                     for kind, pct in (("ACTUAL", 50), ("ACTUAL", 100), ("FORECASTED", 100))]
            aws("budgets", "create-budget", "--account-id", account, "--budget", json.dumps(budget),
                "--notifications-with-subscribers", json.dumps(notes), mutate=True)
            say(f"Budget alert {BUDGET_NAME}: ${a.budget_usd}/month gross usage, mails at 50%, 100%, forecast 100%.")
    if a.vcpus:  # write the envelope Dylan agreed
        STATE.mkdir(exist_ok=True)
        env = {"region": REGION, "max_vcpus": a.vcpus, "max_instances": a.instances, "max_usd_h": a.usd_h,
               "deadline": a.deadline, "agreed": a.agreed}
        (STATE / "envelope.json").write_text(json.dumps(env, indent=1))
        say(f"Envelope saved: {env}")


def cmd_quotas(a) -> None:
    for code, what in QUOTAS.items():
        q = aws("service-quotas", "get-service-quota", "--service-code", "ec2", "--quota-code", code, check=False)
        value = q.get("Quota", {}).get("Value") if isinstance(q, dict) else None
        if value is None:
            d = aws("service-quotas", "get-aws-default-service-quota", "--service-code", "ec2", "--quota-code",
                    code, check=False)
            value = d.get("Quota", {}).get("Value") if isinstance(d, dict) else "?"
        want = a.want_gpu if "G and VT" in what else a.want
        line = f"  {code} {what:40s} now {value} vCPUs"
        if a.request and isinstance(value, (int, float)) and value < want:
            r = aws("service-quotas", "request-service-quota-increase", "--service-code", "ec2", "--quota-code",
                    code, "--desired-value", str(want), mutate=True, check=False)
            line += f" -> requested {want}: {r.get('RequestedQuota', {}).get('Status', r.get('_error', 'dry-run'))}"
        say(line)
    hist = aws("service-quotas", "list-requested-service-quota-change-history", "--service-code", "ec2",
               check=False)
    for r in (hist.get("RequestedQuotas") or [])[:8] if isinstance(hist, dict) else []:
        say(f"  request {r['QuotaCode']} -> {r['DesiredValue']}: {r['Status']} ({r.get('Created', '')})")


# ---------------------------------------------------------------- up / status / down

def cmd_up(a) -> None:
    env = envelope()
    if env["region"] != REGION:
        die(f"Envelope is for {env['region']}, this command is on {REGION}.")
    vcpus, arch = vcpus_of(a.type)
    arch = {"x86_64": "amd64", "arm64": "arm64"}[arch]
    running = instances()
    total_v = sum(h["vcpus"] for h in running) + vcpus * a.count
    if total_v > env["max_vcpus"] or len(running) + a.count > env["max_instances"]:
        die(f"Over the envelope: would be {len(running) + a.count} instances / {total_v} vCPUs "
            f"(max {env['max_instances']} / {env['max_vcpus']}).")
    deadline = dt.datetime.fromisoformat(a.until or env["deadline"])
    if deadline.tzinfo is None:
        die("--until needs a timezone, e.g. 2026-11-15T23:00-08:00")
    deadline = min(deadline, dt.datetime.fromisoformat(env["deadline"]))
    if deadline <= dt.datetime.now(dt.timezone.utc):
        die(f"Deadline {deadline} is in the past.")
    price = on_demand_price(a.type)
    if a.spot:
        sp = spot_prices(a.type)
        price = max(sp.values()) if sp else price
    run_cost = sum(h["price"] for h in running) + price * a.count
    if price and run_cost > env["max_usd_h"]:
        die(f"Over the envelope: ${run_cost:.2f}/h with this launch (max ${env['max_usd_h']}/h).")
    ami = aws("ssm", "get-parameter", "--name", UBUNTU_AMI_PARAM.format(arch=arch))["Parameter"]["Value"]
    sg = security_group()
    _, subnets = default_vpc()
    if a.az:
        subnets = [s for s in subnets if s["AvailabilityZone"] == a.az] or die(f"no default subnet in {a.az}")
    user_data = (HERE / "userdata.sh").read_text() \
        .replace("__DEADLINE__", str(int(deadline.timestamp()))).replace("__IDLE_MIN__", str(a.idle_min))
    STATE.mkdir(exist_ok=True)
    ud_file = STATE / "userdata.rendered.sh"
    ud_file.write_text(user_data)
    tags = [("Project", PROJECT), ("Fleet", a.fleet), ("Deadline", deadline.isoformat()),
            ("PriceUSDh", f"{price:.4f}"), ("Name", f"{PROJECT}-{a.fleet}")]
    tagspec = ",".join(f"{{Key={k},Value={v}}}" for k, v in tags)
    say(f"Launching {a.count} x {a.type} ({vcpus} vCPUs, {'spot' if a.spot else 'on-demand'}, ~${price:.2f}/h each) "
        f"in {REGION}, fleet {a.fleet}, auto-off {deadline.isoformat()} or {a.idle_min} min idle.")
    launched: list[str] = []
    errors = []
    for subnet in subnets:  # try zones in turn until the count is met (capacity varies by zone)
        need = a.count - len(launched)
        if need <= 0:
            break
        args = ["ec2", "run-instances", "--image-id", ami, "--instance-type", a.type, "--count", f"1:{need}",
                "--key-name", KEY_NAME, "--security-group-ids", sg, "--subnet-id", subnet["SubnetId"],
                "--associate-public-ip-address",
                "--instance-initiated-shutdown-behavior", "terminate",
                "--metadata-options", "HttpTokens=required,HttpEndpoint=enabled",
                "--block-device-mappings", json.dumps([{"DeviceName": "/dev/sda1", "Ebs": {
                    "VolumeSize": a.disk_gb, "VolumeType": "gp3", "DeleteOnTermination": True, "Encrypted": True}}]),
                "--user-data", f"file://{ud_file}",
                "--tag-specifications", f"ResourceType=instance,Tags=[{tagspec}]",
                f"ResourceType=volume,Tags=[{tagspec}]"]
        if a.spot:
            args += ["--instance-market-options",
                     "MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate}"]
        r = aws(*args, mutate=True, check=False)
        if "_error" in r:
            errors.append(f"{subnet['AvailabilityZone']}: {r['_error'][-300:]}")
            continue
        launched += [i["InstanceId"] for i in r.get("Instances", [])]
    if DRY:
        return
    if not launched:
        die("No instance started:\n  " + "\n  ".join(errors))
    if errors:
        say("Some zones refused:\n  " + "\n  ".join(errors))
    say(f"Started {launched}; waiting for SSH and first-boot setup (about 2 minutes)...")
    wait_ready(launched, a.wait_s)


def wait_ready(ids: list[str], wait_s: int) -> None:
    t0 = time.time()
    pending = set(ids)
    allow_my_ip()
    while pending and time.time() - t0 < wait_s:
        hosts = [h for h in instances(("pending", "running")) if h["id"] in pending and h["ip"]]
        for h in hosts:
            try:
                p = ssh(h, "test -f /var/lib/avalon-ready && nproc && python3 --version && uv --version", timeout=20)
            except subprocess.TimeoutExpired:
                continue
            if p.returncode == 0:
                say(f"  {h['id']} {h['ip']} ready after {time.time() - t0:.0f}s: " + " | ".join(p.stdout.split("\n")[:3]))
                pending.discard(h["id"])
        if pending:
            time.sleep(5)
    if pending:
        die(f"Not ready after {wait_s}s: {sorted(pending)} (status shows them; `down` removes them).")


def cmd_status(a) -> None:
    hosts = instances(("pending", "running", "stopping", "shutting-down"))
    if not hosts:
        say(f"No fleet instances in {REGION}. Nothing is billing from this tool.")
        return
    now = dt.datetime.now(dt.timezone.utc)
    total_h = total_spent = 0.0
    live = [h for h in hosts if h["state"] == "running" and h["ip"]]
    loads = dict(zip([h["id"] for h in live], on_all(live, lambda h: ssh(h, "cut -d' ' -f1-3 /proc/loadavg; "
                     "ls ~/runs 2>/dev/null | tail -3 | tr '\\n' ' '", timeout=15)))) if live and not a.no_ssh else {}
    for h in hosts:
        hours = (now - dt.datetime.fromisoformat(h["launched"])).total_seconds() / 3600 if h["launched"] else 0
        total_h += h["price"]
        total_spent += h["price"] * hours
        p = loads.get(h["id"])
        extra = (" load " + p.stdout.replace("\n", " | runs ").strip()) if p is not None and p.returncode == 0 else ""
        say(f"  {h['id']} {h['fleet']:8s} {h['type']:15s} {h['vcpus']:4d} vCPU {'spot' if h['spot'] else 'od  '} "
            f"{h['state']:10s} {h['ip']:15s} up {hours:4.1f}h ${h['price']:.2f}/h  off by {h['deadline'][:16]}{extra}")
    say(f"{len(hosts)} instances, ${total_h:.2f}/h now, ~${total_spent:.2f} so far (list price; credits pay).")


def cmd_down(a) -> None:
    hosts = instances(("pending", "running", "stopping", "stopped"))
    if a.fleet:
        hosts = [h for h in hosts if h["fleet"] == a.fleet]
    if not hosts:
        say("Nothing to terminate.")
        return
    ids = [h["id"] for h in hosts]
    aws("ec2", "terminate-instances", "--instance-ids", *ids, mutate=True)
    say(f"Terminating {ids}. Their disks go with them. Check: python3 cloud/aws/fleet.py status")


# ---------------------------------------------------------------- push / build / sh

def parse_paths(specs: list[str]) -> list[tuple[Path, str]]:
    out = []
    for spec in specs:
        src, _, dest = spec.partition(":")
        p = Path(src).expanduser().resolve()
        if not p.exists():
            die(f"{src} does not exist")
        if not dest:
            try:
                dest = str(p.relative_to(Path.cwd().resolve()))
            except ValueError:
                dest = p.name
        if dest.startswith("/") or ".." in Path(dest).parts:
            die(f"destination {dest} must be relative (it lands under ~/w/ on each instance)")
        out.append((p, dest))
    return out


def cmd_push(a) -> None:
    hosts = ready_hosts()
    pairs = parse_paths(a.paths)
    t0 = time.time()

    def push_one(h):
        errs = [f"{d}: {p.stderr.strip()[-300:]}" for s, d in pairs if (p := rsync_to(h, s, d)).returncode != 0]
        return h, errs

    bad = [(h["id"], e) for h, e in on_all(hosts, push_one) if e]
    if bad:
        die(f"push failed: {bad}")
    say(f"Pushed {[d for _, d in pairs]} to {len(hosts)} instance(s) in {time.time() - t0:.1f}s (into ~/w/).")


BUILD_DEFAULT = (
    "set -e; cd ~/w/{dir}; uv venv -q --allow-existing -p 3.12 .venv; "
    "test ! -f requirements.txt || uv pip install -q -p .venv --index-strategy unsafe-best-match -r requirements.txt; "
    # the kit's SDK packages depend on each other: install them editable in one resolve
    "e=(); for d in sdk/*/; do if [ -f \"$d/pyproject.toml\" ] || [ -f \"$d/setup.py\" ]; then e+=(-e \"$d\"); fi; done; "
    "[ ${#e[@]} -eq 0 ] || uv pip install -q -p .venv \"${e[@]}\"; .venv/bin/python --version")


def cmd_build(a) -> None:
    hosts = ready_hosts()
    command = a.cmd or BUILD_DEFAULT.replace("{dir}", shlex.quote(a.dir))
    t0 = time.time()
    res = on_all(hosts, ssh, command, 1800)
    for h, p in zip(hosts, res):
        if p.returncode != 0:
            die(f"build failed on {h['id']}:\n{p.stdout[-1500:]}\n{p.stderr[-3000:]}")
    say(f"Built ~/w/{a.dir}/.venv on {len(hosts)} instance(s) in {time.time() - t0:.1f}s: {res[0].stdout.strip()}")


def cmd_sh(a) -> None:
    hosts = ready_hosts()
    rc = 0
    for h, p in zip(hosts, on_all(hosts, ssh, f"cd ~/w && {a.command}", a.timeout)):
        say(f"--- {h['id']} ({h['ip']}) exit {p.returncode}\n{p.stdout.rstrip()}")
        if p.stderr.strip():
            say(p.stderr.rstrip()[-3000:])
        rc = rc or p.returncode
    sys.exit(rc)


# ---------------------------------------------------------------- run: shard a command over every core

def plan_shards(items: int, per_shard: int, hosts: list[dict], per_host: list[int]) -> list[list[dict]]:
    """Cut [0, items) into shards and deal them to hosts in proportion to their slots."""
    slots = sum(per_host)
    if per_shard <= 0:
        per_shard = max(1, math.ceil(items / slots))
    shards = [{"shard": i, "first": f, "count": min(per_shard, items - f)}
              for i, f in enumerate(range(0, items, per_shard))]
    for s in shards:
        s["shards"] = len(shards)
    per = [[] for _ in hosts]
    # weighted round-robin: next shard goes to the host with the lowest load per slot
    for s in shards:
        k = min(range(len(hosts)), key=lambda j: (len(per[j]) / per_host[j], j))
        per[k].append(s)
    return per


def fill(template: str, s: dict, out: str) -> str:
    for k in ("shard", "shards", "first", "count"):
        template = template.replace("{" + k + "}", str(s[k]))
    return template.replace("{out}", out)


def cmd_run(a) -> None:
    hosts = ready_hosts()
    name = a.name or f"run{int(time.time())}"
    per_host = [a.per_host or max(1, h["vcpus"] // a.cores_per_shard) for h in hosts]
    plan = plan_shards(a.items, a.per_shard, hosts, per_host)
    nshards = sum(len(p) for p in plan)
    rdir = f"runs/{name}"
    t0 = time.time()

    busy = on_all(hosts, ssh, "for f in ~/runs/*/pid; do [ -f \"$f\" ] && kill -0 $(cat \"$f\") 2>/dev/null "
                              "&& echo $(basename $(dirname \"$f\")); done; true", 20)
    others = sorted({r for p in busy for r in p.stdout.split()})
    if others:  # runs queue per instance (a lock): oversubscribed cores make bots time out
        say(f"Queued behind {others}: it starts when they finish." if not a.force
            else f"--force: sharing the cores with {others} (timings and timeouts are not trustworthy).")

    def start(h, shards, slots):
        lines = ["set -e", f"rm -rf ~/{rdir}; mkdir -p ~/{rdir}/s ~/{rdir}/out ~/{rdir}/log"]
        for s in shards:
            out = f"$HOME/{rdir}/out/shard-{s['shard']:05d}.{a.ext}"
            body = (f"cd ~/w/{a.cwd} && export SHARD={s['shard']} SHARDS={s['shards']} FIRST={s['first']} "
                    f"COUNT={s['count']} OUT={out}\n{fill(a.command, s, out)}\n")
            lines.append(f"cat > ~/{rdir}/s/{s['shard']:05d}.sh <<'AVALON_EOF'\n{body}AVALON_EOF")
        # one xargs pool per host; each shard's exit code and log are kept
        pool = (f"date +%s > started; ls s | xargs -P {slots} -I{{}} bash -c "
                f"'bash s/{{}} > log/{{}}.log 2>&1; echo $? > log/{{}}.rc'")
        # one run at a time per instance: later runs wait on the lock (unless --force)
        runner = (f"cd ~/{rdir} && " + (pool if a.force else f"flock ~/runs/.lock bash -c {shlex.quote(pool)}")
                  + "; touch done")
        lines.append(f"nohup bash -c {shlex.quote(runner)} > ~/{rdir}/xargs.log 2>&1 < /dev/null & "
                     f"echo $! > ~/{rdir}/pid")
        return ssh(h, "\n".join(lines), 120)

    res = [start(h, p, n) for h, p, n in zip(hosts, plan, per_host)]
    for h, p in zip(hosts, res):
        if p.returncode != 0:
            die(f"could not start on {h['id']}: {p.stderr[-1500:]}")
    say(f"{name}: {nshards} shards over {len(hosts)} instance(s), slots {per_host}, started in {time.time() - t0:.1f}s")
    if a.detach:
        say(f"Detached. Collect later (same --merge): python3 cloud/aws/fleet.py collect {name}"
            + (f" --merge {a.merge}" if a.merge else ""))
        return
    collect(name, hosts, a, t0, nshards)


def collect(name: str, hosts: list[dict], a, t0: float, nshards: int | None = None) -> None:
    rdir = f"runs/{name}"
    last = ""
    while True:
        st = on_all(hosts, ssh, f"cd ~/{rdir} 2>/dev/null || exit 3; echo $(ls s | wc -l) $(ls log/*.rc 2>/dev/null "
                                f"| wc -l) $(cat log/*.rc 2>/dev/null | grep -vc '^0$') $(test -f done && echo 1 || echo 0)",
                    30)
        nums = []
        for h, p in zip(hosts, st):
            if p.returncode != 0:
                die(f"{h['id']}: no run {name} there ({p.stderr.strip()[-200:]})")
            nums.append([int(x) for x in p.stdout.split()])
        total, done, failed = (sum(n[i] for n in nums) for i in range(3))
        msg = f"  {name}: {done}/{total} shards done, {failed} failed, {time.time() - t0:.0f}s"
        if msg.split(",")[0] != last:
            say(msg)
            last = msg.split(",")[0]
        if all(n[3] for n in nums):
            break
        time.sleep(a.poll_s)
    # wall = from when its shards started playing (after any queue wait) to when the last instance finished
    stamps = [ssh(h, f"cd ~/{rdir} && echo $(cat started) $(stat -c %Y done)", 20).stdout.split() for h in hosts]
    t_start = min([float(x[0]) for x in stamps if len(x) == 2] or [t0])
    t_end = max([float(x[1]) for x in stamps if len(x) == 2] or [time.time()])
    wall = time.time() - t_start if time.time() - t_end < 5 else t_end - t_start  # 1-s stamps when collected late
    dest = RESULTS / name
    shutil.rmtree(dest, ignore_errors=True)  # never merge a previous run's files of the same name
    for h in hosts:
        for sub in ("out", "log"):
            p = rsync_from(h, f"{rdir}/{sub}", dest / sub)
            if p.returncode != 0:
                die(f"collect from {h['id']} failed: {p.stderr[-500:]}")
    rcs = {f.stem: f.read_text().strip() for f in (dest / "log").glob("*.rc")}
    bad = sorted(k for k, v in rcs.items() if v != "0")
    for k in bad[:5]:
        tail = (dest / "log" / f"{k}.log").read_text()[-1500:]
        say(f"--- shard {k} failed (exit {rcs[k]}):\n{tail}")
    say(f"{name}: wall {wall:.1f}s; {len(rcs) - len(bad)}/{len(rcs)} shards ok; files in {dest}/out")
    if a.merge:
        merged = merge(sorted((dest / "out").glob("shard-*")), a.merge)
        merged["wall_s"] = round(wall, 1)
        merged["fleet"] = [{"id": h["id"], "type": h["type"], "vcpus": h["vcpus"], "price": h["price"]} for h in hosts]
        # a run with failed shards never writes NAME.json: a partial result must not pass for a whole one
        target = RESULTS / (f"{name}.partial.json" if bad else f"{name}.json")
        if bad:
            (RESULTS / f"{name}.json").unlink(missing_ok=True)
        target.write_text(json.dumps(merged))
        say(f"merged {len(merged.get(a.merge, []))} {a.merge} -> {target}")
    if bad:
        die(f"{len(bad)} shard(s) failed: {bad[:10]}{'...' if len(bad) > 10 else ''} (logs in {dest}/log)")


def merge(files: list[Path], key: str) -> dict:
    """Same shape as cloud/nl_modal.py merge(): the `key` lists concatenated (sorted by their own
    `table`/`shard`/`index` field if they have one), elapsed_s summed, *_stderr dicts unioned, the rest
    from the first shard; plus shard_elapsed_s."""
    shards = [json.loads(f.read_text()) for f in files]
    if not shards:
        die("nothing to merge")
    out = dict(shards[0])
    rows = [r for s in shards for r in s.get(key, [])]
    sort_key = next((k for k in ("table", "shard", "index") if rows and isinstance(rows[0], dict) and k in rows[0]), None)
    out[key] = sorted(rows, key=lambda r: r[sort_key]) if sort_key else rows
    if all("elapsed_s" in s for s in shards):
        out["elapsed_s"] = round(sum(s["elapsed_s"] for s in shards), 2)
        out["shard_elapsed_s"] = sorted(s["elapsed_s"] for s in shards)
    for k, v in shards[0].items():
        if k.endswith("_stderr") and isinstance(v, dict):
            out[k] = {kk: vv for s in shards for kk, vv in s.get(k, {}).items()}
    return out


def cmd_collect(a) -> None:
    hosts = ready_hosts()
    collect(a.name, hosts, a, time.time())


def cmd_check(a) -> None:
    ident = aws("sts", "get-caller-identity", check=False)
    if "_error" in ident:
        die("Not signed in. Dylan runs: aws login --region us-west-2   (then this again)")
    say(f"Signed in: account {ident['Account']} as {ident['Arn'].split(':')[-1]}; region {REGION}")
    cmd_quotas(argparse.Namespace(request=False, want=0, want_gpu=0))
    vcpus, arch = vcpus_of(a.type)
    sp = spot_prices(a.type)
    od = on_demand_price(a.type)
    say(f"{a.type}: {vcpus} vCPUs ({arch}); on-demand ${od:.3f}/h; spot now "
        + (", ".join(f"{z} ${p:.3f}" for z, p in sorted(sp.items())) or "n/a"))
    offered = aws("ec2", "describe-instance-type-offerings", "--location-type", "availability-zone", "--filters",
                  f"Name=instance-type,Values={a.type}")["InstanceTypeOfferings"]
    say(f"Offered in zones: {sorted(o['Location'] for o in offered)}")
    env = STATE / "envelope.json"
    say(f"Envelope: {env.read_text().strip() if env.exists() else 'not agreed yet'}")
    say(f"Key {KEY}: {'present' if KEY.exists() else 'missing (setup makes it)'}")
    cmd_status(argparse.Namespace(no_ssh=True))


# ---------------------------------------------------------------- CLI

def main() -> None:
    global DRY, REGION
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="print AWS calls that would change anything")
    p.add_argument("--region", default=REGION)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("check", help="read-only: sign-in, quotas, price, zones, envelope, what is running")
    s.add_argument("--type", default="c7a.48xlarge")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("setup", help="key pair, security group, budget alert, and the agreed envelope")
    s.add_argument("--email", help="budget alert recipient (skip to make no budget)")
    s.add_argument("--budget-usd", type=int, default=300)
    s.add_argument("--vcpus", type=int, help="envelope: max vCPUs running at once")
    s.add_argument("--instances", type=int, default=4, help="envelope: max instances")
    s.add_argument("--usd-h", type=float, default=40.0, help="envelope: max $/h (list price)")
    s.add_argument("--deadline", default="2026-11-15T23:00-08:00", help="envelope: everything off by")
    s.add_argument("--agreed", default="", help="who agreed and when, in their words")
    s.set_defaults(fn=cmd_setup)

    s = sub.add_parser("quotas", help="show EC2 vCPU quotas; --request files increases")
    s.add_argument("--request", action="store_true")
    s.add_argument("--want", type=int, default=768)
    s.add_argument("--want-gpu", type=int, default=64)
    s.set_defaults(fn=cmd_quotas)

    s = sub.add_parser("up", help="start instances (Ubuntu 24.04, Python 3.12, uv)")
    s.add_argument("--count", type=int, default=1)
    s.add_argument("--type", default="c7a.48xlarge")
    s.add_argument("--spot", action="store_true", help="spot: cheaper, can be taken back at 2 minutes' notice")
    s.add_argument("--fleet", default="main", help="a label; `down --fleet X` stops only those")
    s.add_argument("--until", help="ISO time with zone; default and maximum: the envelope's deadline")
    s.add_argument("--idle-min", type=int, default=120, help="power off after this long with no fleet command")
    s.add_argument("--az", help="a zone, e.g. us-west-2b (default: try each)")
    s.add_argument("--disk-gb", type=int, default=40)
    s.add_argument("--wait-s", type=int, default=420)
    s.set_defaults(fn=cmd_up)

    s = sub.add_parser("status", help="instances, cost so far, load, recent runs")
    s.add_argument("--no-ssh", action="store_true")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("down", help="terminate this tool's instances (all, or one --fleet)")
    s.add_argument("--fleet")
    s.set_defaults(fn=cmd_down)

    s = sub.add_parser("push", help="rsync folders to ~/w/DEST on every instance (hand histories never go)")
    s.add_argument("paths", nargs="+", help="SRC[:DEST]; DEST defaults to SRC relative to the current folder")
    s.set_defaults(fn=cmd_push)

    s = sub.add_parser("build", help="make ~/w/DIR/.venv: requirements.txt, then sdk/* editable")
    s.add_argument("dir")
    s.add_argument("--cmd", help="a different build command (runs on every instance)")
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser("sh", help="run a command in ~/w on every instance")
    s.add_argument("command")
    s.add_argument("--timeout", type=float, default=600)
    s.set_defaults(fn=cmd_sh)

    for name in ("run", "collect"):
        s = sub.add_parser(name, help="shard a command over every core of every instance, then gather"
                           if name == "run" else "wait for a detached run and gather its files")
        if name == "run":
            s.add_argument("command", help="placeholders {first} {count} {shard} {shards} {out}; also $FIRST etc.")
            s.add_argument("--name")
            s.add_argument("--items", type=int, required=True, help="work items to split (e.g. tables)")
            s.add_argument("--per-shard", type=int, default=0, help="items per shard (0: spread over all slots)")
            s.add_argument("--per-host", type=int, default=0, help="shards at once per instance (0: vCPUs/cores-per-shard)")
            s.add_argument("--cores-per-shard", type=int, default=2)
            s.add_argument("--cwd", default=".", help="folder under ~/w to run in")
            s.add_argument("--ext", default="json")
            s.add_argument("--detach", action="store_true")
            s.add_argument("--force", action="store_true")
        else:
            s.add_argument("name")
        s.add_argument("--merge", default="", help="JSON list key to concatenate into cloud/results/NAME.json "
                                                   "(e.g. tables, as cloud/nl_modal.py writes)")
        s.add_argument("--poll-s", type=float, default=2.0)
        s.set_defaults(fn=cmd_run if name == "run" else cmd_collect)

    a = p.parse_args()
    DRY, REGION = a.dry_run, a.region
    a.fn(a)


if __name__ == "__main__":
    main()
