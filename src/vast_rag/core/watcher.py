"""File watcher for automatic document detection and indexing."""
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Literal, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)


class DocumentEventHandler(FileSystemEventHandler):
    """Event handler for document file changes."""

    def __init__(
        self,
        callback: Callable[[Path, str, Literal["vast-data", "general-tech"]], None],
        debounce_seconds: float = 2.0,
        allowed_extensions: Optional[set[str]] = None,
    ):
        """Initialize event handler.

        Args:
            callback: Function called with (file_path, event_type, category)
            debounce_seconds: Seconds to wait before processing events
            allowed_extensions: Set of allowed file extensions
        """
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.allowed_extensions = allowed_extensions or {
            ".pdf",
            ".md",
            ".html",
            ".docx",
            ".txt",
            ".py",
            ".js",
            ".java",
        }

        # Debouncing state
        self._pending_events: dict[str, tuple[FileSystemEvent, float]] = {}
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory:
            self._schedule_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory:
            self._schedule_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if not event.is_directory:
            logger.info(f"File deleted: {event.src_path}")
            # Note: We could handle deletions from the vector store here
            # For now, we just log them

    def _schedule_event(self, event: FileSystemEvent) -> None:
        """Schedule event for processing after debounce period.

        Args:
            event: File system event
        """
        file_path = Path(event.src_path)

        # Check if file extension is allowed
        if file_path.suffix.lower() not in self.allowed_extensions:
            logger.debug(f"Ignoring unsupported file: {file_path}")
            return

        with self._lock:
            # Store event with timestamp
            self._pending_events[str(file_path)] = (event, time.time())

            # Cancel existing timer
            if self._debounce_timer:
                self._debounce_timer.cancel()

            # Start new timer
            self._debounce_timer = threading.Timer(
                self.debounce_seconds, self._process_pending_events
            )
            self._debounce_timer.start()

    def _process_pending_events(self) -> None:
        """Process all pending events after debounce period."""
        with self._lock:
            current_time = time.time()
            events_to_process = []

            # Find events that have passed debounce period
            for file_path, (event, timestamp) in list(self._pending_events.items()):
                if current_time - timestamp >= self.debounce_seconds:
                    events_to_process.append((Path(file_path), event))
                    del self._pending_events[file_path]

            # Clear timer
            self._debounce_timer = None

        # Process events outside lock
        for file_path, event in events_to_process:
            try:
                category = self._categorize_document(file_path)
                logger.info(
                    f"Processing {event.event_type}: {file_path} (category: {category})"
                )
                self.callback(file_path, event.event_type, category)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)

    def _categorize_document(
        self, file_path: Path
    ) -> Literal["vast-data", "general-tech"]:
        """Categorize document based on path or content.

        Args:
            file_path: Path to document

        Returns:
            Document category
        """
        # Convert to string for case-insensitive matching
        path_str = str(file_path).lower()

        # Check for VAST-related keywords in path
        vast_keywords = [
            "vast",
            "vastdata",
            "vast_data",
            "vast-data",
        ]

        for keyword in vast_keywords:
            if keyword in path_str:
                return "vast-data"

        # Default to general tech
        return "general-tech"


class FileWatcher:
    """File system watcher for automatic document indexing."""

    def __init__(
        self,
        watch_path: Path,
        callback: Callable[[Path, str, Literal["vast-data", "general-tech"]], None],
        debounce_seconds: float = 2.0,
        allowed_extensions: Optional[set[str]] = None,
    ):
        """Initialize file watcher.

        Args:
            watch_path: Directory to watch
            callback: Function called when files change
            debounce_seconds: Debounce period for file events
            allowed_extensions: Set of allowed file extensions
        """
        self.watch_path = watch_path
        self.callback = callback
        self.debounce_seconds = debounce_seconds

        # Create event handler
        self._event_handler = DocumentEventHandler(
            callback=callback,
            debounce_seconds=debounce_seconds,
            allowed_extensions=allowed_extensions,
        )

        # Create observer
        self._observer = Observer()
        self._observer.schedule(
            self._event_handler, str(watch_path), recursive=True
        )

        logger.info(f"File watcher initialized for {watch_path}")

    def start(self) -> None:
        """Start watching for file changes."""
        self._observer.start()
        logger.info(f"Started watching {self.watch_path}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        self._observer.stop()
        self._observer.join(timeout=5.0)
        logger.info(f"Stopped watching {self.watch_path}")

    def is_running(self) -> bool:
        """Check if watcher is running.

        Returns:
            True if watcher is active
        """
        return self._observer.is_alive()

    def wait(self) -> None:
        """Wait for watcher to finish (blocks until stopped)."""
        try:
            while self.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
