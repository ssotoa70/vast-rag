"""VAST RAG MCP Server — production entry point.

This module wires up the DocumentIndexer and MCPServer as an MCP protocol
server that communicates over stdio. It's the target of:
    python -m vast_rag.server

Lifecycle:
    1. Load config from environment variables
    2. Initialize DocumentIndexer (creates ChromaDB, hash index)
    3. Start MCP stdio transport (handshake first)
    4. Index docs and start file watcher in background
    5. Serve tool calls until shutdown
    6. On shutdown, stop the watcher gracefully
"""
import asyncio
import json
import logging
import logging.handlers
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# ---------------------------------------------------------------------------
# Work around macOS 26+ xzone malloc crash during OpenMP cleanup.
# The new xzone allocator detects use-after-free in OpenMP/tokenizers
# native code during atexit, causing EXC_BREAKPOINT.  Disabling nano
# zones falls back to the legacy allocator which tolerates it.
# Also limit OpenMP threads — sentence-transformers doesn't benefit
# from parallel OMP when we already batch in Python.
# ---------------------------------------------------------------------------
os.environ.setdefault("MallocNanoZone", "0")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from vast_rag.config import get_config, Config
from vast_rag.indexer import DocumentIndexer

logger = logging.getLogger("vast_rag")


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def configure_logging(config: Config) -> None:
    """Set up structured logging with optional file rotation."""
    log_dir = config.data_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stderr so it doesn't interfere with stdio MCP)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(fmt)
    console.setLevel(logging.INFO)

    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "vast-rag.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    root = logging.getLogger("vast_rag")
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)


# ---------------------------------------------------------------------------
# MCP server definition
# ---------------------------------------------------------------------------

def create_server(config: Config) -> tuple[Server, DocumentIndexer]:
    """Create the MCP server and indexer pair.

    Returns the Server (for protocol handling) and the DocumentIndexer
    (for lifecycle management — start/stop watcher).
    """
    indexer = DocumentIndexer(config)
    app = Server(
        name="vast-rag",
        version="0.1.0",
        instructions=(
            "Semantic search over VAST Data and general technical documentation. "
            "Use search_docs to find relevant information, list_collections to see "
            "what's indexed, and get_document to retrieve specific documents."
        ),
    )

    # -- list_tools --------------------------------------------------------

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="search_docs",
                description=(
                    "Search indexed documentation using semantic similarity. "
                    "Returns the most relevant document chunks for a query."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query",
                        },
                        "category": {
                            "type": "string",
                            "enum": ["vast-data", "general-tech"],
                            "description": "Filter by document category (optional)",
                        },
                        "n_results": {
                            "type": "integer",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                            "description": "Number of results to return",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="list_collections",
                description=(
                    "List all document collections with their document counts. "
                    "Shows how many chunks are indexed in each category."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="get_document",
                description=(
                    "Retrieve metadata and content for a specific indexed document "
                    "by its source filename."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_file": {
                            "type": "string",
                            "description": "Filename of the document (e.g., 'architecture.md')",
                        },
                        "category": {
                            "type": "string",
                            "enum": ["vast-data", "general-tech"],
                            "description": "Which collection to search in",
                        },
                    },
                    "required": ["source_file", "category"],
                },
            ),
        ]

    # -- call_tool ---------------------------------------------------------

    @app.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent]:
        try:
            if name == "search_docs":
                return _handle_search(indexer, arguments)
            elif name == "list_collections":
                return _handle_list_collections(indexer)
            elif name == "get_document":
                return _handle_get_document(indexer, arguments)
            else:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error: {e}")]

    return app, indexer


# ---------------------------------------------------------------------------
# Tool handlers (sync — run in the indexer's thread)
# ---------------------------------------------------------------------------

def _handle_search(indexer: DocumentIndexer, args: dict) -> list[types.TextContent]:
    query = args["query"]
    category = args.get("category")
    n_results = args.get("n_results", 5)

    query_embedding = indexer.embedding_service.encode_text(query)
    results = indexer.vector_store.search(
        query_embedding=query_embedding,
        category=category,
        n_results=n_results,
    )

    if not results:
        return [types.TextContent(type="text", text="No results found.")]

    output = []
    for i, r in enumerate(results, 1):
        entry = (
            f"**[{i}] {r.source}** (score: {r.score:.3f}, category: {r.category})\n"
            f"{r.text}\n"
        )
        if r.page:
            entry = f"**[{i}] {r.source} p.{r.page}** (score: {r.score:.3f})\n{r.text}\n"
        output.append(entry)

    return [types.TextContent(type="text", text="\n---\n".join(output))]


def _handle_list_collections(indexer: DocumentIndexer) -> list[types.TextContent]:
    vast_count = indexer.vector_store.get_collection_count("vast-data")
    general_count = indexer.vector_store.get_collection_count("general-tech")

    data = {
        "collections": [
            {"name": "vast-data", "count": vast_count},
            {"name": "general-tech", "count": general_count},
        ],
        "total_chunks": vast_count + general_count,
    }
    return [types.TextContent(type="text", text=json.dumps(data, indent=2))]


def _handle_get_document(indexer: DocumentIndexer, args: dict) -> list[types.TextContent]:
    source_file = args["source_file"]
    category = args["category"]

    doc = indexer.vector_store.get_document_by_source(source_file, category)
    if doc is None:
        return [types.TextContent(type="text", text=f"Document '{source_file}' not found in {category}.")]

    return [types.TextContent(type="text", text=json.dumps(doc, indent=2))]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def _deferred_indexing(indexer: DocumentIndexer, config: Config) -> None:
    """Run initial indexing and start file watcher in the background.

    This runs after the MCP transport is established so the server can
    complete the protocol handshake without timing out.  The heavy work
    (model loading + embedding) is offloaded to a thread so it doesn't
    block the async event loop.
    """
    try:
        if config.docs_path.exists():
            logger.info("Running deferred document indexing...")
            loop = asyncio.get_running_loop()
            stats = await loop.run_in_executor(None, indexer.index_directory)
            logger.info(
                f"Initial indexing: {stats['indexed']} indexed, "
                f"{stats['skipped']} skipped, {stats['errors']} errors"
            )
        else:
            logger.warning(f"Docs path does not exist: {config.docs_path}")

        # Start file watcher
        try:
            indexer.start_watching()
            logger.info("File watcher started")
        except Exception as e:
            logger.warning(f"Could not start file watcher: {e}")

    except asyncio.CancelledError:
        logger.info("Deferred indexing cancelled")
    except Exception:
        logger.error("Deferred indexing failed", exc_info=True)


async def main() -> None:
    """Run the VAST RAG MCP server."""
    config = get_config()
    configure_logging(config)

    logger.info("Starting VAST RAG MCP server")
    logger.info(f"Docs path: {config.docs_path}")
    logger.info(f"Data path: {config.data_path}")

    app, indexer = create_server(config)

    # Serve over stdio — start listening FIRST so the MCP handshake
    # completes before heavy indexing work begins.
    indexing_task: asyncio.Task | None = None
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("MCP server listening on stdio")

            # Schedule indexing as a background task now that the
            # transport is ready and the handshake can proceed.
            indexing_task = asyncio.create_task(
                _deferred_indexing(indexer, config)
            )

            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    finally:
        if indexing_task and not indexing_task.done():
            indexing_task.cancel()
            try:
                await indexing_task
            except asyncio.CancelledError:
                pass
        indexer.stop_watching()
        logger.info("VAST RAG MCP server stopped")


def run() -> None:
    """Synchronous wrapper for main(), used as script entry point."""
    exit_code = 0
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception:
        logger.error("Fatal error", exc_info=True)
        exit_code = 1
    finally:
        # Use os._exit() to skip C++ atexit handlers (OpenMP, tokenizers).
        # On macOS 26+ the xzone malloc allocator detects heap corruption
        # in __kmp_internal_end_library during normal exit(), causing
        # EXC_BREAKPOINT.  Since our Python cleanup (watcher stop, log
        # flush) happens in main()'s finally block, we can safely skip
        # the C++ layer teardown.
        logging.shutdown()
        os._exit(exit_code)


if __name__ == "__main__":
    run()
