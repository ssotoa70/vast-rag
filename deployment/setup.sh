#!/usr/bin/env bash
# setup.sh - Environment validation and dependency installation
#
# PRECONDITIONS: None (first script to run)
# POSTCONDITIONS: .venv exists with dependencies, storage dirs created

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ============================================================================
# PRECONDITION CHECKS
# ============================================================================

log_info "Starting VAST RAG environment setup..."

# Check Python version
log_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 not found. Install from https://python.org"
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ "$PYTHON_MAJOR" -lt 3 ]] || { [[ "$PYTHON_MAJOR" -eq 3 ]] && [[ "$PYTHON_MINOR" -lt 11 ]]; }; then
    log_error "Python 3.11+ required. Found: $PYTHON_VERSION"
fi

log_success "Python version: $PYTHON_VERSION ✓"

# Check disk space
log_info "Checking available disk space..."
AVAILABLE_MB=$(df -m "$HOME" | tail -n1 | awk '{print $4}')

if [[ "$AVAILABLE_MB" -lt 1024 ]]; then
    log_warn "Low disk space: ${AVAILABLE_MB}MB available. Indexing may fail if <1GB"
fi

# ============================================================================
# VALIDATE DOCUMENT PATH
# ============================================================================

log_info "Validating document path..."

if [[ ! -d "$RAG_DOCS_PATH" ]]; then
    log_error "Document directory not found: $RAG_DOCS_PATH

Setup instructions:
  1. Create directory: mkdir -p $RAG_DOCS_PATH
  2. Add VAST Data documentation:
     - Create subdirectory: mkdir -p $RAG_DOCS_PATH/vast-data
     - Add PDFs, markdown files, or documentation
  3. Re-run setup: $0"
fi

log_success "Document path exists: $RAG_DOCS_PATH ✓"

# ============================================================================
# VIRTUAL ENVIRONMENT
# ============================================================================

log_info "Setting up Python virtual environment..."

if [[ -d "$VENV_PATH" ]]; then
    log_info "Virtual environment exists, activating..."
else
    log_info "Creating new virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate venv
source "$VENV_PATH/bin/activate"

log_success "Virtual environment activated ✓"

# ============================================================================
# DEPENDENCIES
# ============================================================================

log_info "Installing/upgrading dependencies..."

# Upgrade pip first
python -m pip install --upgrade pip --quiet

# Install project dependencies
if [[ ! -f "$VAST_RAG_ROOT/pyproject.toml" ]]; then
    log_error "pyproject.toml not found in $VAST_RAG_ROOT"
fi

cd "$VAST_RAG_ROOT"
python -m pip install -e "." --quiet
log_success "Dependencies installed ✓"

# ============================================================================
# EMBEDDING MODEL
# ============================================================================

log_info "Downloading embedding model (one-time, ~133MB)..."

# Test if model can be loaded
python -c "
from sentence_transformers import SentenceTransformer
import sys

try:
    model = SentenceTransformer('BAAI/bge-base-en-v1.5')
    print('Model loaded successfully')
    sys.exit(0)
except Exception as e:
    print(f'Model download failed: {e}', file=sys.stderr)
    sys.exit(1)
" || log_error "Failed to download embedding model. Check internet connection."

log_success "Embedding model cached ✓"

# ============================================================================
# STORAGE DIRECTORIES
# ============================================================================

log_info "Creating storage directories..."

ensure_dir "$RAG_DATA_PATH"
ensure_dir "$RAG_DATA_PATH/chroma"
ensure_dir "$RAG_DATA_PATH/cache"
ensure_dir "$RAG_DATA_PATH/logs"
ensure_dir "$RAG_DATA_PATH/index"

log_success "Storage structure created ✓"

# ============================================================================
# ENVIRONMENT FILE
# ============================================================================

log_info "Generating .env file..."

ENV_FILE="$VAST_RAG_ROOT/.env"

if [[ -f "$ENV_FILE" ]]; then
    log_info ".env already exists, skipping generation"
else
    if [[ ! -f "$SCRIPT_DIR/templates/.env.template" ]]; then
        log_error "Template file not found: $SCRIPT_DIR/templates/.env.template"
    fi

    cp "$SCRIPT_DIR/templates/.env.template" "$ENV_FILE"

    # Replace placeholders with actual paths (platform-specific sed syntax)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS requires empty string after -i
        sed -i '' "s|RAG_DOCS_PATH=.*|RAG_DOCS_PATH=$RAG_DOCS_PATH|" "$ENV_FILE"
        sed -i '' "s|RAG_DATA_PATH=.*|RAG_DATA_PATH=$RAG_DATA_PATH|" "$ENV_FILE"
    else
        # Linux doesn't use empty string after -i
        sed -i "s|RAG_DOCS_PATH=.*|RAG_DOCS_PATH=$RAG_DOCS_PATH|" "$ENV_FILE"
        sed -i "s|RAG_DATA_PATH=.*|RAG_DATA_PATH=$RAG_DATA_PATH|" "$ENV_FILE"
    fi

    log_success "Generated .env from template ✓"
fi

# ============================================================================
# COMPLETION
# ============================================================================

log_success "Setup complete!"
log_info "Next steps:"
log_info "  1. Review configuration: cat .env"
log_info "  2. Install MCP server: ./deployment/install.sh"
log_info "  3. Verify installation: ./deployment/verify.sh"
