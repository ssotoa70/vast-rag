#!/usr/bin/env bash
# deploy.sh - Full deployment orchestrator
#
# Runs: setup → install → verify

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ============================================================================
# ORCHESTRATION
# ============================================================================

log_info "Starting VAST RAG full deployment..."
echo ""

# Step 1: Setup
log_info "Step 1/3: Environment setup"
"$SCRIPT_DIR/setup.sh" || log_error "Setup failed. Check errors above."

echo ""

# Step 2: Install
log_info "Step 2/3: MCP server installation"
"$SCRIPT_DIR/install.sh" || log_error "Installation failed. Check errors above."

echo ""

# Step 3: Verify
log_info "Step 3/3: Verification"
"$SCRIPT_DIR/verify.sh" || log_error "Verification failed. Check errors above."

# ============================================================================
# COMPLETION
# ============================================================================

echo ""
echo "=========================================="
log_success "Deployment complete!"
echo "=========================================="
echo ""
log_info "Next steps:"
log_info "  1. Restart Claude Desktop (if using Desktop)"
log_info "  2. In Claude Code, run /mcp to verify vast-rag is enabled"
log_info "  3. Add documents to: $RAG_DOCS_PATH"
log_info "  4. Test: Ask Claude 'Search vast-rag docs for <topic>'"
echo ""
log_info "Logs:"
log_info "  - Deployment: ~/.claude/rag-data/logs/deployment.log"
log_info "  - Verification: ~/.claude/rag-data/logs/verify.log"
echo ""
