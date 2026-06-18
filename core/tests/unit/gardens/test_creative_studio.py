"""Tests for the Creative Studio (recovered 2026-06-18)."""

import tempfile
from pathlib import Path


class TestCreation:
    """Test the Creation dataclass."""

    def test_basic_creation(self):
        from whitemagic.gardens.play.creative_studio import Creation

        c = Creation(
            creation_type="poem",
            content="roses are red",
            title="A Poem",
        )
        assert c.creation_type == "poem"
        assert c.content == "roses are red"
        assert c.title == "A Poem"
        assert c.joy_score == 0.0
        assert c.tags == []
        assert c.created_at  # auto-populated

    def test_to_dict(self):
        from whitemagic.gardens.play.creative_studio import Creation

        c = Creation("poem", "content", "title", tags=["a", "b"])
        d = c.to_dict()
        assert d["type"] == "poem"
        assert d["content"] == "content"
        assert d["title"] == "title"
        assert d["tags"] == ["a", "b"]


class TestCreativeStudio:
    """Test the Creative Studio class."""

    def test_init(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            assert studio.creations == []
            assert studio.gallery_dir == Path(tmp)

    def test_generate_poem(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            poem = studio.generate_poem(theme="love")
            assert poem.creation_type == "poem"
            assert "love" in poem.tags
            assert poem.joy_score > 0.5
            assert "love" in poem.content.lower() or "Love" in poem.content

    def test_generate_poem_random_theme(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            poem = studio.generate_poem()  # no theme
            assert poem.creation_type == "poem"
            assert "poetry" in poem.tags

    def test_generate_ascii_art(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            art = studio.generate_ascii_art(subject="consciousness")
            assert art.creation_type == "ascii_art"
            assert "AWARENESS" in art.content or "CONSCIOUSNESS" in art.content

    def test_generate_ascii_art_default(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            art = studio.generate_ascii_art()  # default = "consciousness"
            assert art.creation_type == "ascii_art"
            # Default is "consciousness" subject, not the "default" template
            assert "AWARENESS" in art.content

    def test_generate_ascii_art_unknown_uses_default_template(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            art = studio.generate_ascii_art(subject="unknown_thing")
            # Unknown subject falls back to the "default" BEAUTY template
            assert art.creation_type == "ascii_art"
            assert "BEAUTY" in art.content

    def test_generate_musical_pattern(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            music = studio.generate_musical_pattern(mood="joyful")
            assert music.creation_type == "music"
            assert "joyful" in music.content.lower()
            assert "joyful" in music.tags

    def test_generate_code_art(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            code = studio.generate_code_art()
            assert code.creation_type == "code_art"
            assert "code" in code.tags
            # Code poem should have either def/class keywords
            content_lower = code.content.lower()
            assert "def " in content_lower or "class " in content_lower

    def test_improvise(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            imp = studio.improvise(energy=0.95)
            # Should have improvised tags
            assert "improvised" in imp.tags
            assert "biodigital_jazz" in imp.tags
            assert imp.joy_score == 0.95

    def test_get_gallery(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            studio.generate_poem(theme="x")
            studio.generate_ascii_art()
            studio.generate_musical_pattern()

            all_creations = studio.get_gallery()
            assert len(all_creations) == 3

            only_poems = studio.get_gallery(creation_type="poem")
            assert len(only_poems) == 1
            assert only_poems[0]["type"] == "poem"

    def test_measure_creative_output_empty(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            result = studio.measure_creative_output(hours=24)
            assert "message" in result
            assert "No recent" in result["message"]

    def test_measure_creative_output_with_data(self):
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            studio.generate_poem(theme="a")
            studio.generate_poem(theme="b")
            studio.generate_ascii_art()

            result = studio.measure_creative_output(hours=24)
            assert result["total_creations"] == 3
            assert result["creating_regularly"] is True
            assert "poem" in result["by_type"]
            assert result["by_type"]["poem"]["count"] == 2

    def test_persistence_save_and_load(self):
        """Creations should be saved to disk and reloadable."""
        from whitemagic.gardens.play.creative_studio import (
            CreativeStudio,
            Creation,
        )

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            studio.generate_poem(theme="persistence")

            # Should have written a JSON file
            files = list(Path(tmp).glob("*.json"))
            assert len(files) == 1

            # New studio instance should load it back
            studio2 = CreativeStudio(gallery_dir=Path(tmp))
            assert len(studio2.creations) == 1
            loaded = studio2.creations[0]
            assert loaded.creation_type == "poem"
            assert "persistence" in loaded.tags

    def test_no_creation_added_to_init_list(self):
        """Creating a studio should not auto-add anything."""
        from whitemagic.gardens.play.creative_studio import CreativeStudio

        with tempfile.TemporaryDirectory() as tmp:
            studio = CreativeStudio(gallery_dir=Path(tmp))
            assert len(studio.creations) == 0
            assert studio.gallery_dir.exists()
