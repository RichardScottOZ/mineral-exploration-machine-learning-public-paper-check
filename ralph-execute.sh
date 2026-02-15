#!/bin/bash
# Ralph Execute Loop Script for Kiro CLI
# Runs the Ralph Wiggum execution loop with safety features

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MAX_ITERATIONS=50
COMPLETION_WORD="DONE"
PROMPT_FILE="PROMPT.md"
LOG_FILE="ralph-execution.log"

while [[ $# -gt 0 ]]; do
  case $1 in
    --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
    --completion-word) COMPLETION_WORD="$2"; shift 2 ;;
    --prompt-file) PROMPT_FILE="$2"; shift 2 ;;
    --log-file) LOG_FILE="$2"; shift 2 ;;
    --help)
      echo "Ralph Execute Loop - Run the autonomous execution phase"
      echo ""
      echo "Usage: ./ralph-execute.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --max-iterations N   Maximum iterations (default: 50)"
      echo "  --completion-word W  Word that signals completion (default: DONE)"
      echo "  --prompt-file F      Prompt file to use (default: PROMPT.md)"
      echo "  --log-file L         Log file path (default: ralph-execution.log)"
      echo "  --help               Show this help message"
      exit 0
      ;;
    *) echo -e "${RED}Error: Unknown option $1${NC}"; exit 1 ;;
  esac
done

if [ ! -f "$PROMPT_FILE" ]; then
  echo -e "${RED}Error: $PROMPT_FILE not found${NC}"
  echo "Make sure you've run the plan phase first."
  exit 1
fi

if ! command -v kiro-cli &> /dev/null; then
  echo -e "${RED}Error: kiro-cli not found${NC}"
  echo "Please install Kiro CLI: https://kiro.dev/cli/"
  exit 1
fi

echo "Ralph Execution Log - $(date)" > "$LOG_FILE"
echo "Max Iterations: $MAX_ITERATIONS" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Ralph Wiggum Execution Loop - Paper Checker  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Max Iterations: ${GREEN}$MAX_ITERATIONS${NC}"
echo -e "  Prompt File:    ${GREEN}$PROMPT_FILE${NC}"
echo -e "  Log File:       ${GREEN}$LOG_FILE${NC}"
echo ""

read -p "Ready to start execution? (y/n) " -n 1 -r
echo ""
[[ ! $REPLY =~ ^[Yy]$ ]] && echo -e "${YELLOW}Cancelled${NC}" && exit 0

iteration=0
start_time=$(date +%s)

while [ $iteration -lt $MAX_ITERATIONS ]; do
  iteration=$((iteration + 1))
  echo -e "${BLUE}━━━ Iteration $iteration/$MAX_ITERATIONS ━━━${NC}"
  echo "=== Iteration $iteration - $(date) ===" >> "$LOG_FILE"

  output=$(cat "$PROMPT_FILE" | kiro-cli chat --no-interactive -a 2>&1) || {
    echo -e "${RED}Error: kiro-cli failed${NC}"
    echo "$output" >> "$LOG_FILE"
    exit 1
  }

  echo "$output"
  echo "$output" >> "$LOG_FILE"

  if echo "$output" | grep -q "$COMPLETION_WORD"; then
    total_time=$(( $(date +%s) - start_time ))
    echo -e "${GREEN}✅ TASK COMPLETED at iteration $iteration! (${total_time}s)${NC}"
    echo "=== COMPLETED at iteration $iteration ===" >> "$LOG_FILE"
    exit 0
  fi

  if echo "$output" | grep -q "STUCK"; then
    echo -e "${RED}⚠️  EXECUTION STUCK at iteration $iteration${NC}"
    echo "=== STUCK at iteration $iteration ===" >> "$LOG_FILE"
    exit 1
  fi

  sleep 2
done

echo -e "${YELLOW}⚠️  Max iterations ($MAX_ITERATIONS) reached${NC}"
echo "=== MAX ITERATIONS REACHED ===" >> "$LOG_FILE"
exit 1
