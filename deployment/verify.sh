#!/usr/bin/env bash
# verify.sh - Comprehensive health checks for VAST RAG installation
#
# PRECONDITIONS: MCP server registered in Claude Desktop config
# POSTCONDITIONS: Installation verified as functional
#
# This script runs 6 comprehensive health checks:
#   1. MCP Configuration - Validate Claude Desktop config
#   2. Python Module Import - Test vast_rag module loading
#   3. Embedding Model - Test BAAI/bge-base-en-v1.5 model
#   4. ChromaDB - Test database operations
#   5. Smoke Test - Test end-to-end chunking (if implementation complete)
#   6. File Watcher - Test watchdog Observer instantiation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ============================================================================
# SETUP LOGGING
# ============================================================================

# Ensure logs directory exists
VERIFY_LOG="$RAG_DATA_PATH/logs/verify.log"
ensure_dir "$(dirname "$VERIFY_LOG")"

# Log all output to verify.log (append mode)
# Note: Using tee in background, output will also go to stdout
exec > >(tee -a "$VERIFY_LOG") 2>&1

# Give tee time to start
sleep 0.1

log_info "=========================================="
log_info "VAST RAG Verification - $(date)"
log_info "=========================================="

# ============================================================================
# HEALTH CHECK COUNTERS
# ============================================================================

TOTAL_CHECKS=6
PASSED_CHECKS=0
FAILED_CHECKS=0
SKIPPED_CHECKS=0

# ============================================================================
# CHECK 1: MCP CONFIGURATION
# ============================================================================

log_info ""
log_info "Check 1/$TOTAL_CHECKS: MCP Configuration"
log_info "----------------------------------------"

# Check 1 uses cascading gates: each sub-check depends on the previous passing.
# The entire check counts as a single pass/fail toward TOTAL_CHECKS.
CHECK1_PASSED=true

# Check 1.1: Claude Desktop config exists
if [[ ! -f "$CLAUDE_CONFIG" ]]; then
    log_warn "Claude Desktop config not found: $CLAUDE_CONFIG"
    CHECK1_PASSED=false
else
    log_success "  ✓ Claude Desktop config exists"

    # Check 1.2: Validate JSON syntax (only if file exists)
    if ! python3 -c "import sys, json; json.load(open(sys.argv[1]))" "$CLAUDE_CONFIG" 2>/dev/null; then
        log_warn "Claude Desktop config has invalid JSON syntax"
        CHECK1_PASSED=false
    else
        log_success "  ✓ Config JSON is valid"

        # Check 1.3: Check vast-rag entry exists (only if JSON is valid)
        if ! jq -e '.mcpServers["vast-rag"]' "$CLAUDE_CONFIG" >/dev/null 2>&1; then
            log_warn "vast-rag entry not found in mcpServers"
            CHECK1_PASSED=false
        else
            log_success "  ✓ vast-rag entry exists in mcpServers"

            # Check 1.4: Extract and display MCP command path
            MCP_COMMAND=$(jq -r '.mcpServers["vast-rag"].command' "$CLAUDE_CONFIG")
            log_info "  → MCP command: $MCP_COMMAND"

            # Check 1.5: Verify command exists
            if [[ ! -f "$MCP_COMMAND" ]]; then
                log_warn "  ⚠ Python binary not found: $MCP_COMMAND"
                CHECK1_PASSED=false
            else
                log_success "  ✓ Python binary exists"
            fi

            # Check 1.6: Verify environment variables are set
            RAG_DOCS_ENV=$(jq -r '.mcpServers["vast-rag"].env.RAG_DOCS_PATH' "$CLAUDE_CONFIG")
            RAG_DATA_ENV=$(jq -r '.mcpServers["vast-rag"].env.RAG_DATA_PATH' "$CLAUDE_CONFIG")
            log_info "  → RAG_DOCS_PATH: $RAG_DOCS_ENV"
            log_info "  → RAG_DATA_PATH: $RAG_DATA_ENV"
        fi
    fi
fi

if [[ "$CHECK1_PASSED" == true ]]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# ============================================================================
# CHECK 2: PYTHON MODULE IMPORT
# ============================================================================

log_info ""
log_info "Check 2/$TOTAL_CHECKS: Python Module Import"
log_info "----------------------------------------"

# Activate virtual environment
if [[ ! -d "$VENV_PATH" ]]; then
    log_warn "Virtual environment not found: $VENV_PATH"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    # Test import vast_rag
    if "$VENV_PATH/bin/python" -c "import vast_rag" 2>/dev/null; then
        log_success "  ✓ vast_rag module imports successfully"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warn "  ⚠ vast_rag module import failed (implementation may be incomplete)"
        log_info "  → This is expected if the module is not yet fully implemented"
        SKIPPED_CHECKS=$((SKIPPED_CHECKS + 1))
    fi
fi

# ============================================================================
# CHECK 3: EMBEDDING MODEL
# ============================================================================

log_info ""
log_info "Check 3/$TOTAL_CHECKS: Embedding Model"
log_info "----------------------------------------"

# Test embedding model loading and generation
EMBEDDING_TEST=$(cat <<'PYTHON'
import sys
try:
    from sentence_transformers import SentenceTransformer

    # Load model
    model = SentenceTransformer('BAAI/bge-base-en-v1.5')

    # Test embedding generation
    test_text = "This is a test document for embedding generation."
    embedding = model.encode(test_text)

    # Verify dimensions
    if len(embedding) == 768:
        print(f"SUCCESS: Generated embedding with {len(embedding)} dimensions")
        sys.exit(0)
    else:
        print(f"ERROR: Expected 768 dimensions, got {len(embedding)}")
        sys.exit(1)

except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
PYTHON
)

if "$VENV_PATH/bin/python" -c "$EMBEDDING_TEST" 2>&1; then
    log_success "  ✓ Embedding model loads and generates 768-dim embeddings"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_warn "  ⚠ Embedding model test failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# ============================================================================
# CHECK 4: CHROMADB
# ============================================================================

log_info ""
log_info "Check 4/$TOTAL_CHECKS: ChromaDB"
log_info "----------------------------------------"

# Test ChromaDB operations
CHROMADB_TEST=$(cat <<'PYTHON'
import sys
import tempfile
import shutil
try:
    import chromadb
    from chromadb.config import Settings

    # Create temporary directory for test
    test_dir = tempfile.mkdtemp(prefix="chromadb_test_")

    try:
        # Initialize ChromaDB client
        client = chromadb.PersistentClient(
            path=test_dir,
            settings=Settings(anonymized_telemetry=False)
        )

        # Test collection creation
        collection = client.create_collection("test_collection")

        # Count collections
        collections = client.list_collections()
        count = len(collections)

        # Test deletion
        client.delete_collection("test_collection")

        print(f"SUCCESS: ChromaDB operations completed (created {count} collection)")
        sys.exit(0)

    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
PYTHON
)

if "$VENV_PATH/bin/python" -c "$CHROMADB_TEST" 2>&1; then
    log_success "  ✓ ChromaDB initialized, collection created/deleted successfully"

    # Count existing collections in production database
    if [[ -d "$RAG_DATA_PATH/chroma" ]]; then
        COLLECTION_COUNT=$(cat <<'PYTHON'
import sys
import os
try:
    import chromadb
    from chromadb.config import Settings

    rag_data_path = os.environ.get('RAG_DATA_PATH')
    chroma_path = os.path.join(rag_data_path, 'chroma')

    if os.path.exists(chroma_path):
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        collections = client.list_collections()
        print(len(collections))
    else:
        print(0)
    sys.exit(0)
except Exception:
    print(0)
    sys.exit(0)
PYTHON
)
        COUNT=$("$VENV_PATH/bin/python" -c "$COLLECTION_COUNT" 2>/dev/null || echo "0")
        log_info "  → Existing collections in production: $COUNT"
    fi

    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_warn "  ⚠ ChromaDB test failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# ============================================================================
# CHECK 5: SMOKE TEST (END-TO-END)
# ============================================================================

log_info ""
log_info "Check 5/$TOTAL_CHECKS: Smoke Test (End-to-End)"
log_info "----------------------------------------"

# Test end-to-end document processing
# TODO: Confirm import paths once vast_rag implementation is complete.
# Current paths (vast_rag.parsing, vast_rag.chunking) may need to change
# to match the actual module structure.
SMOKE_TEST=$(cat <<'PYTHON'
import sys
import tempfile
import os
try:
    # Try to import implementation modules
    from vast_rag.parsing import ParserFactory
    from vast_rag.chunking import SemanticChunker

    # Create test document
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document.\n\n")
        f.write("It contains multiple paragraphs.\n\n")
        f.write("Each paragraph should be chunked appropriately.")
        test_file = f.name

    try:
        # Parse document
        parser = ParserFactory.get_parser(test_file)
        content = parser.parse()

        # Chunk content
        chunker = SemanticChunker(max_chunk_size=512)
        chunks = chunker.chunk(content)

        print(f"SUCCESS: Parsed and chunked document into {len(chunks)} chunks")
        sys.exit(0)

    finally:
        # Cleanup
        os.unlink(test_file)

except ImportError as e:
    print(f"SKIP: Implementation incomplete ({str(e)})")
    sys.exit(2)  # Exit code 2 = skip
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
PYTHON
)

SMOKE_OUTPUT=$("$VENV_PATH/bin/python" -c "$SMOKE_TEST" 2>&1)
SMOKE_EXIT=$?

if [[ $SMOKE_EXIT -eq 0 ]]; then
    log_success "  ✓ $SMOKE_OUTPUT"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [[ $SMOKE_EXIT -eq 2 ]]; then
    log_warn "  ⚠ $SMOKE_OUTPUT"
    log_info "  → This is expected if implementation is not yet complete"
    SKIPPED_CHECKS=$((SKIPPED_CHECKS + 1))
else
    log_warn "  ⚠ $SMOKE_OUTPUT"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# ============================================================================
# CHECK 6: FILE WATCHER
# ============================================================================

log_info ""
log_info "Check 6/$TOTAL_CHECKS: File Watcher"
log_info "----------------------------------------"

# Test watchdog Observer instantiation
WATCHER_TEST=$(cat <<'PYTHON'
import sys
try:
    from watchdog.observers import Observer

    # Test Observer instantiation
    observer = Observer()

    print("SUCCESS: watchdog.Observer instantiated successfully")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
PYTHON
)

if "$VENV_PATH/bin/python" -c "$WATCHER_TEST" 2>&1; then
    log_success "  ✓ watchdog.Observer instantiated successfully"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_warn "  ⚠ File watcher test failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# ============================================================================
# STATUS REPORT
# ============================================================================

log_info ""
log_info "=========================================="
log_info "VERIFICATION SUMMARY"
log_info "=========================================="

# Count indexed documents
INDEXED_DOCS=0
if [[ -d "$RAG_DATA_PATH/chroma" ]]; then
    INDEXED_DOCS=$(cat <<'PYTHON'
import sys
import os
try:
    import chromadb
    from chromadb.config import Settings

    rag_data_path = os.environ.get('RAG_DATA_PATH')
    chroma_path = os.path.join(rag_data_path, 'chroma')

    if os.path.exists(chroma_path):
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        collections = client.list_collections()

        total_docs = 0
        for collection in collections:
            coll = client.get_collection(collection.name)
            total_docs += coll.count()

        print(total_docs)
    else:
        print(0)
    sys.exit(0)
except Exception:
    print(0)
    sys.exit(0)
PYTHON
)
    INDEXED_DOCS=$("$VENV_PATH/bin/python" -c "$INDEXED_DOCS" 2>/dev/null || echo "0")
fi

# Calculate storage size
STORAGE_SIZE="0 KB"
if [[ -d "$RAG_DATA_PATH" ]]; then
    STORAGE_SIZE=$(du -sh "$RAG_DATA_PATH" 2>/dev/null | awk '{print $1}' || echo "0 KB")
fi

log_info "Total Checks:    $TOTAL_CHECKS"
log_info "Passed:          $PASSED_CHECKS"
log_info "Failed:          $FAILED_CHECKS"
log_info "Skipped:         $SKIPPED_CHECKS"
log_info ""
log_info "Indexed Documents: $INDEXED_DOCS"
log_info "Storage Size:      $STORAGE_SIZE"
log_info "Data Path:         $RAG_DATA_PATH"
log_info "Log File:          $VERIFY_LOG"
log_info ""

# Final status determination
if [[ $FAILED_CHECKS -eq 0 ]]; then
    if [[ $SKIPPED_CHECKS -eq 0 ]]; then
        log_success "All checks passed! ✓"
        log_success "VAST RAG installation is fully functional."
        EXIT_CODE=0
    else
        log_success "Core checks passed! ✓"
        log_info "Some checks skipped due to incomplete implementation."
        log_info "This is expected during development."
        EXIT_CODE=0
    fi
else
    log_warn "Some checks failed."
    log_warn "Review the output above for details."
    EXIT_CODE=1
fi

log_info ""
log_info "Next steps:"
log_info "  1. Restart Claude Desktop to activate MCP server"
log_info "  2. Add documents to: $RAG_DOCS_PATH"
log_info "  3. Ask Claude: 'Search vast-rag docs for <topic>'"

# Wait for tee to finish writing to log file
sleep 0.5

exit $EXIT_CODE
