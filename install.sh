#!/usr/bin/env bash
# Install orgo-hermes-connect and its Hermes skill.
#   curl -fsSL https://raw.githubusercontent.com/OrgoAI/orgo-hermes-connect/main/install.sh | bash
# Then:  orgo-hermes-connect up
set -euo pipefail

REPO="${OHC_REPO:-OrgoAI/orgo-hermes-connect}"
REF="${OHC_REF:-main}"
RAW="https://raw.githubusercontent.com/${REPO}/${REF}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

if [ "$(id -u)" = 0 ]; then BIN_DIR="${OHC_BIN_DIR:-/usr/local/bin}"; else BIN_DIR="${OHC_BIN_DIR:-$HOME/.local/bin}"; fi
SKILL_DIR="$HERMES_HOME/skills/autonomous-ai-agents/orgo-hermes-connect"

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }

# Use a local checkout when run from one; otherwise download.
SRC_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "$(dirname "${BASH_SOURCE[0]}")/orgo-hermes-connect" ]; then
  SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

fetch() { # fetch <relpath> <dest>
  if [ -n "$SRC_DIR" ]; then cp "$SRC_DIR/$1" "$2"; else curl -fsSL "$RAW/$1" -o "$2"; fi
}

mkdir -p "$BIN_DIR" "$SKILL_DIR"
fetch orgo-hermes-connect "$BIN_DIR/orgo-hermes-connect"
chmod 755 "$BIN_DIR/orgo-hermes-connect"
fetch skill/SKILL.md "$SKILL_DIR/SKILL.md"

echo "✓ Installed $BIN_DIR/orgo-hermes-connect ($("$BIN_DIR/orgo-hermes-connect" --version))"
echo "✓ Installed Hermes skill: $SKILL_DIR/SKILL.md"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "  (add $BIN_DIR to PATH)";; esac

if [ "${OHC_AUTO_UP:-0}" = 1 ]; then
  exec "$BIN_DIR/orgo-hermes-connect" up
fi
echo
echo "Next:  orgo-hermes-connect up"
