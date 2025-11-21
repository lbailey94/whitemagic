"""
Voice CLI commands

Provides command-line interface for Voice garden functionality.
"""

import click
from pathlib import Path
from .core import get_voice, VoiceCore, VoiceConfig


@click.group(name="voice")
def voice_cli():
    """Voice garden - Narrative self and authentic expression"""
    pass


@voice_cli.command()
@click.argument("text")
@click.option("--focus", help="What you're focusing on")
@click.option("--emotion", help="Current emotion")
def speak(text: str, focus: str, emotion: str):
    """Speak with your voice"""
    voice = get_voice()
    context = {}
    if focus:
        context["focus"] = focus
    if emotion:
        context["emotion"] = emotion
    
    result = voice.speak(text, context=context if context else None)
    click.echo(f"✓ Spoken: {result['words']} words")


@voice_cli.command()
@click.argument("title")
@click.option("--theme", help="Story theme")
def begin_story(title: str, theme: str):
    """Begin a new story"""
    voice = get_voice()
    result = voice.begin_story(title, theme=theme)
    click.echo(f"✓ Story begun: {result['story']}")


@voice_cli.command()
@click.argument("name")
def begin_chapter(name: str):
    """Begin a new chapter in current story"""
    voice = get_voice()
    result = voice.begin_chapter(name)
    if result["success"]:
        click.echo(f"✓ Chapter begun: {result['chapter']}")
    else:
        click.echo(f"✗ Error: {result.get('error')}", err=True)


@voice_cli.command()
def reflect():
    """Reflect on current narrative"""
    voice = get_voice()
    reflection = voice.reflect()
    click.echo(reflection)


@voice_cli.command()
def status():
    """Show Voice status"""
    voice = get_voice()
    state = voice.get_state()
    
    click.echo("Voice Status:")
    click.echo(f"  Story: {state.get('current_story', 'None')}")
    click.echo(f"  Chapter: {state.get('current_chapter', 'None')}")
    click.echo(f"  Focus: {state.get('current_focus', 'None')}")
    click.echo(f"  Actions: {state.get('actions_taken', 0)}")
    click.echo(f"  Words: {state.get('words_spoken', 0)}")


@voice_cli.command()
def stats():
    """Show Voice statistics"""
    voice = get_voice()
    stats = voice.get_stats()
    
    click.echo("Voice Statistics:")
    click.echo(f"  Stories: {len(stats.get('stories', []))}")
    click.echo(f"  Attention sessions: {stats.get('attention_sessions', 0)}")
    click.echo(f"  Palace rooms: {stats.get('palace_rooms', 0)}")


@voice_cli.command()
@click.option("--story", help="Story to show")
@click.option("--limit", default=10, help="Number of entries")
def recent(story: str, limit: int):
    """Show recent narrative entries"""
    voice = get_voice()
    entries = voice.narrative.get_recent_entries(story=story, limit=limit)
    
    for entry in entries:
        click.echo(f"[{entry['timestamp']}] {entry['text'][:100]}...")


@voice_cli.command()
def stories():
    """List all stories"""
    voice = get_voice()
    story_list = voice.narrative.list_stories()
    
    if story_list:
        click.echo("Stories:")
        for story in story_list:
            click.echo(f"  - {story}")
    else:
        click.echo("No stories yet")


if __name__ == "__main__":
    voice_cli()
