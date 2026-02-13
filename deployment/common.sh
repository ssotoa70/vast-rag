#!/usr/bin/env bash
#
# common.sh - Shared configuration and utility functions for VAST RAG deployment
#
# This file provides common variables, logging functions, and utilities used across
# all deployment scripts. Source this file at the beginning of each deployment script.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Exit on error, undefined variables, and pipe failures
set -euo pipefail

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# Project root directory (parent of deployment/)
VAST_RAG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Python virtual environment path
VENV_PATH="${VAST_RAG_ROOT}/.venv"

# Claude configuration file path
CLAUDE_CONFIG="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"

# RAG documentation path (can be overridden via environment variable)
RAG_DOCS_PATH="${RAG_DOCS_PATH:-$HOME/projects/RAG}"

# RAG data storage path
RAG_DATA_PATH="${RAG_DATA_PATH:-$HOME/.claude/rag-data}"

# Export paths for use in subshells
export VAST_RAG_ROOT VENV_PATH CLAUDE_CONFIG RAG_DOCS_PATH RAG_DATA_PATH

# ============================================================================
# COLOR CODES FOR TERMINAL OUTPUT
# ============================================================================

# Detect if output is to a terminal (TTY)
if [[ -t 1 ]]; then
    # Terminal supports colors
    COLOR_RESET='\033[0m'
    COLOR_RED='\033[0;31m'
    COLOR_GREEN='\033[0;32m'
    COLOR_YELLOW='\033[0;33m'
    COLOR_BLUE='\033[0;34m'
    COLOR_CYAN='\033[0;36m'
    COLOR_BOLD='\033[1m'
else
    # No color support (non-TTY, e.g., piped to file)
    COLOR_RESET=''
    COLOR_RED=''
    COLOR_GREEN=''
    COLOR_YELLOW=''
    COLOR_BLUE=''
    COLOR_CYAN=''
    COLOR_BOLD=''
fi

# Export color codes
export COLOR_RESET COLOR_RED COLOR_GREEN COLOR_YELLOW COLOR_BLUE COLOR_CYAN COLOR_BOLD

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

# log_info: Print informational message
# Usage: log_info "message"
log_info() {
    echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $*"
}

# log_success: Print success message
# Usage: log_success "message"
log_success() {
    echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $*"
}

# log_warn: Print warning message
# Usage: log_warn "message"
log_warn() {
    echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $*" >&2
}

# log_error: Print error message and exit
# Usage: log_error "message"
log_error() {
    echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*" >&2
    exit 1
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# check_command: Verify that a command exists in PATH
# Usage: check_command "command_name"
# Returns: 0 if command exists, 1 otherwise
check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &>/dev/null; then
        log_error "Required command not found: $cmd"
        return 1
    fi
    return 0
}

# backup_file: Create a timestamped backup of a file
# Usage: backup_file "file_path"
# Returns: 0 on success, 1 on failure
backup_file() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        log_warn "File not found, skipping backup: $file"
        return 1
    fi

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup="${file}.backup.${timestamp}"

    if cp "$file" "$backup"; then
        log_info "Backed up: $file -> $backup"
        echo "$backup"
        return 0
    else
        log_error "Failed to backup: $file"
        return 1
    fi
}

# get_latest_backup: Find the most recent backup of a file
# Usage: get_latest_backup "file_path"
# Output: Path to latest backup file, or empty string if none found
get_latest_backup() {
    local file="$1"
    local backup_pattern="${file}.backup.*"

    # Find all backups and sort by timestamp (newest first)
    local latest
    latest=$(find "$(dirname "$file")" -maxdepth 1 -name "$(basename "$backup_pattern")" 2>/dev/null | sort -r | head -n1)

    if [[ -n "$latest" ]]; then
        echo "$latest"
        return 0
    else
        log_warn "No backup found for: $file"
        return 1
    fi
}

# validate_json: Validate JSON file syntax using Python
# Usage: validate_json "json_file"
# Returns: 0 if valid, 1 if invalid
validate_json() {
    local json_file="$1"

    if [[ ! -f "$json_file" ]]; then
        log_error "JSON file not found: $json_file"
        return 1
    fi

    if python3 -c "import sys, json; json.load(open(sys.argv[1]))" "$json_file" 2>/dev/null; then
        return 0
    else
        log_error "Invalid JSON in file: $json_file"
        return 1
    fi
}

# ensure_dir: Create directory if it doesn't exist
# Usage: ensure_dir "directory_path"
# Returns: 0 on success (directory exists or was created)
ensure_dir() {
    local dir="$1"

    if [[ ! -d "$dir" ]]; then
        if mkdir -p "$dir"; then
            log_info "Created directory: $dir"
            return 0
        else
            log_error "Failed to create directory: $dir"
            return 1
        fi
    fi
    return 0
}

# ============================================================================
# INITIALIZATION
# ============================================================================

# Log that common utilities have been loaded
log_info "Common utilities loaded from: ${BASH_SOURCE[0]}"
log_info "Project root: $VAST_RAG_ROOT"
