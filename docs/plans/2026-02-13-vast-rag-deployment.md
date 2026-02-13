# VAST RAG Deployment Automation Design

**Date:** 2026-02-13
**Status:** Approved
**Author:** Claude Code with Sergio Soto

## Executive Summary

Deployment automation for the VAST RAG MCP server using a modular multi-script architecture. Supports both development iteration (while implementation is ongoing) and production deployment. Provides environment validation, MCP registration, health checks, and clean uninstallation with comprehensive error handling and rollback mechanisms.

## Context

The VAST RAG system is an MCP server that provides semantic search over VAST Data documentation. Implementation is currently 40% complete in a parallel session. This deployment automation must:

1. Work during active development (reusable scripts for verification)
2. Support production deployment when implementation completes
3. Handle both global Claude Desktop configuration and project-local examples
4. Preserve artifacts on failure for debugging
5. Provide granular control and one-command convenience

## Architecture Overview

### Modular Multi-Script Design

```
vast-rag/deployment/
├── common.sh         # Shared variables and utility functions
├── setup.sh          # Environment validation, venv check, dependency installation
├── install.sh        # MCP server registration in Claude Desktop config
├── verify.sh         # Health checks and smoke tests
├── uninstall.sh      # Clean removal with config backup restoration
├── deploy.sh         # Thin orchestrator (runs setup → install → verify)
└── templates/
    ├── .env.template           # Environment variable template
    ├── .mcp.json.example       # Project-specific MCP config example
    └── config.yaml.example     # Advanced configuration template
```

### Design Principles

1. **Idempotency**: All scripts can be run multiple times safely
2. **Explicit Contracts**: Each script documents preconditions/postconditions
3. **Fail-Fast**: Clear error messages with actionable next steps
4. **Artifact Preservation**: On failure, leaves everything in place for debugging
5. **Dual Configuration**: Registers in global Claude Desktop config + provides project-local example

### Execution Modes

- **Development**: Run individual scripts (`./verify.sh` after code changes)
- **Production**: Single command deployment (`./deploy.sh`)
- **CI/CD**: Compose scripts for staged deployments

## Script Components

### common.sh - Shared Configuration & Utilities

**Purpose**: Centralize paths, colors, and reusable functions to avoid duplication.

**Exports:**
```bash
# Paths
VAST_RAG_ROOT          # Project root directory
VENV_PATH              # .venv location
CLAUDE_CONFIG          # ~/Library/Application Support/Claude/claude_desktop_config.json
RAG_DOCS_PATH          # ~/projects/RAG (user's document directory)
RAG_DATA_PATH          # ~/.claude/rag-data (storage directory)

# Functions
log_info()             # Blue info messages
log_success()          # Green success messages
log_error()            # Red error messages with exit
check_command()        # Verify command exists (python3, jq)
backup_file()          # Create timestamped backup before modification
```

### setup.sh - Environment Preparation

**Preconditions**: None (first script to run)

**Actions:**
1. Validate `~/projects/RAG` exists (fail with setup instructions if missing)
2. Check Python 3.11+ installed
3. Detect existing `.venv` or create new one
4. Install/upgrade dependencies from `pyproject.toml`
5. Download sentence-transformers model to cache (one-time ~133MB)
6. Create `~/.claude/rag-data/` storage structure
7. Generate `.env` file from template if missing

**Postconditions**: Environment ready for MCP server execution

**Performance**: <3 minutes first run, <30 seconds cached

### install.sh - MCP Server Registration

**Preconditions**: `.venv` exists with dependencies installed

**Actions:**
1. Backup existing Claude Desktop config (timestamped)
2. Read current config using `jq` (install if missing)
3. Add `vast-rag` entry to `mcpServers` section
4. Generate `.mcp.json.example` in project root
5. Validate JSON syntax before writing

**Postconditions**: `vast-rag` registered in global MCP config

**MCP Configuration Template:**
```json
{
  "mcpServers": {
    "vast-rag": {
      "command": "/Users/sergio.soto/Development/vast-rag/.venv/bin/python",
      "args": ["-m", "vast_rag.server"],
      "env": {
        "RAG_DOCS_PATH": "/Users/sergio.soto/projects/RAG",
        "RAG_DATA_PATH": "/Users/sergio.soto/.claude/rag-data"
      }
    }
  }
}
```

**Performance**: <5 seconds

### verify.sh - Health Checks

**Preconditions**: MCP server registered in config

**Actions:**
1. Check MCP server entry exists in config
2. Verify Python can import `vast_rag` module
3. Test embedding model loads successfully
4. Validate ChromaDB can initialize collections
5. Run smoke test: index sample document, query it
6. Check file watcher can start (doesn't actually watch, just validates)
7. Report system status (doc count, storage size)

**Postconditions**: MCP server verified functional

**Performance**: <20 seconds (includes test indexing)

### uninstall.sh - Clean Removal

**Preconditions**: None (safe to run anytime)

**Actions:**
1. Remove `vast-rag` entry from Claude Desktop config
2. Restore most recent config backup if desired (interactive prompt)
3. Optionally remove `~/.claude/rag-data/` (interactive prompt with warning)
4. Optionally remove `.venv` (interactive prompt)
5. Keep source code and deployment scripts intact

**Safety**: Never removes source documents from `~/projects/RAG/`

**Interactive Prompts:**
- "Remove vast-rag from Claude Desktop? [y/N]"
- "Delete ~/.claude/rag-data/? WARNING: All indexed docs will be lost [y/N]"
- "Remove .venv/? (Can rebuild with setup.sh) [y/N]"

### deploy.sh - Orchestrator

**Purpose**: Convenience wrapper for full deployment

**Implementation** (~30 lines):
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

log_info "Starting VAST RAG deployment..."

"$SCRIPT_DIR/setup.sh"    || exit 1
"$SCRIPT_DIR/install.sh"  || exit 1
"$SCRIPT_DIR/verify.sh"   || exit 1

log_success "Deployment complete! Restart Claude Desktop to activate MCP server."
```

**Performance**: <4 minutes first-time full deployment

## Data Flow

### Happy Path: Full Deployment (`./deploy.sh`)

```
┌─────────────┐
│  User runs  │
│ ./deploy.sh │
└──────┬──────┘
       │
       ├──► setup.sh
       │     ├─ Check Python 3.11+ exists
       │     ├─ Validate ~/projects/RAG/ exists
       │     │  └─ FAIL → "Create ~/projects/RAG and add docs"
       │     ├─ Detect .venv (exists from implementation session)
       │     ├─ Activate .venv
       │     ├─ pip install -e ".[dev]" (upgrade if needed)
       │     ├─ Download bge-base-en-v1.5 to ~/.cache/
       │     ├─ Create ~/.claude/rag-data/{chroma,logs,cache,index}
       │     └─ Generate .env from template
       │
       ├──► install.sh
       │     ├─ Backup Claude Desktop config
       │     │  → ~/Library/Application Support/Claude/claude_desktop_config.json.backup.20260213-143022
       │     ├─ Read config with jq
       │     ├─ Check if "vast-rag" already exists
       │     │  └─ EXISTS → Update entry (overwrite)
       │     │  └─ MISSING → Add new entry
       │     ├─ Write updated config atomically (tmp file + mv)
       │     ├─ Validate JSON syntax
       │     └─ Generate .mcp.json.example in project root
       │
       └──► verify.sh
             ├─ Import vast_rag module (Python test)
             ├─ Load embedding model (one chunk)
             ├─ Initialize ChromaDB collections
             ├─ Index test document (in-memory)
             ├─ Query test document (verify retrieval)
             ├─ Report status:
             │   ✓ MCP server: registered
             │   ✓ Embeddings: functional
             │   ✓ ChromaDB: 2 collections ready
             │   ✓ Storage: ~/.claude/rag-data (0 docs indexed)
             └─ SUCCESS → "Restart Claude Desktop to activate"
```

### Development Iteration Flow

During active development (implementation session ongoing):

```
Developer modifies parser code
  ↓
./deployment/verify.sh
  ├─ Re-imports vast_rag module (picks up changes)
  ├─ Runs smoke tests
  └─ PASS/FAIL → immediate feedback

No need to re-run setup.sh or install.sh
```

### Configuration Flow

Template → User Customization → Active Config

```
.env.template              User edits              .env (gitignored)
─────────────────────────────────────────►
RAG_DOCS_PATH=...                                  RAG_DOCS_PATH=/Users/sergio.soto/projects/RAG
RAG_DATA_PATH=...                                  RAG_CHUNK_SIZE=750
RAG_CHUNK_SIZE=500                                 RAG_EMBEDDING_MODEL=custom-model

                                                   ↓

config.yaml.example       User edits              config.yaml (optional)
─────────────────────────────────────────►
(Advanced settings)                                (Custom chunking strategies)
```

### Failure Recovery Flow

```
./deploy.sh runs
  ↓
verify.sh FAILS (ChromaDB import error)
  ↓
Deployment STOPS (set -e)
  ├─ No automatic rollback
  ├─ Config backup preserved
  ├─ Logs written to ~/.claude/rag-data/logs/deployment.log
  └─ Error message:
      "ERROR: ChromaDB initialization failed
       Check logs: ~/.claude/rag-data/logs/deployment.log
       To rollback: ./deployment/install.sh --rollback"

User investigates
  ↓
Fixes issue (installs missing dependency)
  ↓
Re-runs ./deployment/verify.sh
  ↓
SUCCESS → Continue where left off
```

## Error Handling & Recovery

### Error Categories & Responses

#### 1. Environment Errors (setup.sh)

| Error | Detection | Response |
|-------|-----------|----------|
| Python < 3.11 | `python3 --version` | FAIL: "Install Python 3.11+ from python.org" |
| `~/projects/RAG/` missing | `[ -d "$RAG_DOCS_PATH" ]` | FAIL: "Create ~/projects/RAG and add VAST Data docs" |
| Insufficient disk space | `df -h ~/.claude` | WARN: "Low disk space (<1GB), indexing may fail" |
| pip install failure | Exit code from pip | FAIL: "Dependency installation failed. Check network/permissions" |
| Model download failure | `sentence-transformers` import | FAIL: "Download failed. Check internet connection or use offline model" |

#### 2. Configuration Errors (install.sh)

| Error | Detection | Response |
|-------|-----------|----------|
| Claude Desktop config missing | `[ ! -f "$CLAUDE_CONFIG" ]` | FAIL: "Claude Desktop not installed or config not found" |
| `jq` not installed | `command -v jq` | AUTO-FIX: "Installing jq via homebrew..." |
| Config JSON malformed | `jq . "$CLAUDE_CONFIG"` | FAIL: "Config is corrupted. Restore backup from: [path]" |
| Write permission denied | Write test to config dir | FAIL: "No write permission. Run: chmod u+w [config]" |
| Backup creation fails | Disk full or permissions | WARN: "Proceeding without backup (risky)" |

#### 3. Verification Errors (verify.sh)

| Error | Detection | Response |
|-------|-----------|----------|
| Module import fails | `python -c "import vast_rag"` | FAIL: "Installation incomplete. Re-run setup.sh" |
| Embedding model missing | Model load test | FAIL: "Model not cached. Re-run setup.sh to download" |
| ChromaDB init fails | Collection creation | FAIL: "ChromaDB error. Check logs: [log_path]" |
| Test indexing fails | Document parse/chunk/embed | FAIL: "Pipeline broken. Check implementation" |
| File watcher can't start | Watchdog init | FAIL: "Watchdog error. Check docs path permissions" |

### Rollback Mechanisms

#### install.sh --rollback

Restores system to pre-installation state:
```bash
# Restore Claude Desktop config from most recent backup
cp "$CLAUDE_CONFIG.backup.LATEST" "$CLAUDE_CONFIG"

# Remove .mcp.json.example
rm -f "$PROJECT_ROOT/.mcp.json.example"

# Log rollback
echo "Rolled back to backup: $BACKUP_FILE"
```

### Logging Strategy

**Log Locations:**
- `~/.claude/rag-data/logs/deployment.log` - All deployment script output
- `~/.claude/rag-data/logs/verify.log` - Detailed verification results
- `/tmp/vast-rag-install.log` - Installation temporary log (deleted on success)

**Log Format:**
```
[2026-02-13 14:30:22] [INFO] Starting setup.sh
[2026-02-13 14:30:23] [INFO] Python version: 3.11.7 ✓
[2026-02-13 14:30:24] [ERROR] ~/projects/RAG not found
[2026-02-13 14:30:24] [ERROR] Setup failed. See details above.
```

**Log Retention:**
- Keep last 10 deployment logs (rotate automatically)
- Verification logs kept for 7 days
- Error logs never auto-deleted

### Safety Guardrails

1. **Atomic Config Updates**: Write to temp file, validate, then `mv` (prevents corruption)
2. **Automatic Backups**: Config backed up before every `install.sh` run
3. **Dry-Run Mode**: `./install.sh --dry-run` shows changes without applying
4. **Validation Gates**: JSON syntax check before writing config
5. **Explicit Confirmations**: Destructive operations (`uninstall.sh` data deletion) require `y` confirmation

### Recovery Documentation

Each script failure includes recovery instructions:

```bash
# Example error message from verify.sh
ERROR: ChromaDB initialization failed

Diagnosis:
  - ChromaDB may not be installed correctly
  - Storage directory may be corrupted

Recovery Options:
  1. Re-run setup: ./deployment/setup.sh
  2. Check logs: cat ~/.claude/rag-data/logs/verify.log
  3. Remove storage: rm -rf ~/.claude/rag-data && ./deployment/setup.sh
  4. Report issue: https://github.com/your-repo/issues

To rollback installation:
  ./deployment/install.sh --rollback
```

## Testing & Verification Strategy

### Manual Testing Checklist

Before considering deployment automation complete, verify:

**Setup Script (`./deployment/setup.sh`)**
- [ ] Fresh clone: No `.venv` exists → creates new venv
- [ ] Existing venv: `.venv` exists → reuses and upgrades dependencies
- [ ] Missing docs path: `~/projects/RAG` doesn't exist → fails with clear message
- [ ] Offline mode: No internet → fails gracefully on model download
- [ ] Low disk space: <500MB free → warns but continues
- [ ] Model already cached: Re-run doesn't re-download (fast)

**Install Script (`./deployment/install.sh`)**
- [ ] First install: Adds `vast-rag` entry to config cleanly
- [ ] Re-install: Updates existing entry without duplicates
- [ ] Config backup: Creates timestamped backup before changes
- [ ] Invalid JSON: Corrupted config → detects and aborts safely
- [ ] Dry-run mode: `--dry-run` shows diff without applying
- [ ] Rollback: `--rollback` restores previous config

**Verify Script (`./deployment/verify.sh`)**
- [ ] Fresh install: All checks pass on first run
- [ ] Smoke test: Indexes sample doc, retrieves it successfully
- [ ] Module changes: Detects updated code from implementation session
- [ ] ChromaDB missing: Fails gracefully with actionable error
- [ ] Model missing: Detects and suggests re-running setup
- [ ] Status report: Shows doc count, storage size, collection status

**Uninstall Script (`./deployment/uninstall.sh`)**
- [ ] MCP removal: Removes entry, validates JSON after
- [ ] Interactive prompts: Each step asks for confirmation
- [ ] Selective removal: Can remove config but keep data
- [ ] Complete removal: Removes everything when all prompts answered `y`
- [ ] Source preservation: Never touches source code or `~/projects/RAG`

**Orchestrator (`./deployment/deploy.sh`)**
- [ ] Fresh system: Full deployment succeeds end-to-end
- [ ] Partial failure: Stops at failed script, preserves state
- [ ] Idempotency: Re-running after success is safe

### Integration Checklist

After deployment completes, verify MCP server integration:

**In Claude Desktop:**
- [ ] Restart Claude Desktop
- [ ] Open Developer Tools → Console
- [ ] Check for "MCP server vast-rag connected" message
- [ ] No error messages in console
- [ ] Ask Claude: "Search vast-rag docs for VastDB" → receives results

**Smoke Test Workflow:**
```bash
# 1. Add test document to watched directory
echo "# VastDB Test\n\nVastDB is a database." > ~/projects/RAG/vast-data/test.md

# 2. Wait 5 seconds (debounce + indexing)
sleep 5

# 3. Verify in Claude Desktop
# Ask: "What is VastDB according to the indexed docs?"
# Expected: Claude quotes the test document with citation
```

### Rollback Testing

Verify recovery mechanisms work:

- [ ] Install, then rollback → config restored exactly
- [ ] Partial uninstall → only selected items removed
- [ ] Config corruption recovery → backup restoration works
- [ ] Failed verify → can re-run after fixing issue

### Performance Benchmarks

Target timing for deployment scripts:

| Script | Target Time | Notes |
|--------|-------------|-------|
| `setup.sh` (first run) | <3 minutes | Includes model download (~133MB) |
| `setup.sh` (cached) | <30 seconds | Model already downloaded |
| `install.sh` | <5 seconds | JSON manipulation only |
| `verify.sh` | <20 seconds | Includes test indexing |
| `deploy.sh` (full) | <4 minutes | First-time full deployment |

## Configuration Templates

### .env.template

```bash
# VAST RAG Configuration
# Copy to .env and customize

# Document source directory (must exist before deployment)
RAG_DOCS_PATH=/Users/sergio.soto/projects/RAG

# Storage directory (created automatically)
RAG_DATA_PATH=/Users/sergio.soto/.claude/rag-data

# Chunking configuration
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=50

# Embedding model
RAG_EMBEDDING_MODEL=BAAI/bge-base-en-v1.5

# Batch processing
RAG_BATCH_SIZE=32

# File watching
RAG_DEBOUNCE_SECONDS=2.0
```

### .mcp.json.example

```json
{
  "mcpServers": {
    "vast-rag": {
      "command": "/Users/sergio.soto/Development/vast-rag/.venv/bin/python",
      "args": ["-m", "vast_rag.server"],
      "env": {
        "RAG_DOCS_PATH": "/Users/sergio.soto/projects/RAG",
        "RAG_DATA_PATH": "/Users/sergio.soto/.claude/rag-data"
      }
    }
  }
}
```

### config.yaml.example

```yaml
# Advanced VAST RAG Configuration
# Copy to config.yaml for custom settings

chunking:
  strategy: semantic  # semantic, fixed, or adaptive
  size: 500
  overlap: 50
  preserve_code_blocks: true

embedding:
  model: BAAI/bge-base-en-v1.5
  dimension: 768
  batch_size: 32
  device: mps  # mps (Mac), cuda, or cpu

storage:
  chroma_path: ~/.claude/rag-data/chroma
  cache_size: 50  # LRU cache for parsed documents
  query_cache_ttl: 300  # seconds

file_watcher:
  debounce: 2.0  # seconds
  extensions:
    - .pdf
    - .md
    - .html
    - .docx
    - .txt
    - .py
    - .js
    - .java
```

## Success Criteria

The deployment automation will be considered successful when:

1. **Development Support**: Developers can run `verify.sh` after code changes and get immediate feedback
2. **Production Ready**: `./deploy.sh` completes full deployment in <4 minutes on fresh system
3. **Error Clarity**: Every failure includes actionable recovery instructions
4. **Idempotency**: All scripts can be re-run safely without side effects
5. **Recovery**: Rollback mechanisms restore system to pre-deployment state
6. **Integration**: Claude Desktop successfully connects to MCP server after deployment
7. **Documentation**: README provides clear usage examples and troubleshooting

## Future Enhancements (Out of Scope)

- Container-based deployment (Docker image)
- Automated testing with `bats` (Bash Automated Testing System)
- CI/CD pipeline integration (GitHub Actions)
- Multi-platform support (Linux, Windows WSL)
- Monitoring dashboard for indexed documents
- Automatic updates mechanism
- Health monitoring endpoint

## References

- VAST RAG System Design: `/Users/sergio.soto/Development/docs/plans/2026-02-12-vast-rag-system-design.md`
- VAST RAG Implementation Plan: `/Users/sergio.soto/Development/docs/plans/2026-02-12-vast-rag-implementation.md`
- Model Context Protocol: https://spec.modelcontextprotocol.io
- Architecture Authority Assessment: Agent ID aca7b19
