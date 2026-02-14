#!/usr/bin/env bash
# uninstall.sh - Clean removal with rollback
#
# PRECONDITIONS: None (safe to run anytime)
# POSTCONDITIONS: vast-rag removed from config, optional data cleanup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ============================================================================
# INTERACTIVE PROMPTS
# ============================================================================

log_info "VAST RAG Uninstaller"
log_info "===================="
echo ""

# Prompt 1: Remove MCP registration
read -rp "Remove vast-rag from Claude Desktop? [y/N] " response
REMOVE_MCP=false
if [[ "$response" =~ ^[Yy]$ ]]; then
    REMOVE_MCP=true
fi

# Prompt 2: Delete indexed data
read -rp "Delete ~/.claude/rag-data/? WARNING: All indexed docs will be lost [y/N] " response
DELETE_DATA=false
if [[ "$response" =~ ^[Yy]$ ]]; then
    DELETE_DATA=true
fi

# Prompt 3: Delete virtual environment
read -rp "Remove .venv/? (Can rebuild with setup.sh) [y/N] " response
DELETE_VENV=false
if [[ "$response" =~ ^[Yy]$ ]]; then
    DELETE_VENV=true
fi

echo ""

# ============================================================================
# REMOVE MCP REGISTRATION
# ============================================================================

if [[ "$REMOVE_MCP" == true ]]; then
    log_info "Removing vast-rag from Claude Desktop configuration..."

    if [[ ! -f "$CLAUDE_CONFIG" ]]; then
        log_warn "Claude Desktop config not found: $CLAUDE_CONFIG"
        log_warn "Skipping MCP removal (already absent)."
    else
        # Check if vast-rag entry exists before attempting removal
        if ! jq -e '.mcpServers["vast-rag"]' "$CLAUDE_CONFIG" >/dev/null 2>&1; then
            log_warn "vast-rag entry not found in Claude Desktop config. Skipping."
        else
            # Backup config before modifying
            BACKUP_FILE=$(backup_file "$CLAUDE_CONFIG") || true

            # Create temporary file for the modified config
            TMP_CONFIG=$(mktemp)
            trap 'rm -f "$TMP_CONFIG"' EXIT

            # Remove vast-rag entry
            jq 'del(.mcpServers["vast-rag"])' "$CLAUDE_CONFIG" > "$TMP_CONFIG"

            # Validate the new JSON
            validate_json "$TMP_CONFIG"

            # Replace original config with modified version
            mv "$TMP_CONFIG" "$CLAUDE_CONFIG"

            log_success "vast-rag removed from Claude Desktop configuration."
            if [[ -n "${BACKUP_FILE:-}" ]]; then
                log_info "Backup saved at: $BACKUP_FILE"
            fi
        fi
    fi

    # Remove project-local .mcp.json.example if it exists
    if [[ -f "$VAST_RAG_ROOT/.mcp.json.example" ]]; then
        rm -f "$VAST_RAG_ROOT/.mcp.json.example"
        log_info "Removed .mcp.json.example"
    fi
fi

# ============================================================================
# DELETE INDEXED DATA
# ============================================================================

if [[ "$DELETE_DATA" == true ]]; then
    log_info "Deleting indexed data..."

    if [[ -d "$RAG_DATA_PATH" ]]; then
        rm -rf "$RAG_DATA_PATH"
        log_success "Deleted indexed data: $RAG_DATA_PATH"
    else
        log_warn "Data directory not found: $RAG_DATA_PATH (already removed)"
    fi
fi

# ============================================================================
# DELETE VIRTUAL ENVIRONMENT
# ============================================================================

if [[ "$DELETE_VENV" == true ]]; then
    log_info "Deleting virtual environment..."

    if [[ -d "$VENV_PATH" ]]; then
        rm -rf "$VENV_PATH"
        log_success "Deleted virtual environment: $VENV_PATH"
    else
        log_warn "Virtual environment not found: $VENV_PATH (already removed)"
    fi
fi

# ============================================================================
# COMPLETION SUMMARY
# ============================================================================

echo ""
log_success "Uninstallation complete!"
echo ""
log_info "Preserved:"
log_info "  - Source code (always kept)"
log_info "  - Source documents in $RAG_DOCS_PATH (always kept)"
if [[ "$DELETE_DATA" != true ]]; then
    log_info "  - Indexed data in $RAG_DATA_PATH"
fi
if [[ "$DELETE_VENV" != true ]]; then
    log_info "  - Virtual environment in $VENV_PATH"
fi

if [[ "$REMOVE_MCP" == true ]]; then
    echo ""
    log_info "Restart Claude Desktop to apply configuration changes."
fi
