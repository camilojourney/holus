#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  ./init-project.sh [--mode 2]

Mode 2 bootstraps scaffold files in the current project.
USAGE
}

MODE="2"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode|-m)
      MODE="${2:-2}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$MODE" != "2" ]]; then
  echo "Only mode 2 is supported in project bootstrap script." >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/specs"

if [[ -f "$ROOT_DIR/.ai/contexts/product-context.md.example" && ! -f "$ROOT_DIR/.ai/contexts/product-context.md" ]]; then
  cp "$ROOT_DIR/.ai/contexts/product-context.md.example" "$ROOT_DIR/.ai/contexts/product-context.md"
fi

if [[ -f "$ROOT_DIR/.ai/contexts/current-priorities.md.example" && ! -f "$ROOT_DIR/.ai/contexts/current-priorities.md" ]]; then
  cp "$ROOT_DIR/.ai/contexts/current-priorities.md.example" "$ROOT_DIR/.ai/contexts/current-priorities.md"
fi

echo "Bootstrap complete in: $ROOT_DIR"
echo "Created/verified: specs/, .ai/contexts/product-context.md, .ai/contexts/current-priorities.md"
