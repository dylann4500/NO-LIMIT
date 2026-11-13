#!/bin/zsh
# Start this laptop's agent hub.   ./hub/start.sh samuel ~/nolimit-rehearsal
# Then open http://127.0.0.1:7777
set -e
PERSON=${1:?usage: hub/start.sh samuel|dylan <team repo>}
REPO=${2:?usage: hub/start.sh samuel|dylan <team repo>}
cd "$(dirname "$0")"
exec caffeinate -i uv run --no-project --with aiohttp --with claude-agent-sdk --with modal \
  python hub.py --person "$PERSON" --repo "$REPO" "${@:3}"
