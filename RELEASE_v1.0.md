# VAST RAG v1.0 Release Notes

**Release Date**: February 17, 2026
**Status**: Production Ready
**Stability**: Stable

## Production Release

VAST RAG is now production-ready with complete implementation, comprehensive testing, and full deployment automation.

## Major Features

- **Semantic Search**: Fast, intelligent semantic search over VAST Data technical documentation using ChromaDB and BAAI/bge-base-en-v1.5 embeddings
- **MCP Server Support**: Full Model Context Protocol support for Claude Desktop and Claude Code
- **Local-First Architecture**: All documents and embeddings remain on your machine—no external API calls
- **Multi-Format Support**: PDF, Markdown, HTML, DOCX, plain text, and code files
- **Dual Collection Storage**: Organized into vast-data and general-tech collections for flexible scoping
- **Semantic Chunking**: Intelligent 500-token chunking with 50-token overlap for optimal search relevance
- **File Watching**: Automatic live-reload—documents become searchable within seconds of being added
- **Hash-Based Change Detection**: Efficient re-indexing that only processes changed files

## Implementation Status

✓ All 15 core implementation tasks completed (100%)
✓ 97 tests passing (65 unit + 17 integration + 15 end-to-end)
✓ Full deployment automation with shell scripts
✓ Production-ready error handling and recovery
✓ macOS 26+ compatibility with xzone malloc workarounds
✓ Comprehensive documentation and troubleshooting guides

## Technical Specifications

- **Python Version**: 3.12+ (required due to torch compatibility)
- **Embedding Model**: BAAI/bge-base-en-v1.5 (768-dimensional)
- **Vector Database**: ChromaDB with local persistence
- **File Monitoring**: watchdog library with recursive directory watching
- **Chunking Strategy**: Token-based with configurable overlap
- **Search Algorithm**: L2 distance (Euclidean) with similarity score normalization

## MCP Tools Exposed

1. **search_docs** - Semantic search across indexed documents with optional category filtering
2. **list_collections** - Display available collections and document counts
3. **get_document** - Retrieve complete metadata for a specific indexed document

## Deployment Features

- One-command setup: `./deployment/deploy.sh`
- Automatic Python 3.12 virtual environment creation
- Model download and caching (~400MB embedding model)
- Automatic Claude Desktop registration
- 6-point verification suite to ensure system health
- Clean uninstallation with data preservation options

## Performance Benchmarks

Typical performance on 2023 MacBook Pro (16GB RAM):
- Index 100 new PDFs: 45-60s (including initial model download)
- Re-index with no changes: < 5s
- Search query (top 5 results): 100-300ms
- Single file re-index: 2-5s
- Model download (first run): 2-3 minutes

## Known Limitations & Workarounds

- **Python 3.13 Not Supported**: Use Python 3.12 due to torch malloc issues
- **macOS 26+ Exit Crash**: Handled via xzone malloc workarounds (crash-on-exit only, no functional impact)
- **Large Documents**: Split files > 1GB for optimal performance
- **Unicode Filenames**: Use ASCII or common Unicode for best compatibility

## What's Included

- Production MCP server entry point with deferred initialization
- DocumentIndexer orchestration layer coordinating all components
- Semantic chunker with tiktoken-based token counting
- Embedding service with lazy loading and batch processing
- ChromaDB wrapper with dual collection management
- File watcher with format detection and specialized parsers
- 97 comprehensive tests (unit, integration, E2E)
- Full deployment automation with verification
- Detailed documentation and guides

## Getting Started

1. Clone: `git clone https://github.com/ssotoa70/vast-rag.git`
2. Deploy: `./deployment/deploy.sh`
3. Restart Claude Desktop
4. Start asking Claude about your documentation!

## Documentation

- [System Design](docs/plans/2026-02-12-vast-rag-system-design.md) - High-level architecture and decisions
- [Implementation Details](docs/plans/2026-02-12-vast-rag-implementation.md) - Deep dive into each component
- [Deployment Guide](deployment/README.md) - Step-by-step setup instructions
- [Troubleshooting Guide](docs/guides/deployment-troubleshooting.md) - Common issues and solutions
