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

    log_info "Restoring from backup: $LATEST_BACKUP"
    cp "$LATEST_BACKUP" "$CLAUDE_CONFIG"

    # Remove project-local example
    rm -f "$VAST_RAG_ROOT/.mcp.json.example"

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
    log_info "jq not found, installing via Homebrew..."

    if ! command -v brew &> /dev/null; then
        log_error "Homebrew not found. Install from https://brew.sh, then re-run this script."
    fi

    brew install jq
    log_success "jq installed ✓"
fi

# ============================================================================
# BACKUP CONFIGURATION
# ============================================================================

log_info "Backing up Claude Desktop configuration..."

BACKUP_FILE=$(backup_file "$CLAUDE_CONFIG")

if [[ -z "$BACKUP_FILE" ]]; then
    log_warn "Backup failed. Proceeding anyway (risky)..."
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

# ============================================================================
# UPDATE CONFIGURATION
# ============================================================================

log_info "Updating Claude Desktop configuration..."

# Create temporary file
TMP_CONFIG=$(mktemp)

# Check if vast-rag already exists
if jq -e '.mcpServers["vast-rag"]' "$CLAUDE_CONFIG" >/dev/null 2>&1; then
    log_info "vast-rag entry exists, updating..."
    jq --argjson entry "$MCP_ENTRY" '.mcpServers["vast-rag"] = $entry' "$CLAUDE_CONFIG" > "$TMP_CONFIG"
else
    log_info "Adding new vast-rag entry..."

    # Check if mcpServers exists
    if ! jq -e '.mcpServers' "$CLAUDE_CONFIG" >/dev/null 2>&1; then
        # Create mcpServers section
        jq '. + {mcpServers: {}}' "$CLAUDE_CONFIG" > "$TMP_CONFIG.init"
        mv "$TMP_CONFIG.init" "$CLAUDE_CONFIG"
    fi

    jq --argjson entry "$MCP_ENTRY" '.mcpServers["vast-rag"] = $entry' "$CLAUDE_CONFIG" > "$TMP_CONFIG"
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
# COMPLETION
# ============================================================================

log_success "MCP server installation complete!"
log_info "Next steps:"
log_info "  1. Restart Claude Desktop to activate MCP server"
log_info "  2. Verify installation: ./deployment/verify.sh"
log_info ""
log_info "To rollback: $0 --rollback"
