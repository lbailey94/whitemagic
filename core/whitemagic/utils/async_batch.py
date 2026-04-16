"""Async batch processing utilities (PSR-013)."""
import asyncio
from collections.abc import Callable, Iterable
from typing import Any


async def async_batch_process(items, processor, batch_size=100, concurrency=10):
    """Process items in async batches with concurrency control."""
    items_list = list(items)
    results = []
    sem = asyncio.Semaphore(concurrency)
    async def bounded(item):
        async with sem:
            return await processor(item)
    batches = [items_list[i:i+batch_size] for i in range(0, len(items_list), batch_size)]
    for batch in batches:
        batch_results = await asyncio.gather(*[bounded(i) for i in batch], return_exceptions=True)
        results.extend(batch_results)
    return results

async def async_map(items: Iterable[Any], fn: Callable, max_concurrent: int = 50) -> list:
    """Async map with concurrency limit."""
    sem = asyncio.Semaphore(max_concurrent)
    async def bounded(item):
        async with sem:
            return await fn(item)
    return await asyncio.gather(*[bounded(i) for i in items], return_exceptions=True)
