#!/usr/bin/env bash
#
# sync-education-assets.sh - Validate and sync education-course-studio assets
#
# Source of truth:
#   - agents/education-course-studio/
#   - skills/custom/* (9 required education skills)
#
# Runtime target:
#   - ${DEER_FLOW_HOME:-backend/.deer-flow}/agents/education-course-studio

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_AGENT_DIR="$REPO_ROOT/agents/education-course-studio"
RUNTIME_HOME="${DEER_FLOW_HOME:-$REPO_ROOT/backend/.deer-flow}"
RUNTIME_AGENTS_DIR="$RUNTIME_HOME/agents"
RUNTIME_AGENT_DIR="$RUNTIME_AGENTS_DIR/education-course-studio"

REQUIRED_AGENT_FILES=(
    "config.yaml"
    "SOUL.md"
)

REQUIRED_SKILLS=(
    "education-intake"
    "ubd-stage-1"
    "education-research"
    "ubd-stage-2"
    "ubd-stage-3-pbl"
    "learning-kit-planning"
    "education-presentation"
    "course-quality-review"
    "course-quality-critic"
)

missing=()

if [ ! -d "$SOURCE_AGENT_DIR" ]; then
    missing+=("agents/education-course-studio/")
fi

for file in "${REQUIRED_AGENT_FILES[@]}"; do
    if [ ! -f "$SOURCE_AGENT_DIR/$file" ]; then
        missing+=("agents/education-course-studio/$file")
    fi
done

for skill in "${REQUIRED_SKILLS[@]}"; do
    if [ ! -f "$REPO_ROOT/skills/custom/$skill/SKILL.md" ]; then
        missing+=("skills/custom/$skill/SKILL.md")
    fi
done

if [ "${#missing[@]}" -gt 0 ]; then
    echo "ERROR: Education demo asset validation failed."
    echo "Missing required files:"
    for item in "${missing[@]}"; do
        echo "  - $item"
    done
    exit 1
fi

mkdir -p "$RUNTIME_AGENTS_DIR"

source_real="$(cd "$SOURCE_AGENT_DIR" && pwd)"
runtime_real="$(cd "$RUNTIME_AGENTS_DIR" && pwd)/education-course-studio"

if [ "$source_real" = "$runtime_real" ]; then
    echo "OK: Education assets validated in-place: $source_real"
    exit 0
fi

rm -rf "$RUNTIME_AGENT_DIR"
cp -R "$SOURCE_AGENT_DIR" "$RUNTIME_AGENT_DIR"

echo "OK: Education assets synced:"
echo "  source : $SOURCE_AGENT_DIR"
echo "  runtime: $RUNTIME_AGENT_DIR"
