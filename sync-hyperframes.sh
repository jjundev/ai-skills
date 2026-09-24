#!/usr/bin/env bash
# ==============================================================================
# sync-hyperframes.sh — pull HyperFrames skills and plugin assets from upstream
# (heygen-com/hyperframes).
#
# Copies skills to:
#   1. Repository root: $SKILLS_DIR/<skill> (consumed by Antigravity, Claude, Codex)
#   2. Portable plugin: $SKILLS_DIR/plugins/hyperframes/skills/<skill>
#   3. AI Skills bundle: $SKILLS_DIR/plugins/ai-skills/skills/<skill>
#
# Also updates plugin manifests and assets under $SKILLS_DIR/plugins/hyperframes/
# and registers in $SKILLS_DIR/.agents/plugins/marketplace.json.
#
# Env overrides:
#   HYPERFRAMES_REPO  git URL to clone (default: https://github.com/heygen-com/hyperframes.git)
#   NO_COMMIT         copy files but skip git commit (default: 0)
# ==============================================================================
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HYPERFRAMES_REPO="${HYPERFRAMES_REPO:-https://github.com/heygen-com/hyperframes.git}"
NO_COMMIT="${NO_COMMIT:-0}"

HYPERFRAMES_SKILLS=(
  embedded-captions
  faceless-explainer
  figma
  general-video
  hyperframes
  hyperframes-animation
  hyperframes-audio
  hyperframes-cli
  hyperframes-core
  hyperframes-creative
  hyperframes-keyframes
  hyperframes-registry
  hyperframes-studio
  media-use
  motion-graphics
  music-to-video
  pr-to-video
  product-launch-video
  remotion-to-hyperframes
  slideshow
  talking-head-recut
)

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

WARN_COUNT=0

print_warn_summary() {
  if [ "$WARN_COUNT" -gt 0 ]; then
    echo "⚠ $WARN_COUNT allowlisted skill(s) missing upstream - see WARN lines above" >&2
  fi
}

echo "=== Cloning heygen-com/hyperframes ==="
git clone --quiet --depth 1 "$HYPERFRAMES_REPO" "$TMP_DIR/hyperframes"

HF_CLONE="$TMP_DIR/hyperframes"
HF_TAG="$(git -C "$HF_CLONE" describe --tags --exact-match 2>/dev/null || true)"
HF_SHA7="$(git -C "$HF_CLONE" rev-parse --short=7 HEAD)"

HF_SYNCED=()

PLUGIN_DIR="$SKILLS_DIR/plugins/hyperframes"
AI_SKILLS_PLUGIN_DIR="$SKILLS_DIR/plugins/ai-skills/skills"
mkdir -p "$PLUGIN_DIR/skills" "$AI_SKILLS_PLUGIN_DIR"

echo "=== Syncing HyperFrames skills ==="
for name in "${HYPERFRAMES_SKILLS[@]}"; do
  if [ ! -d "$HF_CLONE/skills/$name" ]; then
    echo "WARN: HyperFrames upstream has no skills/$name - skipping" >&2
    WARN_COUNT=$((WARN_COUNT + 1))
    continue
  fi

  # 1. Root skill directory (Antigravity, Claude, Codex global sync)
  rm -rf "${SKILLS_DIR:?}/$name"
  cp -R "$HF_CLONE/skills/$name" "$SKILLS_DIR/$name"

  # 2. plugins/hyperframes/skills (dedicated portable package)
  rm -rf "${PLUGIN_DIR:?}/skills/$name"
  cp -R "$HF_CLONE/skills/$name" "$PLUGIN_DIR/skills/$name"

  # 3. plugins/ai-skills/skills (ai-skills portable bundle mirror)
  rm -rf "${AI_SKILLS_PLUGIN_DIR:?}/$name"
  cp -R "$HF_CLONE/skills/$name" "$AI_SKILLS_PLUGIN_DIR/$name"

  HF_SYNCED+=("$name")
  echo "  • Synced $name"
done

if [ "${#HF_SYNCED[@]}" -eq 0 ]; then
  echo "Nothing synced (every allowlisted skill was missing upstream)." >&2
  print_warn_summary
  exit 1
fi

echo "=== Updating HyperFrames plugin metadata & assets ==="
# Assets
if [ -d "$HF_CLONE/assets" ]; then
  mkdir -p "$PLUGIN_DIR/assets"
  cp -R "$HF_CLONE/assets/"* "$PLUGIN_DIR/assets/" 2>/dev/null || true
fi

# Claude Plugin compatibility directory
if [ -d "$HF_CLONE/.claude-plugin" ]; then
  mkdir -p "$PLUGIN_DIR/.claude-plugin"
  cp -R "$HF_CLONE/.claude-plugin/"* "$PLUGIN_DIR/.claude-plugin/" 2>/dev/null || true
fi

# Codex Plugin compatibility directory
if [ -d "$HF_CLONE/.codex-plugin" ]; then
  mkdir -p "$PLUGIN_DIR/.codex-plugin"
  cp -R "$HF_CLONE/.codex-plugin/"* "$PLUGIN_DIR/.codex-plugin/" 2>/dev/null || true
fi

# Read version from upstream plugin.json or package.json
VERSION="0.8.71"
if [ -f "$HF_CLONE/.claude-plugin/plugin.json" ]; then
  V_EXTRACT=$(python3 -c "import json, sys; 
try:
  d = json.load(open(sys.argv[1]))
  print(d.get('version', '0.8.71'))
except: print('0.8.71')" "$HF_CLONE/.claude-plugin/plugin.json" 2>/dev/null || true)
  if [ -n "$V_EXTRACT" ]; then
    VERSION="$V_EXTRACT"
  fi
fi

# Generate / update plugins/hyperframes/plugin.json
cat <<EOF > "$PLUGIN_DIR/plugin.json"
{
  "\$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "hyperframes",
  "version": "$VERSION",
  "description": "HyperFrames by HeyGen. Write HTML, render video. Compositions, Tailwind v4 styles, GSAP and runtime adapter animations, captions, voiceovers, audio-reactive visuals, and website capture for HyperFrames.",
  "author": {
    "name": "HeyGen",
    "email": "hyperframes@heygen.com",
    "url": "https://hyperframes.heygen.com"
  },
  "repository": "https://github.com/heygen-com/hyperframes",
  "license": "Apache-2.0",
  "keywords": [
    "hyperframes",
    "video",
    "html",
    "animation",
    "gsap",
    "rendering",
    "captions",
    "motion-graphics"
  ],
  "skills": "./skills/",
  "extensions": {
    "com.openai": {
      "interface": {
        "displayName": "HyperFrames by HeyGen",
        "shortDescription": "Write HTML, render video",
        "longDescription": "Build videos from HTML with HyperFrames. Author compositions with HTML, CSS, Tailwind v4 browser-runtime styles, GSAP, Anime.js, Lottie, Three.js, and WAAPI adapter patterns, use the CLI for the dev loop (init/preview/render), preprocess assets for compositions, install reusable registry blocks, and turn any website into a video.",
        "developerName": "HeyGen",
        "category": "Creativity",
        "capabilities": ["Read", "Write"],
        "websiteURL": "https://hyperframes.heygen.com"
      }
    }
  }
}
EOF

# Generate plugins/hyperframes/README.md
cat <<'EOF' > "$PLUGIN_DIR/README.md"
# HyperFrames Plugin

This directory is the portable plugin package for HyperFrames by HeyGen in the [`jjundev/ai-skills`](https://github.com/jjundev/ai-skills) repository.

## Overview
HyperFrames enables AI agents (Claude Code, Antigravity, Codex) to author, preview, and render videos from HTML, CSS, and JavaScript.

## Included Skills
- `hyperframes`: Router and orchestration entry point
- `faceless-explainer`: Concept explainer videos with kinetic typography and diagrams
- `motion-graphics`: Short design-led motion graphics (<10s)
- `product-launch-video`: Web / landing page promotional videos
- `pr-to-video`: GitHub PR code diff video walkthroughs
- `embedded-captions`: Synchronized captions on video footage
- `talking-head-recut`: Graphic overlays on interview / footage
- `slideshow`: Navigable decks and presentations
- `remotion-to-hyperframes`: Remotion composition migration
- `music-to-video`: Beat-synced visual animations
- `figma`: Figma design asset extraction and motion reconstruction
- `general-video`: Custom video compositions
- Domain skills: `hyperframes-animation`, `hyperframes-audio`, `hyperframes-cli`, `hyperframes-core`, `hyperframes-creative`, `hyperframes-keyframes`, `hyperframes-registry`, `hyperframes-studio`, `media-use`
EOF

# Register in .agents/plugins/marketplace.json if present
MARKETPLACE_JSON="$SKILLS_DIR/.agents/plugins/marketplace.json"
if [ -f "$MARKETPLACE_JSON" ]; then
  python3 -c "
import json, sys

path = sys.argv[1]
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    plugins = data.setdefault('plugins', [])
    names = [p.get('name') for p in plugins if isinstance(p, dict)]
    if 'hyperframes' not in names:
        plugins.append({
            'name': 'hyperframes',
            'source': {
                'source': 'local',
                'path': './plugins/hyperframes'
            },
            'policy': {
                'installation': 'AVAILABLE',
                'authentication': 'ON_INSTALL'
            },
            'category': 'Creativity'
        })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        print('  • Registered hyperframes in .agents/plugins/marketplace.json')
except Exception as e:
    print(f'WARN: Failed to update marketplace.json: {e}', file=sys.stderr)
" "$MARKETPLACE_JSON"
fi

if [ "$NO_COMMIT" = "1" ]; then
  echo "NO_COMMIT=1: files updated, skipping git commit."
  print_warn_summary
  exit 0
fi

cd "$SKILLS_DIR"

echo "=== Committing changes ==="
STAGING_PATHS=("${HF_SYNCED[@]}" "plugins/hyperframes")
for s in "${HF_SYNCED[@]}"; do
  STAGING_PATHS+=("plugins/ai-skills/skills/$s")
done
if [ -f "$MARKETPLACE_JSON" ]; then
  STAGING_PATHS+=(".agents/plugins/marketplace.json")
fi

git add -A -- "${STAGING_PATHS[@]}"

if git diff --cached --quiet; then
  echo "✨ All HyperFrames skills and plugin assets are already up-to-date."
  print_warn_summary
  exit 0
fi

if [ -n "$HF_TAG" ]; then
  SUBJECT="chore: sync hyperframes $HF_TAG ($HF_SHA7)"
else
  SUBJECT="chore: sync hyperframes ($HF_SHA7)"
fi

git commit -q -m "$SUBJECT"
echo "✅ Committed HyperFrames: $SUBJECT"

print_warn_summary
