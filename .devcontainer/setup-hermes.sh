#!/usr/bin/env bash
# Installs Hermes Agent, at a pinned version, with the configuration of this guide.
# Runs once, when the Codespace is created (postCreateCommand in devcontainer.json).
set -euo pipefail

# The version this guide was tested with (tag v0.22.5, this commit). A newer one comes out several
# times a week: change the commit and this tag, and test the guide again (ci/README.md).
HERMES_COMMIT=bf0203a794a07aac3ff764972ab9087baa4e4f4e

guide="$(cd "$(dirname "$0")/.." && pwd)"

# The configuration first: the installer keeps a config.yaml that is already there.
mkdir -p "$HOME/.hermes"
sed "s#@WORKSPACE@#$guide#g" "$guide/hermes/config.yaml" > "$HOME/.hermes/config.yaml"

# The installer of this same commit (a tag can move), then the commit. No browser and no "computer use"
# driver: this guide does not use them. --non-interactive: no setup wizard, no messaging gateway.
tmp="$(mktemp -d)"
curl -fsSL "https://raw.githubusercontent.com/NousResearch/hermes-agent/$HERMES_COMMIT/scripts/install.sh" \
  -o "$tmp/install.sh"
bash "$tmp/install.sh" --commit "$HERMES_COMMIT" --non-interactive --skip-browser --skip-computer-use
rm -rf "$tmp"
