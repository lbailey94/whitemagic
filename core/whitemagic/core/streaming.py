"""
Streaming Response Protocol
============================

Async generators for handling large tool results efficiently.
Enables progressive loading, cancellation, and better UX.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ChunkType(Enum):
    """Types of chunks in a stream."""
    DATA = "data"
    PROGRESS = "progress"
    METADATA = "metadata"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class StreamChunk:
    """A chunk of streamed data."""
    chunk_id: int
    chunk_type: ChunkType
    data: Any
    progress: float  # 0.0 to 1.0
    is_final: bool
    timestamp: datetime
    metadata: dict[str, Any]


class StreamableToolResponse:
    """Wrapper for tool responses that can be streamed."""

    def __init__(self, tool_name: str, total_items: int | None = None):
        self.tool_name = tool_name
        self.total_items = total_items
        self.chunk_counter = 0
        self.start_time = datetime.now()
        self.cancelled = False

    async def stream_results(
        self,
        results: list,
        chunk_size: int = 10
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream results in chunks.

        Args:
            results: List of results to stream
            chunk_size: Number of items per chunk
        """
        total = len(results)

        # Send metadata chunk
        yield StreamChunk(
            chunk_id=self.chunk_counter,
            chunk_type=ChunkType.METADATA,
            data={"total_items": total, "chunk_size": chunk_size},
            progress=0.0,
            is_final=False,
            timestamp=datetime.now(),
            metadata={"tool": self.tool_name}
        )
        self.chunk_counter += 1

        # Stream data in chunks
        for i in range(0, total, chunk_size):
            if self.cancelled:
                logger.info(f"Stream cancelled for {self.tool_name}")
                break

            chunk_data = results[i:i + chunk_size]
            progress = min(1.0, (i + len(chunk_data)) / total)
            is_final = (i + chunk_size >= total)

            yield StreamChunk(
                chunk_id=self.chunk_counter,
                chunk_type=ChunkType.DATA,
                data=chunk_data,
                progress=progress,
                is_final=is_final,
                timestamp=datetime.now(),
                metadata={
                    "items_in_chunk": len(chunk_data),
                    "items_so_far": i + len(chunk_data),
                    "total_items": total,
                }
            )
            self.chunk_counter += 1

            # Small delay to allow cancellation
            await asyncio.sleep(0.001)

        # Send completion chunk
        if not self.cancelled:
            elapsed = (datetime.now() - self.start_time).total_seconds()

            yield StreamChunk(
                chunk_id=self.chunk_counter,
                chunk_type=ChunkType.COMPLETE,
                data={"status": "success", "elapsed_seconds": elapsed},
                progress=1.0,
                is_final=True,
                timestamp=datetime.now(),
                metadata={"total_chunks": self.chunk_counter}
            )

    def cancel(self):
        """Cancel the stream."""
        self.cancelled = True


async def stream_search_results(query: str, results: list, chunk_size: int = 10) -> AsyncGenerator[StreamChunk, None]:
    """
    Stream search results progressively.

    Example usage:
        async for chunk in stream_search_results("test query", results):
            if chunk.chunk_type == ChunkType.DATA:
                process_data(chunk.data)
            elif chunk.chunk_type == ChunkType.PROGRESS:
                update_progress_bar(chunk.progress)
    """
    streamer = StreamableToolResponse("search_memories", len(results))
    async for chunk in streamer.stream_results(results, chunk_size):
        yield chunk


async def stream_large_memory(memory_id: str, content: str, chunk_size: int = 1000) -> AsyncGenerator[StreamChunk, None]:
    """
    Stream large memory content in chunks.

    Useful for very large memories (>100KB) to avoid loading everything at once.
    """
    StreamableToolResponse("read_memory", len(content))

    # Send metadata
    yield StreamChunk(
        chunk_id=0,
        chunk_type=ChunkType.METADATA,
        data={"memory_id": memory_id, "total_size": len(content)},
        progress=0.0,
        is_final=False,
        timestamp=datetime.now(),
        metadata={"content_type": "text"}
    )

    # Stream content in chunks
    chunk_id = 1
    for i in range(0, len(content), chunk_size):
        chunk_text = content[i:i + chunk_size]
        progress = min(1.0, (i + len(chunk_text)) / len(content))
        is_final = (i + chunk_size >= len(content))

        yield StreamChunk(
            chunk_id=chunk_id,
            chunk_type=ChunkType.DATA,
            data=chunk_text,
            progress=progress,
            is_final=is_final,
            timestamp=datetime.now(),
            metadata={
                "char_offset": i,
                "chunk_length": len(chunk_text),
            }
        )
        chunk_id += 1

        await asyncio.sleep(0.001)

    # Completion
    yield StreamChunk(
        chunk_id=chunk_id,
        chunk_type=ChunkType.COMPLETE,
        data={"status": "success"},
        progress=1.0,
        is_final=True,
        timestamp=datetime.now(),
        metadata={}
    )


async def stream_tool_call(tool_name: str, **kwargs) -> AsyncGenerator[StreamChunk, None]:
    """
    Generic streaming wrapper for any tool call.

    Automatically detects if result is large and streams it.
    """
    streamer = StreamableToolResponse(tool_name)

    try:
        # Send start notification
        yield StreamChunk(
            chunk_id=0,
            chunk_type=ChunkType.PROGRESS,
            data={"status": "starting"},
            progress=0.0,
            is_final=False,
            timestamp=datetime.now(),
            metadata={"tool": tool_name, "args": kwargs}
        )

        # Execute tool (would call actual tool here)
        # For now, simulate
        await asyncio.sleep(0.1)
        result = {"status": "simulated", "tool": tool_name}

        # Stream result
        if isinstance(result, list) and len(result) > 10:
            # Large list - stream it
            async for chunk in streamer.stream_results(result):
                yield chunk
        else:
            # Small result - send as single chunk
            yield StreamChunk(
                chunk_id=1,
                chunk_type=ChunkType.DATA,
                data=result,
                progress=1.0,
                is_final=True,
                timestamp=datetime.now(),
                metadata={}
            )

    except Exception as e:
        # Error chunk
        yield StreamChunk(
            chunk_id=streamer.chunk_counter,
            chunk_type=ChunkType.ERROR,
            data={"error": str(e)},
            progress=0.0,
            is_final=True,
            timestamp=datetime.now(),
            metadata={"error_type": type(e).__name__}
        )


# Example integration with existing tools
class StreamingToolAdapter:
    """Adapter to make existing tools streamable."""

    @staticmethod
    async def search_memories_stream(query: str, limit: int = 100, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """Stream search_memories results."""
        # In production, this would call the actual search_memories tool
        # For now, simulate
        results = [{"id": f"mem_{i}", "title": f"Memory {i}"} for i in range(limit)]

        async for chunk in stream_search_results(query, results, chunk_size=10):
            yield chunk

    @staticmethod
    async def list_memories_stream(limit: int = 1000, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """Stream list_memories results."""
        # Simulate large list
        results = [{"id": f"mem_{i}"} for i in range(limit)]

        streamer = StreamableToolResponse("list_memories", len(results))
        async for chunk in streamer.stream_results(results, chunk_size=50):
            yield chunk

    @staticmethod
    async def graph_walk_stream(start_id: str, depth: int = 3, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """Stream graph walk results as they're discovered."""
        StreamableToolResponse("graph_walk")

        # Send start
        yield StreamChunk(
            chunk_id=0,
            chunk_type=ChunkType.PROGRESS,
            data={"status": "starting", "start_id": start_id},
            progress=0.0,
            is_final=False,
            timestamp=datetime.now(),
            metadata={"depth": depth}
        )

        # Simulate progressive discovery
        visited = []
        for level in range(depth):
            # Discover nodes at this level
            new_nodes = [f"node_{level}_{i}" for i in range(5)]
            visited.extend(new_nodes)

            progress = (level + 1) / depth

            yield StreamChunk(
                chunk_id=level + 1,
                chunk_type=ChunkType.DATA,
                data={"level": level, "nodes": new_nodes},
                progress=progress,
                is_final=(level == depth - 1),
                timestamp=datetime.now(),
                metadata={"total_visited": len(visited)}
            )

            await asyncio.sleep(0.05)

        # Complete
        yield StreamChunk(
            chunk_id=depth + 1,
            chunk_type=ChunkType.COMPLETE,
            data={"total_nodes": len(visited)},
            progress=1.0,
            is_final=True,
            timestamp=datetime.now(),
            metadata={}
        )


# Utility functions
def chunk_to_dict(chunk: StreamChunk) -> dict[str, Any]:
    """Convert StreamChunk to dictionary for JSON serialization."""
    return {
        "chunk_id": chunk.chunk_id,
        "chunk_type": chunk.chunk_type.value,
        "data": chunk.data,
        "progress": chunk.progress,
        "is_final": chunk.is_final,
        "timestamp": chunk.timestamp.isoformat(),
        "metadata": chunk.metadata,
    }


async def collect_stream(stream: AsyncGenerator[StreamChunk, None]) -> list:
    """Collect all chunks from a stream (for testing)."""
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return chunks
