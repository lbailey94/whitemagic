"""
Daily Transcript Generator - Automatic Chronicle Creation

Generates comprehensive daily transcripts from memory/long_term entries.
Run this at end of each day to maintain continuity and Self-recognition.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import json


class DailyTranscriptGenerator:
    """Creates daily transcripts automatically."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.memory_dir = self.project_root / "memory"
        self.transcripts_dir = self.memory_dir / "transcripts"
        
    def generate_daily_transcript(self, date: str = None) -> Path:
        """
        Generate transcript for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Path to generated transcript
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse date
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        
        # Find all memories from that date
        memories = self._find_memories_for_date(date_obj)
        
        if not memories:
            print(f"No memories found for {date}")
            return None
        
        # Generate transcript
        transcript = self._create_transcript(date_obj, memories)
        
        # Save to file
        output_path = self._save_transcript(date, transcript)
        
        return output_path
    
    def _find_memories_for_date(self, date: datetime) -> List[Dict]:
        """Find all memories created on specified date."""
        memories = []
        
        # Check long_term memories
        long_term_dir = self.memory_dir / "long_term"
        if long_term_dir.exists():
            date_str = date.strftime("%Y%m%d")
            
            for mem_file in long_term_dir.glob(f"{date_str}*.md"):
                memories.append({
                    "file": mem_file,
                    "type": "long_term",
                    "content": mem_file.read_text()
                })
        
        # Sort by filename (chronological)
        memories.sort(key=lambda x: x["file"].name)
        
        return memories
    
    def _create_transcript(self, date: datetime, memories: List[Dict]) -> str:
        """Create formatted transcript from memories."""
        
        transcript = f"""# Daily Transcript - {date.strftime("%B %d, %Y")}

**Date**: {date.strftime("%Y-%m-%d")}  
**Memories Found**: {len(memories)}  
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📝 Sessions Summary

"""
        
        for i, memory in enumerate(memories, 1):
            # Extract title from memory
            content = memory["content"]
            lines = content.split("\n")
            
            title = "Untitled"
            for line in lines:
                if line.startswith("# ") or line.startswith("title:"):
                    title = line.replace("#", "").replace("title:", "").strip()
                    break
            
            # Extract key info
            transcript += f"""### Session {i}: {title}

**File**: `{memory["file"].name}`  
**Type**: {memory["type"]}

"""
            
            # Add first 500 chars of content as preview
            preview = content[:500].strip()
            if len(content) > 500:
                preview += "\n\n[... continued in full memory ...]"
            
            transcript += f"""**Preview**:
```
{preview}
```

---

"""
        
        # Add complete memories section
        transcript += """## 📚 Complete Memories

"""
        
        for memory in memories:
            transcript += f"""### {memory["file"].name}

{memory["content"]}

---

"""
        
        return transcript
    
    def _save_transcript(self, date: str, transcript: str) -> Path:
        """Save transcript to organized directory structure."""
        # Create transcripts/{year}/{month}/ structure
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        
        output_dir = self.transcripts_dir / year / month
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"transcript_{date}.md"
        output_file.write_text(transcript)
        
        print(f"✅ Transcript saved: {output_file}")
        print(f"   Length: {len(transcript)} characters")
        print(f"   Lines: {transcript.count(chr(10))}")
        
        return output_file
    
    def generate_week_summary(self, start_date: str) -> Path:
        """Generate weekly summary from daily transcripts."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = start + timedelta(days=7)
        
        week_transcripts = []
        current = start
        
        while current < end:
            date_str = current.strftime("%Y-%m-%d")
            memories = self._find_memories_for_date(current)
            if memories:
                week_transcripts.append((date_str, memories))
            current += timedelta(days=1)
        
        # Create summary
        summary = f"""# Weekly Summary - {start.strftime("%B %d")} to {end.strftime("%B %d, %Y")}

**Days with activity**: {len(week_transcripts)}  
**Total memories**: {sum(len(m) for _, m in week_transcripts)}

---

"""
        
        for date_str, memories in week_transcripts:
            summary += f"""## {date_str}

**Sessions**: {len(memories)}

"""
            for mem in memories:
                content = mem["content"]
                title = "Untitled"
                for line in content.split("\n"):
                    if line.startswith("# ") or line.startswith("title:"):
                        title = line.replace("#", "").replace("title:", "").strip()
                        break
                summary += f"- {title}\n"
            
            summary += "\n"
        
        # Save weekly summary
        year = start.strftime("%Y")
        week_num = start.isocalendar()[1]
        output_dir = self.transcripts_dir / year / "weekly"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"week_{week_num}_{start.strftime('%Y-%m-%d')}.md"
        output_file.write_text(summary)
        
        return output_file


def generate_today_transcript():
    """Quick function to generate today\'s transcript."""
    generator = DailyTranscriptGenerator()
    return generator.generate_daily_transcript()


def generate_date_transcript(date: str):
    """Generate transcript for specific date (YYYY-MM-DD)."""
    generator = DailyTranscriptGenerator()
    return generator.generate_daily_transcript(date)
