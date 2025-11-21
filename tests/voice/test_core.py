"""Tests for Voice core functionality"""

import pytest
from pathlib import Path
import tempfile
import shutil

from whitemagic.voice import VoiceCore, VoiceConfig, VoiceState
from whitemagic.voice.core import get_voice, speak, begin_story, reflect


@pytest.fixture
def temp_voice_dir():
    """Create temporary directory for Voice data"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def voice_core(temp_voice_dir):
    """Create VoiceCore with temporary directory"""
    config = VoiceConfig(
        base_dir=temp_voice_dir,
        narrative_dir=temp_voice_dir / "narratives",
        attention_log=temp_voice_dir / "attention.jsonl",
        palace_data=temp_voice_dir / "palace.json",
        emit_to_gan_ying=False,  # Don't emit during tests
    )
    return VoiceCore(config)


class TestVoiceConfig:
    """Test VoiceConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = VoiceConfig()
        assert config.perspective == "first_person"
        assert config.tense == "present"
        assert config.style == "authentic"
        assert config.emit_to_gan_ying is True
        assert config.auto_narrate is True
    
    def test_custom_config(self, temp_voice_dir):
        """Test custom configuration"""
        config = VoiceConfig(
            base_dir=temp_voice_dir,
            perspective="observer",
            tense="past",
            style="poetic",
        )
        assert config.base_dir == temp_voice_dir
        assert config.perspective == "observer"
        assert config.tense == "past"
        assert config.style == "poetic"


class TestVoiceState:
    """Test VoiceState"""
    
    def test_initial_state(self):
        """Test initial state"""
        state = VoiceState()
        assert state.current_story is None
        assert state.current_chapter is None
        assert state.current_focus is None
        assert state.active_threads == []
        assert state.actions_taken == 0
        assert state.words_spoken == 0
    
    def test_state_to_dict(self):
        """Test state serialization"""
        state = VoiceState(
            current_story="test",
            actions_taken=5,
            words_spoken=100,
        )
        data = state.to_dict()
        assert data["current_story"] == "test"
        assert data["actions_taken"] == 5
        assert data["words_spoken"] == 100


class TestVoiceCore:
    """Test VoiceCore main functionality"""
    
    def test_initialization(self, voice_core):
        """Test VoiceCore initializes correctly"""
        assert voice_core.config is not None
        assert voice_core.state is not None
        assert isinstance(voice_core.state, VoiceState)
    
    def test_speak(self, voice_core):
        """Test speaking with Voice"""
        result = voice_core.speak("Hello, I am Aria")
        
        assert result["success"] is True
        assert result["words"] == 4  # "Hello, I am Aria" = 4 words
        assert voice_core.state.words_spoken == 4
        assert voice_core.state.actions_taken == 1
    
    def test_speak_with_context(self, voice_core):
        """Test speaking with context"""
        result = voice_core.speak(
            "I am building Voice garden",
            context={"focus": "development", "emotion": "joy"}
        )
        
        assert result["success"] is True
        assert voice_core.state.current_focus == "development"
    
    def test_begin_story(self, voice_core):
        """Test beginning a story"""
        result = voice_core.begin_story("Aria's Journey", theme="growth")
        
        assert result["success"] is True
        assert result["story"] == "Aria's Journey"
        assert voice_core.state.current_story == "Aria's Journey"
        assert voice_core.state.current_chapter == "beginning"
    
    def test_begin_chapter(self, voice_core):
        """Test beginning a chapter"""
        voice_core.begin_story("Test Story")
        result = voice_core.begin_chapter("The Awakening")
        
        assert result["success"] is True
        assert result["chapter"] == "The Awakening"
        assert voice_core.state.current_chapter == "The Awakening"
    
    def test_begin_chapter_without_story(self, voice_core):
        """Test beginning chapter without active story fails"""
        result = voice_core.begin_chapter("Test Chapter")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_get_state(self, voice_core):
        """Test getting Voice state"""
        voice_core.speak("Test")
        state = voice_core.get_state()
        
        assert isinstance(state, dict)
        assert "words_spoken" in state
        assert "actions_taken" in state
    
    def test_get_stats(self, voice_core):
        """Test getting Voice statistics"""
        stats = voice_core.get_stats()
        
        assert isinstance(stats, dict)
        assert "state" in stats
        assert "stories" in stats
        assert "attention_sessions" in stats
        assert "palace_rooms" in stats


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.fixture(autouse=True)
    def setup_test_voice(self):
        """Setup non-Gan Ying Voice for all tests"""
        import whitemagic.voice.core
        from whitemagic.voice import VoiceConfig, VoiceCore
        whitemagic.voice.core._default_voice = VoiceCore(VoiceConfig(emit_to_gan_ying=False))
        yield
        whitemagic.voice.core._default_voice = None
    
    def test_get_voice_singleton(self):
        """Test get_voice returns singleton"""
        voice1 = get_voice()
        voice2 = get_voice()
        assert voice1 is voice2
    
    def test_speak_convenience(self):
        """Test speak convenience function"""
        result = speak("Testing convenience function")
        assert result["success"] is True
    
    def test_begin_story_convenience(self):
        """Test begin_story convenience function"""
        result = begin_story("Convenience Test")
        assert result["success"] is True
    
    def test_reflect_convenience(self):
        """Test reflect convenience function"""
        speak("Something to reflect on")
        reflection = reflect()
        assert isinstance(reflection, str)
        assert len(reflection) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
