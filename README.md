# VAST RAG - Semantic Search for VAST Data Documentation

MCP server that provides fast, local semantic search over VAST Data technical documentation using ChromaDB and sentence-transformers.

## Features

- **Automatic Indexing**: File watcher monitors `~/projects/RAG` for new documents
- **Multi-Format Support**: PDF, Markdown, HTML, DOCX, code files
- **Semantic Search**: Find relevant content using natural language queries
- **Source Citations**: Results include page numbers and section references
- **100% Local**: No external API calls, all processing happens on your machine
- **VAST Data First**: Automatic categorization for VastDB, VAST Data Engine, InsightEngine docs

## Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd vast-rag

# 2. Run deployment
./deployment/deploy.sh

# 3. Add documents
mkdir -p ~/projects/RAG/vast-data
# Copy your VAST Data PDFs and docs

# 4. Restart Claude Desktop

# 5. Ask Claude
"Search vast-rag docs for VastDB query optimization"
```

## Documentation

- [System Design](docs/plans/2026-02-12-vast-rag-system-design.md)
- [Implementation Plan](docs/plans/2026-02-12-vast-rag-implementation.md)
- [Deployment Guide](deployment/README.md)

## Architecture

```
MCP Server (Python)
├── File Watcher (watchdog)
├── Document Parsers (PDF, MD, HTML, DOCX)
├── Semantic Chunker (500 tokens, 50 overlap)
├── Embedding Service (bge-base-en-v1.5)
└── Vector Storage (ChromaDB)
```

## Requirements

- macOS 15.2+ (tested)
- Python 3.11+
- Claude Desktop
- ~500MB disk space

## Development

See [deployment/README.md](deployment/README.md) for detailed setup instructions.

## License

[Add license information]
