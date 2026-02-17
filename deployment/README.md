# VAST RAG Deployment Scripts

Automated deployment and configuration scripts for the VAST RAG MCP server.

## Quick Start

```bash
cd ~/Development/vast-rag
./deployment/deploy.sh
```

This runs setup, install, and verify in sequence.

## Detailed Usage

### Full Deployment

```bash
cd ~/Development/vast-rag
./deployment/deploy.sh
```

This runs:
1. `setup.sh` - Validates environment, installs dependencies
2. `install.sh` - Registers MCP server in Claude Desktop
3. `verify.sh` - Runs health checks

### Individual Scripts

**Setup only:**
```bash
./deployment/setup.sh
```

**Install MCP server:**
```bash
./deployment/install.sh
```

**Dry-run install (preview changes):**
```bash
./deployment/install.sh --dry-run
```

**Verify installation:**
```bash
./deployment/verify.sh
```

**Uninstall:**
```bash
./deployment/uninstall.sh
```

**Rollback installation:**
```bash
./deployment/install.sh --rollback
```

## Directory Structure

```
deployment/
├── README.md                 # This file
├── common.sh                 # Shared utilities and configuration
├── templates/                # Configuration templates
│   ├── config.yaml.example   # RAG configuration template
│   └── mcp-entry.json        # MCP server entry template
├── deploy.sh                 # Full deployment orchestrator
├── setup.sh                  # Environment setup script
├── install.sh                # MCP server installation script
├── verify.sh                 # Health check and verification script
└── uninstall.sh              # Clean removal script
```

## Common Utilities

All scripts source `common.sh`, which provides:

- **Path variables**: `VAST_RAG_ROOT`, `VENV_PATH`, `CLAUDE_CONFIG`, `RAG_DOCS_PATH`, `RAG_DATA_PATH`
- **Logging functions**: `log_info()`, `log_success()`, `log_warn()`, `log_error()`
- **Utility functions**: `check_command()`, `backup_file()`, `get_latest_backup()`, `validate_json()`, `ensure_dir()`
- **Color-coded terminal output** (automatically disabled for non-TTY)

## Troubleshooting

### Setup fails: "Document directory not found"

Create the documents directory:
```bash
mkdir -p ~/projects/RAG/vast-data
# Add your VAST Data documentation
```

### Install fails: "jq not found"

Install Homebrew and jq:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install jq
```

### Verify fails: "Cannot import vast_rag"

This is expected if implementation is incomplete. Run verify again when the implementation session finishes.

### MCP server doesn't appear in Claude Desktop

1. Check config: `jq '.mcpServers["vast-rag"]' ~/Library/Application\ Support/Claude/claude_desktop_config.json`
2. Restart Claude Desktop completely
3. Check Developer Tools → Console for errors

## Logs

- **Verification**: `~/.claude/rag-data/logs/verify.log`
- **MCP Server**: Check Claude Desktop Developer Tools

## Configuration

### Environment Variables

Override defaults by setting environment variables before running scripts:

```bash
RAG_DOCS_PATH=~/projects/RAG
RAG_DATA_PATH=~/.claude/rag-data
```

### Advanced Configuration (config.yaml)

Copy template and customize:
```bash
cp deployment/templates/config.yaml.example config.yaml
# Edit config.yaml
```
