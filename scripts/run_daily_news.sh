#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/marcus/projects/pageDalliy"
PROMPT_FILE="$PROJECT_DIR/prompts/daily_news_codex_prompt.md"
LOCAL_PIPELINE="$PROJECT_DIR/scripts/generate_daily_news.py"
LOG_DIR="$PROJECT_DIR/logs"
LOCK_DIR="$PROJECT_DIR/tmp/.daily_news_lock"
DATE_TAG="$(date +%F_%H-%M-%S)"
RUN_LOG="$LOG_DIR/run_$DATE_TAG.log"

# launchd has a minimal PATH; pin common locations and a discovered codex binary.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
CODEX_BIN="${CODEX_BIN:-/Users/marcus/.vscode/extensions/openai.chatgpt-26.304.20706-darwin-arm64/bin/macos-aarch64/codex}"

mkdir -p "$LOG_DIR" "$PROJECT_DIR/tmp"

if [ ! -x "$CODEX_BIN" ] && [ ! -x "$LOCAL_PIPELINE" ]; then
  echo "[$(date '+%F %T')] codex CLI not found and local pipeline missing" | tee -a "$RUN_LOG"
  exit 1
fi

if [ ! -f "$PROMPT_FILE" ]; then
  echo "[$(date '+%F %T')] prompt file missing: $PROMPT_FILE" | tee -a "$RUN_LOG"
  exit 1
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$(date '+%F %T')] another run is in progress, skipping" | tee -a "$RUN_LOG"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

{
  echo "[$(date '+%F %T')] start daily news generation"
  if [ -x "$LOCAL_PIPELINE" ]; then
    "$LOCAL_PIPELINE"
  else
    "$CODEX_BIN" exec \
      --cd "$PROJECT_DIR" \
      --skip-git-repo-check \
      --dangerously-bypass-approvals-and-sandbox \
      "$(cat "$PROMPT_FILE")"
  fi
  echo "[$(date '+%F %T')] done"
} >>"$RUN_LOG" 2>&1
