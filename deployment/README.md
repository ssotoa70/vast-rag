# VAST RAG Deployment Scripts

Automated deployment and configuration scripts for the VAST RAG MCP server.

## Quick Start

The deployment process consists of several scripts that should be run in order:

1. **`setup_environment.sh`** - Set up Python virtual environment and install dependencies
2. **`configure_mcp.sh`** - Configure Claude Desktop to use the VAST RAG MCP server
3. **`index_documentation.sh`** - Index VAST documentation for RAG retrieval
4. **`validate_deployment.sh`** - Validate the complete deployment
5. **`rollback.sh`** - Rollback to previous configuration if needed

## Prerequisites

- macOS (tested on Darwin 25.2.0)
- Python 3.11+
- Claude Desktop installed
- Git (for version control)

## Usage

### Full Deployment

Run all deployment steps in sequence:

```bash
cd deployment
./setup_environment.sh
./configure_mcp.sh
./index_documentation.sh
./validate_deployment.sh
```

### Individual Scripts

Each script can be run independently if needed:

```bash
# Set up Python environment only
./setup_environment.sh

# Reconfigure MCP settings only
./configure_mcp.sh

# Re-index documentation only
./index_documentation.sh

# Validate current deployment
./validate_deployment.sh
```

### Rollback

If something goes wrong, use the rollback script:

```bash
./rollback.sh
```

This will restore the previous Claude Desktop configuration from the most recent backup.

## Directory Structure

```
deployment/
├── README.md                 # This file
├── .gitignore               # Git ignore rules
├── common.sh                # Shared utilities and configuration
├── templates/               # Configuration templates
├── setup_environment.sh     # Environment setup script
├── configure_mcp.sh         # MCP configuration script
├── index_documentation.sh   # Documentation indexing script
├── validate_deployment.sh   # Deployment validation script
└── rollback.sh              # Configuration rollback script
```

## Common Utilities

All scripts source `common.sh`, which provides:

- **Path variables**: `VAST_RAG_ROOT`, `VENV_PATH`, `CLAUDE_CONFIG`, etc.
- **Logging functions**: `log_info()`, `log_success()`, `log_warn()`, `log_error()`
- **Utility functions**: `check_command()`, `backup_file()`, `validate_json()`, etc.
- **Color-coded terminal output** (automatically disabled for non-TTY)

## Configuration

The scripts use the following default paths:

- **Project root**: `/Users/sergio.soto/Development/vast-rag`
- **Virtual environment**: `{project_root}/.venv`
- **Claude config**: `~/.claude`
- **RAG documentation**: `{project_root}/docs`
- **RAG data**: `~/.vast-rag/data`

These can be customized by editing `common.sh`.

## Logs and Backups

- Configuration backups are created automatically with timestamps
- Backup files use the pattern: `{filename}.backup.{YYYYMMDD_HHMMSS}`
- Log files are ignored by Git (see `.gitignore`)

## Troubleshooting

If a script fails:

1. Check the error message for specific issues
2. Verify prerequisites are installed
3. Review the script's log output
4. Use `rollback.sh` to restore previous configuration
5. Re-run the failed script after fixing issues

## Development

When adding new deployment scripts:

1. Source `common.sh` at the beginning
2. Use the provided logging functions
3. Create backups before modifying files
4. Validate all changes before applying
5. Update this README with script documentation

## Support

For issues or questions:

- Check the main project README
- Review script comments for detailed behavior
- Examine log output for error details
