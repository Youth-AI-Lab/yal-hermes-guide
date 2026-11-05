#!/usr/bin/env bash
# Installs Hermes Agent, at a pinned version, with the configuration of this guide.
# Runs once, when the Codespace is created (postCreateCommand in devcontainer.json).
set -euo pipefail

# The version this guide is tested with (tag v0.22.7, this commit; v0.22.5 until 2026-11-05). A newer one comes out several
# times a week: change the commit and this tag, and test the guide again (ci/README.md).
HERMES_COMMIT=b200f5bc60e31588ba2cb60e288029c4a54ba5fa

guide="$(cd "$(dirname "$0")/.." && pwd)"

# The configuration first: the installer keeps a config.yaml that is already there.
mkdir -p "$HOME/.hermes"
sed "s#@WORKSPACE@#$guide#g" "$guide/hermes/config.yaml" > "$HOME/.hermes/config.yaml"

# The installer of this same commit (a tag can move), then the commit. No browser and no "computer use"
# driver: this guide does not use them. --non-interactive: no setup wizard, no messaging gateway.
tmp="$(mktemp -d)"
# --retry: GitHub sometimes answers 429 (too many requests) to a shared address (CI, 2026-11-02).
curl -fsSL --retry 5 --retry-delay 15 "https://raw.githubusercontent.com/NousResearch/hermes-agent/$HERMES_COMMIT/scripts/install.sh" \
  -o "$tmp/install.sh"
bash "$tmp/install.sh" --commit "$HERMES_COMMIT" --non-interactive --skip-browser --skip-computer-use
rm -rf "$tmp"
