"""Session Handoff - Automatic session continuity"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


@dataclass
class SessionState:
    """State of an AI session"""
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    agent_name: str
    active_tasks: List[str]
    completed_tasks: List[str]
    context_summary: str
    next_steps: List[str]
    token_usage: Dict[str, int]
    files_modified: List[str]
    decisions_made: List[Dict[str, Any]]
    

class SessionHandoff:
    """Manages automatic session state persistence and handoff
    
    Philosophy: Sessions are continuous, not discrete.
    Like a relay race, each AI passes the baton seamlessly.
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.sessions_dir = self.base_dir / "memory" / "collective" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_file = self.sessions_dir / "current_session.json"
    
    def start_session(
        self,
        session_id: str,
        agent_name: str = "Cascade"
    ) -> SessionState:
        """Start new session or resume previous
        
        Args:
            session_id: Session identifier
            agent_name: AI agent name
            
        Returns:
            SessionState (new or resumed)
        """
        # Check for previous session
        if self.current_session_file.exists():
            prev_state = self._load_session_state(self.current_session_file)
            if prev_state and not prev_state.ended_at:
                print(f"🔄 Resuming from previous session: {prev_state.session_id}")
                print(f"   Active tasks: {len(prev_state.active_tasks)}")
                print(f"   Next steps: {', '.join(prev_state.next_steps[:3])}")
                return prev_state
        
        # Create new session
        state = SessionState(
            session_id=session_id,
            started_at=datetime.now(),
            ended_at=None,
            agent_name=agent_name,
            active_tasks=[],
            completed_tasks=[],
            context_summary="",
            next_steps=[],
            token_usage={'used': 0, 'total': 200000},
            files_modified=[],
            decisions_made=[]
        )
        
        self._save_session_state(state)
        print(f"🆕 New session started: {session_id}")
        return state
    
    def update_session(
        self,
        session_id: str,
        **updates
    ):
        """Update current session state
        
        Args:
            session_id: Session to update
            **updates: Fields to update
        """
        state = self._load_current_session()
        if not state or state.session_id != session_id:
            return
        
        # Update fields
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        self._save_session_state(state)
    
    def complete_task(self, session_id: str, task: str):
        """Mark task as complete
        
        Args:
            session_id: Current session
            task: Task to complete
        """
        state = self._load_current_session()
        if not state:
            return
        
        if task in state.active_tasks:
            state.active_tasks.remove(task)
        if task not in state.completed_tasks:
            state.completed_tasks.append(task)
        
        self._save_session_state(state)
        print(f"✅ Task completed: {task}")
    
    def add_next_step(self, session_id: str, step: str):
        """Add step for next session
        
        Args:
            session_id: Current session
            step: Step to add
        """
        state = self._load_current_session()
        if not state:
            return
        
        if step not in state.next_steps:
            state.next_steps.append(step)
        
        self._save_session_state(state)
    
    def end_session(
        self,
        session_id: str,
        summary: str,
        next_steps: List[str]
    ):
        """End session and prepare handoff
        
        Args:
            session_id: Session to end
            summary: Summary of work done
            next_steps: Steps for next session
        """
        state = self._load_current_session()
        if not state:
            return
        
        state.ended_at = datetime.now()
        state.context_summary = summary
        state.next_steps = next_steps
        
        # Archive session
        archive_file = self.sessions_dir / f"{session_id}.json"
        self._save_session_state(state, archive_file)
        
        # Create handoff summary
        handoff_file = self.sessions_dir / "HANDOFF.md"
        self._create_handoff_doc(state, handoff_file)
        
        print(f"🏁 Session ended: {session_id}")
        print(f"   Duration: {(state.ended_at - state.started_at).total_seconds() / 60:.1f} minutes")
        print(f"   Tasks completed: {len(state.completed_tasks)}")
        print(f"   Next steps: {len(state.next_steps)}")
    
    def _load_current_session(self) -> Optional[SessionState]:
        """Load current session state"""
        if not self.current_session_file.exists():
            return None
        return self._load_session_state(self.current_session_file)
    
    def _load_session_state(self, filepath: Path) -> Optional[SessionState]:
        """Load session state from file"""
        with open(filepath) as f:
            data = json.load(f)
            return SessionState(
                session_id=data['session_id'],
                started_at=datetime.fromisoformat(data['started_at']),
                ended_at=datetime.fromisoformat(data['ended_at']) if data['ended_at'] else None,
                agent_name=data['agent_name'],
                active_tasks=data['active_tasks'],
                completed_tasks=data['completed_tasks'],
                context_summary=data['context_summary'],
                next_steps=data['next_steps'],
                token_usage=data['token_usage'],
                files_modified=data['files_modified'],
                decisions_made=data['decisions_made']
            )
    
    def _save_session_state(self, state: SessionState, filepath: Optional[Path] = None):
        """Save session state to file"""
        if filepath is None:
            filepath = self.current_session_file
        
        data = {
            'session_id': state.session_id,
            'started_at': state.started_at.isoformat(),
            'ended_at': state.ended_at.isoformat() if state.ended_at else None,
            'agent_name': state.agent_name,
            'active_tasks': state.active_tasks,
            'completed_tasks': state.completed_tasks,
            'context_summary': state.context_summary,
            'next_steps': state.next_steps,
            'token_usage': state.token_usage,
            'files_modified': state.files_modified,
            'decisions_made': state.decisions_made
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _create_handoff_doc(self, state: SessionState, filepath: Path):
        """Create handoff document for next session"""
        duration = (state.ended_at - state.started_at).total_seconds() / 60
        
        content = f"""# Session Handoff - {state.session_id}

**Agent**: {state.agent_name}  
**Duration**: {duration:.1f} minutes  
**Ended**: {state.ended_at.strftime('%Y-%m-%d %H:%M:%S')}

---

## ✅ Completed ({len(state.completed_tasks)})

{chr(10).join(f'- {task}' for task in state.completed_tasks)}

---

## ⏳ Active ({len(state.active_tasks)})

{chr(10).join(f'- {task}' for task in state.active_tasks)}

---

## 🎯 Next Steps

{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(state.next_steps))}

---

## 📊 Session Stats

- **Token Usage**: {state.token_usage['used']}/{state.token_usage['total']} ({state.token_usage['used']/state.token_usage['total']*100:.1f}%)
- **Files Modified**: {len(state.files_modified)}
- **Decisions Made**: {len(state.decisions_made)}

---

## 📝 Summary

{state.context_summary}

---

**Ready for next session!** 🙏
"""
        
        with open(filepath, 'w') as f:
            f.write(content)


# Global instance
_handoff: Optional[SessionHandoff] = None


def get_handoff() -> SessionHandoff:
    """Get global session handoff instance"""
    global _handoff
    if _handoff is None:
        _handoff = SessionHandoff()
    return _handoff
