#!/usr/bin/env bash
# Install the /visuals effect skills into your Claude skills directory.
# Usage: bash install.sh            (or CLAUDE_SKILLS_DIR=/path bash install.sh)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"
for d in "$SRC"/*/; do
  name="$(basename "$d")"
  rm -rf "$DEST/$name"
  cp -R "$d" "$DEST/$name"
  echo "installed $name -> $DEST/$name"
done
command -v ffmpeg >/dev/null || echo "WARNING: ffmpeg not found on PATH - install it (https://ffmpeg.org/download.html)"
python3 -c "import cv2, numpy, PIL" 2>/dev/null || python -c "import cv2, numpy, PIL" 2>/dev/null || \
  echo "WARNING: run  pip install -r requirements.txt  (opencv-python, numpy, pillow)"
echo
echo "Restart Claude Code, then try:  /orbit"
