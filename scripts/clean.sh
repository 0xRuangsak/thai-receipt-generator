#!/usr/bin/env bash
# Clean generated files (JSON configs and PNG outputs)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

rm -rf "$PROJECT_DIR/generated_json"
rm -rf "$PROJECT_DIR/output"

echo "Cleaned generated_json/ and output/"
