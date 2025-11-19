"""Automated wisdom text ingestion from sacred-texts.com."""

import asyncio
from dataclasses import dataclass
from typing import List, Optional
import aiohttp
from whitemagic.core import MemoryManager


@dataclass
class WisdomText:
    name: str
    base_url: str
    tags: List[str]


TEXTS = [
    WisdomText("Dao De Jing", "https://sacred-texts.com/tao/taote.htm", ["daoism"]),
    WisdomText("I Ching", "https://sacred-texts.com/ich/index.htm", ["iching"]),
    WisdomText("Art of War", "https://sacred-texts.com/tao/aow/index.htm", ["strategy"]),
    WisdomText("Yang Chu", "https://sacred-texts.com/tao/ycgp/index.htm", ["yang-chu"]),
    WisdomText("Tai Shang", "https://sacred-texts.com/tao/ts/index.htm", ["morality"]),
    WisdomText("Yin Classic", "https://sacred-texts.com/tao/ycc/index.htm", ["yin"]),
    WisdomText("Zhuangzi", "https://sacred-texts.com/tao/mcm/index.htm", ["zhuangzi"]),
    WisdomText("Teachings", "https://sacred-texts.com/tao/tt/index.htm", ["teachings"]),
    WisdomText("SBE 39", "https://sacred-texts.com/tao/sbe39/index.htm", ["translation"]),
]


async def ingest_all():
    """Ingest all 9 wisdom texts."""
    memory = MemoryManager()
    stats = {"success": 0, "failed": 0}
    
    async with aiohttp.ClientSession() as session:
        for text in TEXTS:
            try:
                await asyncio.sleep(2)  # Rate limit
                async with session.get(text.base_url, timeout=30) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        memory.create_memory(
                            title=f"Wisdom: {text.name}",
                            content=content[:8000],
                            memory_type="long_term",
                            tags=text.tags + ["wisdom", "v2.3.5"]
                        )
                        stats["success"] += 1
                        print(f"✓ {text.name}")
                    else:
                        stats["failed"] += 1
            except Exception as e:
                print(f"✗ {text.name}: {e}")
                stats["failed"] += 1
    
    return stats
