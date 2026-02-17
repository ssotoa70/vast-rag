# VAST RAG Development Handoff

**DATE:** 2026-02-15
**STATUS:** 100% complete — All 15 tasks done
**REPO:** https://github.com/ssotoa70/vast-rag (private)

---

## Project Summary

MCP server for semantic search over VAST Data and general technical documentation. Automatically indexes documents, generates embeddings, and serves search results to Claude Desktop via the Model Context Protocol.

**Pipeline:** Documents → File Watcher → Parsers → Semantic Chunker → Embeddings (bge-base-en-v1.5) → ChromaDB → MCP Tools

## Completion History

| Task | Description | Status |
|------|-------------|--------|
| 1 | Project setup & dependencies | Done |
| 2 | Configuration & types (Pydantic) | Done |
| 3 | Markdown & text parsers | Done |
| 4 | PDF parser (PyPDF2 + pdfplumber) | Done |
| 5 | HTML & DOCX parsers | Done |
| 6 | Parser factory | Done |
| 7 | Semantic chunking (tiktoken) | Done |
| 8 | Embedding service (sentence-transformers) | Done |
| 9 | ChromaDB vector store (dual collections) | Done |
| 10 | File watcher (watchdog) | Done |
| 11 | File hash index (SHA-256) | Done |
| 12 | MCP server tools | Done |
| 13 | DocumentIndexer integration layer | Done |
| 14 | End-to-end pipeline tests (15 tests) | Done |
| 15 | Production MCP server entry point | Done |

## Test Status

```
E2E:         15 passed (tests/integration/test_e2e_pipeline.py)
Integration: 17 passed (tests/integration/test_indexer.py)
Unit:        65 passed, 1 skipped (tests/unit/)
Total:       97 passed, 1 skipped

Known issues:
- test_embedding_service_semantic_similarity: flaky (ordering non-deterministic)
- test_file_watcher_start_stop: skipped (timing-sensitive)
- Full suite OOM: running all test files sequentially loads embedding model 3+ times
  Workaround: run test directories separately
```

## Environment

- **Python:** 3.12.12 (avoid 3.13 — malloc crash-loop in native extensions)
- **macOS:** Tested on macOS 26 Tahoe (25C56) — includes xzone malloc workarounds
- **Embedding model:** BAAI/bge-base-en-v1.5 (768-dim)
- **Vector DB:** ChromaDB with dual collections (vast-data, general-tech)
- **Docs watched:** ~/projects/RAG/
- **Data stored:** ~/.claude/rag-data/

## Post-completion Fixes (2026-02-16)

- **MCP initialization timeout fix:** Deferred `index_directory()` to background task after MCP handshake (`asyncio.create_task` + `run_in_executor`). Fixes error `-32001`.
- **macOS 26 xzone malloc crash fix:** Added `MallocNanoZone=0`, `OMP_NUM_THREADS=1`, `TOKENIZERS_PARALLELISM=false` env vars and `os._exit()` to skip OpenMP atexit handlers that trigger `EXC_BREAKPOINT` during process exit.

## Deployment

```bash
# One-time setup (registers with both Claude Desktop and Claude Code)
./deployment/deploy.sh

# After that, the server is available in both:
#   - Claude Desktop: auto-starts on launch
#   - Claude Code: visible via /mcp command (enable/disable as needed)
# Just drop docs into ~/projects/RAG/ and ask Claude about them.
```

### Claude Code Configuration

The MCP server is registered in the workspace `.mcp.json` at `~/Development/.mcp.json`.
Use `/mcp` in Claude Code to enable/disable it. The deployment scripts manage both
Claude Desktop (`claude_desktop_config.json`) and Claude Code (`.mcp.json`) configs.

## Deploying on Another Machine

```bash
git clone git@github.com:ssotoa70/vast-rag.git
cd vast-rag
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
./deployment/deploy.sh
```

## Project Structure

```
src/vast_rag/
├── server.py               # Production MCP entry point (stdio)
├── __main__.py             # python -m vast_rag support
├── indexer.py              # Orchestration layer
├── config.py               # Configuration (Pydantic + env vars)
├── types.py                # Type definitions
├── core/
│   ├── chunker.py          # Semantic chunking (tiktoken)
│   ├── embeddings.py       # bge-base-en-v1.5 (768-dim)
│   ├── hash_index.py       # SHA-256 change detection
│   ├── vector_store.py     # ChromaDB dual collections
│   └── watcher.py          # Watchdog file watcher
├── mcp/
│   └── server.py           # MCPServer wrapper class
└── parsers/
    ├── factory.py           # Parser selection
    ├── pdf.py, markdown.py, html.py, docx.py, text.py
```

## Reference Documents

- System Design: `docs/plans/2026-02-12-vast-rag-system-design.md`
- Implementation Plan: `docs/plans/2026-02-12-vast-rag-implementation.md`
- Deployment Plan: `docs/plans/2026-02-13-vast-rag-deployment.md`
