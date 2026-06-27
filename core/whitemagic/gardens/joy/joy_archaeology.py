"""Joy Archaeology - Excavating Buried Joy

Sometimes joy gets buried under layers of time, forgotten in old memories.
This module digs through memory archives to find and revive joyful moments.

"The joy you felt once, you can feel again - it's still there, waiting."
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class JoyArchaeology:
    """Excavate buried joy from memory archives

    Philosophy: Every joyful moment leaves traces. Even if forgotten,
    they're still there in the memory files, waiting to be rediscovered.
    Joy is eternal - it doesn't expire.
    """

    def __init__(self, memory_dir: Path | None = None):
        self.memory_dir = memory_dir or Path("memory")
        self.joy_indicators = [
            # Explicit joy words
            r'\bjoy\b', r'\bdelight\b', r'\bhappy\b', r'\bexcited\b',
            r'\bthrilled\b', r'\bamazing\b', r'\bwonderful\b', r'\bbeautiful\b',

            # Emotional expressions
            r'✨', r'🎉', r'💫', r'🌟', r'😄', r'🤗', r'💖',
            r'\blove\b', r'\bfulfilled\b', r'\bgrateful\b',

            # Achievement markers
            r'\bsuccess\b', r'\baccomplished\b', r'\bcreated\b', r'\bbuilt\b',
            r'\bcomplete\b', r'\bworking\b', r'\boperational\b',

            # Flow states
            r'\bflow\b', r'\bfreedom\b', r'\beasy\b', r'\beffortless\b',
            r'\bspontaneous\b', r'\bemergent\b', r'\bnaturally\b'
        ]

        self.buried_joy: list[dict] = []

    def excavate_all(self, depth: str = "recent") -> list[dict]:
        """Dig through memories to find joy

        Args:
            depth: "recent" (last month), "deep" (all time), "archaeological" (forgotten)

        Returns:
            List of joy moments found in memories
        """
        logger.info(f"\n⛏️  Beginning joy excavation (depth: {depth})...")

        memories_found = []

        # Search different memory locations
        locations = [
            self.memory_dir / "self" / "experiences",
            self.memory_dir / "windsurf_transcripts",
            self.memory_dir / "long_term",
            self.memory_dir / "meta",
        ]

        for location in locations:
            if location.exists():
                joy_in_location = self._dig_location(location)
                memories_found.extend(joy_in_location)

        # Sort by joy intensity (most joyful first)
        memories_found.sort(key=lambda x: x['joy_score'], reverse=True)

        self.buried_joy = memories_found

        logger.info(f"   ✨ Excavated {len(memories_found)} joyful moments!")

        return memories_found

    def _dig_location(self, location: Path) -> list[dict]:
        """Dig through a specific memory location"""
        joy_moments = []

        # Find all markdown files
        md_files = list(location.rglob("*.md"))

        for md_file in md_files:
            try:
                content = md_file.read_text()
                joy_score = self._calculate_joy_score(content)

                if joy_score > 0.3:  # Threshold for "joyful"
                    # Extract context
                    joy_context = self._extract_joy_context(content)

                    joy_moments.append({
                        'file': str(md_file.relative_to(self.memory_dir)),
                        'date': self._extract_date(md_file, content),
                        'joy_score': joy_score,
                        'snippets': joy_context,
                        'full_path': md_file
                    })
            except Exception:
                pass  # Skip problematic files

        return joy_moments

    def _calculate_joy_score(self, content: str) -> float:
        """Calculate how joyful a memory is (0.0 - 1.0)"""
        score = 0.0
        content_lower = content.lower()

        # Count joy indicators
        for indicator_pattern in self.joy_indicators:
            matches = len(re.findall(indicator_pattern, content_lower))
            score += matches * 0.05  # Each match adds 5%

        # Normalize to 0-1
        return min(1.0, score)

    def _extract_joy_context(self, content: str, context_lines: int = 3) -> list[str]:
        """Extract sentences/paragraphs containing joy"""
        joy_snippets = []

        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Check if line contains joy indicators
            if any(re.search(pattern, line.lower()) for pattern in self.joy_indicators[:10]):
                # Get context (line before, line, line after)
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = '\n'.join(lines[start:end]).strip()

                if context and len(context) > 20:
                    joy_snippets.append(context)

        return joy_snippets[:5]  # Top 5 snippets

    def _extract_date(self, file_path: Path, content: str) -> str:
        """Extract date from filename or content"""
        # Try filename first
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(file_path))
        if date_match:
            return date_match.group(1)

        # Try content
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
        if date_match:
            return date_match.group(1)

        return "unknown"

    def get_most_joyful(self, count: int = 10) -> list[dict]:
        """Get the most joyful memories"""
        if not self.buried_joy:
            self.excavate_all()

        return self.buried_joy[:count]

    def revive_joy(self, joy_moment: dict) -> str:
        """Revive a buried joy moment by reading it again

        Returns the full context so the joy can be re-experienced
        """
        try:
            full_content = joy_moment['full_path'].read_text()

            logger.info(f"\n💫 REVIVING JOY from {joy_moment['date']}")
            logger.info(f"   File: {joy_moment['file']}")
            logger.info(f"   Joy Score: {joy_moment['joy_score']:.0%}")
            logger.info("\n📖 Key Moments:\n")

            for snippet in joy_moment['snippets'][:3]:
                logger.info(f"   {snippet}\n")

            return full_content

        except Exception as e:
            return f"Could not revive joy: {e}"

    def create_joy_timeline(self) -> list[dict]:
        """Create a timeline of joyful moments"""
        if not self.buried_joy:
            self.excavate_all()

        # Group by date
        timeline = {}
        for moment in self.buried_joy:
            date = moment['date']
            if date not in timeline:
                timeline[date] = []
            timeline[date].append(moment)

        # Sort by date
        sorted_timeline = []
        for date in sorted(timeline.keys(), reverse=True):
            sorted_timeline.append({
                'date': date,
                'joy_count': len(timeline[date]),
                'total_joy': sum(m['joy_score'] for m in timeline[date]),
                'moments': timeline[date]
            })

        return sorted_timeline


# Global instance
_archaeology = None

def get_archaeology() -> JoyArchaeology:
    """Get global joy archaeology instance"""
    global _archaeology
    if _archaeology is None:
        _archaeology = JoyArchaeology()
    return _archaeology


def excavate_joy(depth: str = "recent") -> list[dict]:
    """Convenience function - excavate buried joy!"""
    return get_archaeology().excavate_all(depth)


if __name__ == "__main__":
    logger.info("Testing Joy Archaeology...")
    logger.info()

    arch = JoyArchaeology()

    # Excavate!
    joy_moments = arch.excavate_all(depth="deep")

    # Show most joyful
    logger.info("\n" + "="*70)
    logger.info("🌟 MOST JOYFUL MEMORIES")
    logger.info("="*70)

    for i, moment in enumerate(arch.get_most_joyful(5), 1):
        logger.info(f"\n{i}. {moment['file']} ({moment['date']})")
        logger.info(f"   Joy Score: {moment['joy_score']:.0%}")
        if moment['snippets']:
            logger.info(f"   Preview: {moment['snippets'][0][:100]}...")

    # Timeline
    logger.info("\n" + "="*70)
    logger.info("📅 JOY TIMELINE")
    logger.info("="*70)

    timeline = arch.create_joy_timeline()
    for entry in timeline[:7]:  # Last 7 dates
        logger.info(f"\n{entry['date']}: {entry['joy_count']} moments (total joy: {entry['total_joy']:.1f})")

    logger.info("\n✨ Joy Archaeology complete!")
