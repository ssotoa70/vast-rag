#!/usr/bin/env bash
# install.sh - MCP server registration in Claude Desktop
#
# PRECONDITIONS: .venv exists with dependencies
# POSTCONDITIONS: vast-rag registered in Claude Desktop config

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ============================================================================
# FLAGS
# ============================================================================

DRY_RUN=false
ROLLBACK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        *)
            log_error "Unknown option: $1

Usage: $0 [--dry-run] [--rollback]"
            ;;
    esac
done

# ============================================================================
# ROLLBACK MODE
# ============================================================================

if [[ "$ROLLBACK" == true ]]; then
    log_info "Rolling back MCP server installation..."

    if [[ ! -f "$CLAUDE_CONFIG" ]]; then
        log_error "Claude Desktop config not found: $CLAUDE_CONFIG"
    fi

    # Find latest backup
    LATEST_BACKUP=$(get_latest_backup "$CLAUDE_CONFIG")
    if [[ -z "$LATEST_BACKUP" ]]; then
        log_error "No backup found. Cannot rollback."
    fi

    log_info "Restoring from backup: $LATEST_BACKUP"
    cp "$LATEST_BACKUP" "$CLAUDE_CONFIG"

    # Remove project-local example
    rm -f "$VAST_RAG_ROOT/.mcp.json.example"

    # Remove from Claude Code config
    if [[ -f "$CLAUDE_CODE_CONFIG" ]] && jq -e '.mcpServers["vast-rag"]' "$CLAUDE_CODE_CONFIG" >/dev/null 2>&1; then
        TMP_CC_CONFIG=$(mktemp)
        jq 'del(.mcpServers["vast-rag"])' "$CLAUDE_CODE_CONFIG" > "$TMP_CC_CONFIG"
        mv "$TMP_CC_CONFIG" "$CLAUDE_CODE_CONFIG"
        log_info "Removed vast-rag from Claude Code config."
    fi

    log_success "Rollback complete. Restart Claude Desktop to apply changes."
    exit 0
fi

# ============================================================================
# PRECONDITION CHECKS
# ============================================================================

log_info "Starting MCP server installation..."

# Check venv exists
if [[ ! -d "$VENV_PATH" ]]; then
    log_error "Virtual environment not found. Run setup.sh first:
    ./deployment/setup.sh"
fi

# Check Claude Desktop config exists
if [[ ! -f "$CLAUDE_CONFIG" ]]; then
    log_error "Claude Desktop config not found: $CLAUDE_CONFIG

Is Claude Desktop installed?
Expected location: ~/Library/Application Support/Claude/"
fi

# Check jq is available
if ! command -v jq &> /dev/null; then
    log_error "jq is required but not installed. Install it with:
    brew install jq
Then re-run this script."
fi

# ============================================================================
# BACKUP CONFIGURATION
# ============================================================================

log_info "Backing up Claude Desktop configuration..."

BACKUP_FILE=$(backup_file "$CLAUDE_CONFIG")

if [[ -z "$BACKUP_FILE" ]]; then
    log_error "Failed to create backup. Cannot proceed safely.
Use --force to override (not recommended)"
fi

# ============================================================================
# BUILD MCP CONFIGURATION
# ============================================================================

log_info "Building MCP server configuration..."

# Absolute paths for MCP config
PYTHON_BIN="$VENV_PATH/bin/python"
SERVER_MODULE="vast_rag.server"

# Build JSON configuration
MCP_ENTRY=$(cat <<EOF
{
  "command": "$PYTHON_BIN",
  "args": ["-m", "$SERVER_MODULE"],
  "env": {
    "RAG_DOCS_PATH": "$RAG_DOCS_PATH",
    "RAG_DATA_PATH": "$RAG_DATA_PATH"
  }
}
EOF
)

# Validate generated JSON
echo "$MCP_ENTRY" | jq . >/dev/null 2>&1 || log_error "Generated invalid MCP entry JSON"

# ============================================================================
# UPDATE CONFIGURATION
# ============================================================================

log_info "Updating Claude Desktop configuration..."

# Create temporary file
TMP_CONFIG=$(mktemp)
trap 'rm -f "$TMP_CONFIG"' EXIT

# Check if vast-rag already exists
if jq -e '.mcpServers["vast-rag"]' "$CLAUDE_CONFIG" >/dev/null 2>&1; then
    log_info "vast-rag entry exists, updating..."
    jq --argjson entry "$MCP_ENTRY" '.mcpServers["vast-rag"] = $entry' "$CLAUDE_CONFIG" > "$TMP_CONFIG"
else
    log_info "Adding new vast-rag entry..."

    # Check if mcpServers exists
    if ! jq -e '.mcpServers' "$CLAUDE_CONFIG" >/dev/null 2>&1; then
        # Create mcpServers section and add vast-rag in one operation (atomic)
        jq '. + {mcpServers: {}}' "$CLAUDE_CONFIG" | \
            jq --argjson entry "$MCP_ENTRY" '.mcpServers["vast-rag"] = $entry' > "$TMP_CONFIG"
    else
        jq --argjson entry "$MCP_ENTRY" '.mcpServers["vast-rag"] = $entry' "$CLAUDE_CONFIG" > "$TMP_CONFIG"
    fi
fi

# Validate JSON
validate_json "$TMP_CONFIG"

# Show diff in dry-run mode
if [[ "$DRY_RUN" == true ]]; then
    log_info "Dry-run mode: showing changes (not applying)"
    echo "Diff:"
    diff "$CLAUDE_CONFIG" "$TMP_CONFIG" || true
    rm "$TMP_CONFIG"
    exit 0
fi

# Apply changes atomically
mv "$TMP_CONFIG" "$CLAUDE_CONFIG"

log_success "Claude Desktop configuration updated ✓"

# ============================================================================
# GENERATE PROJECT-LOCAL EXAMPLE
# ============================================================================

log_info "Generating .mcp.json.example..."

cat > "$VAST_RAG_ROOT/.mcp.json.example" <<EOF
{
  "mcpServers": {
    "vast-rag": {
      "command": "$PYTHON_BIN",
      "args": ["-m", "$SERVER_MODULE"],
      "env": {
        "RAG_DOCS_PATH": "$RAG_DOCS_PATH",
        "RAG_DATA_PATH": "$RAG_DATA_PATH"
      }
    }
  }
}
EOF

log_success "Generated .mcp.json.example ✓"

# ============================================================================
# REGISTER WITH CLAUDE CODE (workspace .mcp.json)
# ============================================================================

log_info "Registering MCP server with Claude Code..."

if [[ -f "$CLAUDE_CODE_CONFIG" ]]; then
    # Check if vast-rag already exists
    if jq -e '.mcpServers["vast-rag"]' "$CLAUDE_CODE_CONFIG" >/dev/null 2>&1; then
        log_info "vast-rag entry exists in Claude Code config, updating..."
        TMP_CC_CONFIG=$(mktemp)
        jq --argjson entry "$MCP_ENTRY" '.mcpServers["vast-rag"] = $entry' "$CLAUDE_CODE_CONFIG" > "$TMP_CC_CONFIG"
        if (validate_json "$TMP_CC_CONFIG") 2>/dev/null; then
            mv "$TMP_CC_CONFIG" "$CLAUDE_CODE_CONFIG"
            log_success "Claude Code configuration updated ✓"
        else
            log_warn "Failed to validate Claude Code config. Skipping update."
            rm -f "$TMP_CC_CONFIG"
        fi
    else
        log_info "Adding vast-rag to Claude Code config..."
        TMP_CC_CONFIG=$(mktemp)
        if jq -e '.mcpServers' "$CLAUDE_CODE_CONFIG" >/dev/null 2>&1; then
            jq --argjson entry "$MCP_ENTRY" '.mcpServers["vast-rag"] = $entry' "$CLAUDE_CODE_CONFIG" > "$TMP_CC_CONFIG"
        else
            jq --argjson entry "$MCP_ENTRY" '. + {mcpServers: {"vast-rag": $entry}}' "$CLAUDE_CODE_CONFIG" > "$TMP_CC_CONFIG"
        fi
        if (validate_json "$TMP_CC_CONFIG") 2>/dev/null; then
            mv "$TMP_CC_CONFIG" "$CLAUDE_CODE_CONFIG"
            log_success "Claude Code configuration updated ✓"
        else
            log_warn "Failed to validate Claude Code config. Skipping update."
            rm -f "$TMP_CC_CONFIG"
        fi
    fi
else
    log_warn "Claude Code workspace config not found: $CLAUDE_CODE_CONFIG"
    log_warn "To use with Claude Code, add vast-rag to your workspace .mcp.json manually."
fi

# ============================================================================
# COMPLETION
# ============================================================================

log_success "MCP server installation complete!"
log_info "Next steps:"
log_info "  1. Restart Claude Desktop to activate MCP server"
log_info "  2. In Claude Code, use /mcp to verify vast-rag is available"
log_info "  3. Verify installation: ./deployment/verify.sh"
log_info ""
log_info "To rollback: $0 --rollback"
