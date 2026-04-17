#!/usr/bin/env bash
# Launch Flappy Code. Uses the system Python 3 so there's nothing to install.
set -e
cd "$(dirname "$0")"
exec python3 flappy.py "$@"
