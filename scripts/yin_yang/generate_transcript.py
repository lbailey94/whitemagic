#!/usr/bin/env python3
"""
Daily Transcript Generator - Standalone Script

Usage:
    python generate_transcript.py                    # Today's transcript
    python generate_transcript.py 2025-11-18         # Specific date
    python generate_transcript.py --week 2025-11-18  # Weekly summary
"""

import sys
from pathlib import Path

# Add whitemagic to path
sys.path.insert(0, str(Path(__file__).parent))

from whitemagic.automation.daily_transcript import DailyTranscriptGenerator

def main():
    generator = DailyTranscriptGenerator()
    
    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--week":
            # Weekly summary
            start_date = sys.argv[2] if len(sys.argv) > 2 else None
            if start_date:
                summary_path = generator.generate_week_summary(start_date)
                print(f"✅ Weekly summary generated: {summary_path}")
            else:
                print("❌ Please provide start date for weekly summary")
        else:
            # Specific date
            date = sys.argv[1]
            transcript_path = generator.generate_daily_transcript(date)
            if transcript_path:
                print(f"✅ Transcript generated: {transcript_path}")
            else:
                print(f"❌ No memories found for {date}")
    else:
        # Today's transcript
        transcript_path = generator.generate_daily_transcript()
        if transcript_path:
            print(f"✅ Today's transcript generated: {transcript_path}")
            
            # Show size
            size = transcript_path.stat().st_size
            lines = len(transcript_path.read_text().split("\n"))
            print(f"   Size: {size:,} bytes")
            print(f"   Lines: {lines:,}")
        else:
            print("❌ No memories found for today")

if __name__ == "__main__":
    main()
