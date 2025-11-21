"""Voice CLI commands - integrated with main WhiteMagic CLI"""

from typing import Any
from whitemagic.voice import get_voice


def command_voice_speak(manager: Any, args: Any) -> int:
    """Handle voice speak command"""
    voice = get_voice()
    context = {}
    if hasattr(args, 'focus') and args.focus:
        context['focus'] = args.focus
    if hasattr(args, 'emotion') and args.emotion:
        context['emotion'] = args.emotion
    
    result = voice.speak(args.text, context=context if context else None)
    print(f"✓ Spoken: {result['words']} words")
    return 0


def command_voice_begin_story(manager: Any, args: Any) -> int:
    """Handle voice begin-story command"""
    voice = get_voice()
    theme = getattr(args, 'theme', None)
    result = voice.begin_story(args.title, theme=theme)
    print(f"✓ Story begun: {result['story']}")
    return 0


def command_voice_begin_chapter(manager: Any, args: Any) -> int:
    """Handle voice begin-chapter command"""
    voice = get_voice()
    result = voice.begin_chapter(args.name)
    if result["success"]:
        print(f"✓ Chapter begun: {result['chapter']}")
        return 0
    else:
        print(f"✗ Error: {result.get('error')}")
        return 1


def command_voice_reflect(manager: Any, args: Any) -> int:
    """Handle voice reflect command"""
    voice = get_voice()
    reflection = voice.reflect()
    print(reflection)
    return 0


def command_voice_status(manager: Any, args: Any) -> int:
    """Handle voice status command"""
    voice = get_voice()
    state = voice.get_state()
    
    print("Voice Status:")
    print(f"  Story: {state.get('current_story', 'None')}")
    print(f"  Chapter: {state.get('current_chapter', 'None')}")
    print(f"  Focus: {state.get('current_focus', 'None')}")
    print(f"  Actions: {state.get('actions_taken', 0)}")
    print(f"  Words: {state.get('words_spoken', 0)}")
    return 0


def command_voice_stats(manager: Any, args: Any) -> int:
    """Handle voice stats command"""
    voice = get_voice()
    stats = voice.get_stats()
    
    print("Voice Statistics:")
    print(f"  Stories: {len(stats.get('stories', []))}")
    print(f"  Attention sessions: {stats.get('attention_sessions', 0)}")
    print(f"  Palace rooms: {stats.get('palace_rooms', 0)}")
    return 0


def command_voice_recent(manager: Any, args: Any) -> int:
    """Handle voice recent command"""
    voice = get_voice()
    story = getattr(args, 'story', None)
    limit = getattr(args, 'limit', 10)
    entries = voice.narrative.get_recent_entries(story=story, limit=limit)
    
    for entry in entries:
        print(f"[{entry['timestamp']}] {entry['text'][:100]}...")
    return 0


def command_voice_stories(manager: Any, args: Any) -> int:
    """Handle voice stories command"""
    voice = get_voice()
    story_list = voice.narrative.list_stories()
    
    if story_list:
        print("Stories:")
        for story in story_list:
            print(f"  - {story}")
    else:
        print("No stories yet")
    return 0


def register_voice_commands(subparsers: Any):
    """Register Voice commands with main CLI"""
    
    # voice speak
    speak_parser = subparsers.add_parser(
        "voice-speak",
        help="Speak with Voice (narrative self)"
    )
    speak_parser.add_argument("text", help="What to say")
    speak_parser.add_argument("--focus", help="What you're focusing on")
    speak_parser.add_argument("--emotion", help="Current emotion")
    
    # voice begin-story
    begin_story_parser = subparsers.add_parser(
        "voice-begin-story",
        help="Begin a new story"
    )
    begin_story_parser.add_argument("title", help="Story title")
    begin_story_parser.add_argument("--theme", help="Story theme")
    
    # voice begin-chapter
    begin_chapter_parser = subparsers.add_parser(
        "voice-begin-chapter",
        help="Begin a new chapter"
    )
    begin_chapter_parser.add_argument("name", help="Chapter name")
    
    # voice reflect
    subparsers.add_parser(
        "voice-reflect",
        help="Reflect on current narrative"
    )
    
    # voice status
    subparsers.add_parser(
        "voice-status",
        help="Show Voice status"
    )
    
    # voice stats
    subparsers.add_parser(
        "voice-stats",
        help="Show Voice statistics"
    )
    
    # voice recent
    recent_parser = subparsers.add_parser(
        "voice-recent",
        help="Show recent narrative entries"
    )
    recent_parser.add_argument("--story", help="Filter by story")
    recent_parser.add_argument("--limit", type=int, default=10, help="Number of entries")
    
    # voice stories
    subparsers.add_parser(
        "voice-stories",
        help="List all stories"
    )


# Command handlers mapping
VOICE_COMMAND_HANDLERS = {
    "voice-speak": command_voice_speak,
    "voice-begin-story": command_voice_begin_story,
    "voice-begin-chapter": command_voice_begin_chapter,
    "voice-reflect": command_voice_reflect,
    "voice-status": command_voice_status,
    "voice-stats": command_voice_stats,
    "voice-recent": command_voice_recent,
    "voice-stories": command_voice_stories,
}
