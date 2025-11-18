"""
CLI commands for terminal multiplexing
"""

from pathlib import Path

from whitemagic.scratchpad.manager import ScratchpadManager
from whitemagic.terminal.multiplexer import TerminalMultiplexer


def terminal_session_create(args):
    """Create a new multiplexed session."""
    mux = TerminalMultiplexer()
    
    session = mux.create_session(args.name)
    
    print(f"📺 Created multiplexed session: {session.name}")
    print(f"   Session ID: {session.id}")
    print()
    print("💡 Next steps:")
    print(f"   1. Create pads: whitemagic terminal pad-new <name>")
    print(f"   2. Switch pads: whitemagic terminal pad-switch <name>")
    print(f"   3. View layout: whitemagic terminal layout")


def terminal_pad_new(args):
    """Create a new pad in current session."""
    mux = TerminalMultiplexer()
    pad_manager = ScratchpadManager()
    
    # Load current session or create one
    sessions = mux.list_sessions()
    if not sessions:
        print("⚠️  No active session. Creating one...")
        session = mux.create_session("default")
    elif not mux.current_session:
        mux.load_session(sessions[0]["id"])
    
    # Create scratchpad
    import asyncio
    pad = asyncio.run(pad_manager.create(
        name=args.name,
        session_id=mux.current_session.id if mux.current_session else None
    ))
    
    # Add to session
    if mux.current_session:
        mux.add_pad(args.name, pad.id)
        print(f"✅ Created pad: {args.name}")
        print(f"   Pad ID: {pad.id}")
        _show_layout(mux)
    else:
        print(f"⚠️  Pad created but not added to session")


def terminal_pad_switch(args):
    """Switch to a different pad."""
    mux = TerminalMultiplexer()
    
    sessions = mux.list_sessions()
    if not sessions:
        print("❌ No active sessions")
        return
    
    if not mux.current_session:
        mux.load_session(sessions[0]["id"])
    
    pad_id = mux.switch_pad(args.name)
    
    if pad_id:
        print(f"✅ Switched to pad: {args.name}")
        _show_layout(mux)
    else:
        print(f"❌ Pad not found: {args.name}")
        print("\nAvailable pads:")
        for pad in mux.list_pads():
            symbol = "▶" if pad["active"] else "▷"
            print(f"  {symbol} {pad['name']}")


def terminal_layout(args):
    """Show current session layout."""
    mux = TerminalMultiplexer()
    
    sessions = mux.list_sessions()
    if not sessions:
        print("📺 No active sessions")
        print("\n💡 Create one: whitemagic terminal session-create <name>")
        return
    
    if not mux.current_session:
        mux.load_session(sessions[0]["id"])
    
    _show_layout(mux)


def terminal_sessions_list(args):
    """List all sessions."""
    mux = TerminalMultiplexer()
    
    sessions = mux.list_sessions()
    
    if not sessions:
        print("📺 No active sessions")
        return
    
    print("📺 Active Terminal Sessions")
    print("=" * 60)
    
    for session in sessions:
        print(f"\n• {session['name']}")
        print(f"  ID: {session['id']}")
        print(f"  Pads: {session['pads']}")
        print(f"  Last accessed: {session['last_accessed']}")


def _show_layout(mux: TerminalMultiplexer):
    """Display session layout."""
    layout = mux.get_session_layout()
    
    if "error" in layout:
        print(f"❌ {layout['error']}")
        return
    
    print()
    print(f"📺 Session: {layout['session']}")
    print("─" * 40)
    
    for pad in layout["layout"]:
        symbol = pad["symbol"]
        name = pad["name"]
        active_marker = " (ACTIVE)" if pad["active"] else ""
        print(f"{symbol} {name}{active_marker}")
    
    print("─" * 40)
    print(f"Total pads: {layout['pads']}")


def register_terminal_commands(subparsers):
    """Register terminal multiplexer commands."""
    
    # Main terminal command
    terminal_parser = subparsers.add_parser(
        "terminal",
        help="Terminal multiplexer - parallel thought streams"
    )
    terminal_subparsers = terminal_parser.add_subparsers(dest="terminal_command")
    
    # Session create
    session_create_parser = terminal_subparsers.add_parser(
        "session-create",
        help="Create new multiplexed session"
    )
    session_create_parser.add_argument("name", help="Session name")
    session_create_parser.set_defaults(func=terminal_session_create)
    
    # Pad new
    pad_new_parser = terminal_subparsers.add_parser(
        "pad-new",
        help="Create new pad in current session"
    )
    pad_new_parser.add_argument("name", help="Pad name")
    pad_new_parser.set_defaults(func=terminal_pad_new)
    
    # Pad switch
    pad_switch_parser = terminal_subparsers.add_parser(
        "pad-switch",
        help="Switch to different pad"
    )
    pad_switch_parser.add_argument("name", help="Pad name")
    pad_switch_parser.set_defaults(func=terminal_pad_switch)
    
    # Layout
    layout_parser = terminal_subparsers.add_parser(
        "layout",
        help="Show current session layout"
    )
    layout_parser.set_defaults(func=terminal_layout)
    
    # Sessions list
    sessions_parser = terminal_subparsers.add_parser(
        "sessions",
        help="List all sessions"
    )
    sessions_parser.set_defaults(func=terminal_sessions_list)
