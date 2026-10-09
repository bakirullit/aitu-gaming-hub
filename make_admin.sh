#!/usr/bin/env bash
set -e

# Script to easily grant admin permissions to @ALG0RITHMs (or specified user)
# Usage:
#   ./make_admin.sh
#   ./make_admin.sh @username
#   ./make_admin.sh @username role1 role2

TARGET_USER="${1:-ALG0RITHMs}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/update_admin.py" "$@"
elif command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "^aitu-gaming-hub$"; then
    docker exec aitu-gaming-hub python update_admin.py "$@"
elif command -v python3 &> /dev/null; then
    python3 "$SCRIPT_DIR/update_admin.py" "$@"
else
    echo "❌ Error: Neither Python (.venv / python3) nor Docker container 'aitu-gaming-hub' found."
    exit 1
fi
