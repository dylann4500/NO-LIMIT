#!/bin/zsh
# Start this laptop's agent hub, and restart it automatically if it ever crashes.
#   ./hub/start.sh samuel ~/nolimit-rehearsal [more options, e.g. --portal-base ... --portal-key-file ...]
# Then open http://127.0.0.1:7777. Stop with Ctrl+C.
PERSON=${1:?usage: hub/start.sh samuel|dylan <team repo> [options]}
REPO=${2:?usage: hub/start.sh samuel|dylan <team repo> [options]}
shift 2
cd "$(dirname "$0")"
while true; do
  caffeinate -dimsu uv run --no-project --with aiohttp --with claude-agent-sdk --with modal \
    python hub.py --person "$PERSON" --repo "$REPO" "$@" 2> >(grep -v -e CanUseToolShadowed -e _warn_if_can_use >&2)
  code=$?
  [ $code -eq 130 -o $code -eq 0 ] && break      # Ctrl+C or a clean exit: stop
  echo "hub exited ($code); restarting in 3 s (Ctrl+C to stop)"; sleep 3
done
