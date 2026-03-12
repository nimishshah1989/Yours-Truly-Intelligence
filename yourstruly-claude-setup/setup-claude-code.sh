#!/bin/bash
# ============================================================
# YoursTruly Intelligence Platform — Claude Code Setup
# Run this from the root of the yourstruly-intelligence repo
# Usage: bash setup-claude-code.sh
# ============================================================

set -e
echo ""
echo "============================================"
echo "  YoursTruly — Claude Code Setup"
echo "============================================"
echo ""

# Create .claude directory structure in project root
mkdir -p .claude/commands
mkdir -p .claude/skills/petpooja-integration
mkdir -p .claude/skills/tally-integration
mkdir -p .claude/skills/analytics-engine
mkdir -p .claude/skills/nl-query-pipeline
mkdir -p .claude/skills/supabase-patterns
mkdir -p .claude/skills/fastapi-patterns
mkdir -p .claude/agents

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Copy CLAUDE.md to project root
cp "$SCRIPT_DIR/CLAUDE.md" ./CLAUDE.md

# Copy commands
cp "$SCRIPT_DIR/.claude/commands/"*.md .claude/commands/

# Copy skills
cp "$SCRIPT_DIR/.claude/skills/petpooja-integration/SKILL.md"  .claude/skills/petpooja-integration/
cp "$SCRIPT_DIR/.claude/skills/tally-integration/SKILL.md"     .claude/skills/tally-integration/
cp "$SCRIPT_DIR/.claude/skills/analytics-engine/SKILL.md"      .claude/skills/analytics-engine/
cp "$SCRIPT_DIR/.claude/skills/nl-query-pipeline/SKILL.md"     .claude/skills/nl-query-pipeline/
cp "$SCRIPT_DIR/.claude/skills/supabase-patterns/SKILL.md"     .claude/skills/supabase-patterns/
cp "$SCRIPT_DIR/.claude/skills/fastapi-patterns/SKILL.md"      .claude/skills/fastapi-patterns/

# Copy agents
cp "$SCRIPT_DIR/.claude/agents/"*.md .claude/agents/

echo "✅ CLAUDE.md placed at project root"
echo "✅ Commands: architect, build, review, deploy, sync"
echo "✅ Skills: petpooja-integration, tally-integration, analytics-engine,"
echo "           nl-query-pipeline, supabase-patterns, fastapi-patterns"
echo "✅ Agents: code-reviewer, data-validator"
echo ""
echo "--------------------------------------------"
echo "  Next steps:"
echo "  1. cd yourstruly-intelligence"
echo "  2. claude  (opens Claude Code)"
echo "  3. Type: /architect Phase 1 — PetPooja ETL + Supabase schema"
echo "--------------------------------------------"
echo ""
