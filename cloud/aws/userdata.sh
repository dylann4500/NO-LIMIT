#!/bin/bash
# First-boot script for an avalon fleet instance (Ubuntu 24.04: its system Python is 3.12).
# fleet.py fills in __DEADLINE__ (epoch seconds) and __IDLE_MIN__ before launch.
# The instance is launched with "shutdown behaviour = terminate", so every power-off below
# deletes the instance and its disk: nothing keeps billing.
set -eux

DEADLINE=__DEADLINE__
IDLE_MIN=__IDLE_MIN__

# 1. Hard deadline, two ways: a scheduled shutdown now, and a watchdog every minute (survives a reboot).
now=$(date +%s)
mins=$(( (DEADLINE - now) / 60 )); [ "$mins" -lt 1 ] && mins=1
shutdown -h +"$mins" "avalon fleet deadline" || true

cat > /usr/local/bin/avalon-watchdog <<EOF
#!/bin/bash
# Power off (= terminate) at the deadline, or after ${IDLE_MIN} minutes with no fleet command and a quiet CPU.
now=\$(date +%s)
[ "\$now" -ge ${DEADLINE} ] && exec /sbin/poweroff
last=\$(stat -c %Y /var/tmp/avalon-last-use 2>/dev/null || echo \$now)
load15=\$(cut -d' ' -f3 /proc/loadavg)
if [ \$(( now - last )) -ge $(( IDLE_MIN * 60 )) ] && awk "BEGIN{exit !(\$load15 < 0.5)}"; then
  exec /sbin/poweroff
fi
EOF
chmod 755 /usr/local/bin/avalon-watchdog
touch /var/tmp/avalon-last-use && chmod 666 /var/tmp/avalon-last-use
echo '* * * * * root /usr/local/bin/avalon-watchdog' > /etc/cron.d/avalon-watchdog

# 2. Tools: rsync for pushes, a compiler for any wheel that builds from source, uv for fast installs.
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q rsync build-essential python3.12-venv python3.12-dev
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh

# 3. Room for many bot processes per shard.
cat > /etc/security/limits.d/avalon.conf <<EOF
ubuntu soft nofile 65536
ubuntu hard nofile 65536
ubuntu soft nproc 65536
ubuntu hard nproc 65536
EOF

# 4. SSH on 443 as well as 22: venue Wi-Fi often blocks outbound 22 (fleet.py: AVALON_SSH_PORT=443).
#    Ubuntu 24.04 starts sshd from ssh.socket; daemon-reload turns these Port lines into its listeners.
printf 'Port 22\nPort 443\n' > /etc/ssh/sshd_config.d/avalon-ports.conf
systemctl daemon-reload
systemctl restart ssh.socket || systemctl restart ssh

mkdir -p /home/ubuntu/w /home/ubuntu/runs && chown -R ubuntu:ubuntu /home/ubuntu/w /home/ubuntu/runs
touch /var/lib/avalon-ready
