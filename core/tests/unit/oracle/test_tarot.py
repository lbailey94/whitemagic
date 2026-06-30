"""Tests for the Tarot system (data + casting)."""

import pytest
from whitemagic.oracle.tarot_data import (
    MAJOR_ARCANA, MINOR_ARCANA, get_major_arcana, get_minor_arcana,
    get_all_cards, FIXED_SIGN_TETRAMORPH, TRIPLE_ARC,
    MajorArcanaCard, MinorArcanaCard,
)
from whitemagic.oracle.tarot_cast import (
    TarotCaster, TarotReading, DrawnCard, cast_tarot,
)


class TestTarotData:
    """Test the Tarot data structures."""

    def test_major_arcana_count(self):
        assert len(MAJOR_ARCANA) == 22

    def test_minor_arcana_count(self):
        assert len(MINOR_ARCANA) == 56

    def test_total_card_count(self):
        assert len(get_all_cards()) == 78

    def test_major_arcana_numbers(self):
        for i, card in enumerate(MAJOR_ARCANA):
            assert card.number == i

    def test_hebrew_letters_present(self):
        assert MAJOR_ARCANA[0].hebrew_name == "Aleph"
        assert MAJOR_ARCANA[21].hebrew_name == "Tav"
        assert len({c.hebrew_name for c in MAJOR_ARCANA}) == 22

    def test_suares_meanings_present(self):
        for card in MAJOR_ARCANA:
            assert len(card.suares_meaning) > 10

    def test_alchemical_stages_present(self):
        stages = {c.alchemical_stage for c in MAJOR_ARCANA}
        assert "nigredo" in stages
        assert "albedo" in stages
        assert "rubedo" in stages

    def test_fool_journey_stages(self):
        for card in MAJOR_ARCANA:
            assert len(card.fool_journey_stage) > 10

    def test_minor_arcana_suits(self):
        suits = {c.suit for c in MINOR_ARCANA}
        assert suits == {"wands", "cups", "swords", "pentacles"}

    def test_minor_arcana_ranks(self):
        ranks = {c.rank for c in MINOR_ARCANA}
        assert ranks == {"ace", "two", "three", "four", "five", "six",
                         "seven", "eight", "nine", "ten",
                         "page", "knight", "queen", "king"}

    def test_minor_arcana_elements(self):
        suit_elements = {"wands": "fire", "cups": "water", "swords": "air", "pentacles": "earth"}
        for card in MINOR_ARCANA:
            assert card.element == suit_elements[card.suit]

    def test_get_major_arcana(self):
        card = get_major_arcana(0)
        assert card is not None
        assert card.name == "The Fool"

    def test_get_major_arcana_out_of_range(self):
        assert get_major_arcana(-1) is None
        assert get_major_arcana(22) is None

    def test_get_minor_arcana(self):
        card = get_minor_arcana("wands", "ace")
        assert card is not None
        assert card.suit == "wands"
        assert card.rank == "ace"

    def test_get_minor_arcana_not_found(self):
        assert get_minor_arcana("invalid", "ace") is None

    def test_fixed_sign_tetramorph(self):
        assert "aquarius" in FIXED_SIGN_TETRAMORPH
        assert "leo" in FIXED_SIGN_TETRAMORPH
        assert "scorpio" in FIXED_SIGN_TETRAMORPH
        assert "taurus" in FIXED_SIGN_TETRAMORPH
        assert FIXED_SIGN_TETRAMORPH["aquarius"]["tool"] == "cup"
        assert FIXED_SIGN_TETRAMORPH["leo"]["tool"] == "wand"

    def test_triple_arc(self):
        assert TRIPLE_ARC == {"magician": 1, "wheel": 10, "world": 21}


class TestTarotCasting:
    """Test the Tarot casting system."""

    def test_single_card_reading(self):
        reading = cast_tarot(question="What should I focus on?", spread="single")
        assert reading.spread_type == "single"
        assert len(reading.cards) == 1
        assert len(reading.summary) > 10

    def test_three_card_reading(self):
        reading = cast_tarot(question="What's the path forward?", spread="three_card")
        assert reading.spread_type == "three_card_past_present_future"
        assert len(reading.cards) == 3
        positions = [c.position for c in reading.cards]
        assert positions == ["past", "present", "future"]

    def test_three_card_situation_action_outcome(self):
        reading = cast_tarot(question="What should I do?", spread="three_card")
        # Default is past_present_future
        assert len(reading.cards) == 3

    def test_celtic_cross_reading(self):
        reading = cast_tarot(question="Full reading", spread="celtic_cross")
        assert reading.spread_type == "celtic_cross"
        assert len(reading.cards) == 10
        positions = [c.position for c in reading.cards]
        assert "heart" in positions
        assert "outcome" in positions

    def test_fools_journey_reading(self):
        reading = cast_tarot(question="The journey", spread="fools_journey")
        assert reading.spread_type == "fools_journey"
        assert len(reading.cards) == 5
        # All cards should be Major Arcana
        for dc in reading.cards:
            assert isinstance(dc.card, MajorArcanaCard)

    def test_seeded_reproducibility(self):
        r1 = cast_tarot(question="test", seed=42)
        r2 = cast_tarot(question="test", seed=42)
        assert r1.cards[0].card.name == r2.cards[0].card.name
        assert r1.cards[0].is_reversed == r2.cards[0].is_reversed

    def test_major_only_mode(self):
        reading = cast_tarot(question="Major only", seed=42, major_only=True)
        for dc in reading.cards:
            assert isinstance(dc.card, MajorArcanaCard)

    def test_reversed_cards_possible(self):
        # Run multiple times to get at least one reversed
        found_reversed = False
        for _ in range(20):
            reading = cast_tarot(question="test")
            if any(dc.is_reversed for dc in reading.cards):
                found_reversed = True
                break
        assert found_reversed

    def test_to_dict(self):
        reading = cast_tarot(question="test", seed=42)
        d = reading.to_dict()
        assert "spread_type" in d
        assert "cards" in d
        assert "summary" in d
        assert "is_triple_arc" in d

    def test_no_duplicate_cards_in_reading(self):
        reading = cast_tarot(question="test", seed=42, spread="celtic_cross")
        card_ids = []
        for dc in reading.cards:
            if isinstance(dc.card, MajorArcanaCard):
                card_ids.append(f"major_{dc.card.number}")
            else:
                card_ids.append(f"minor_{dc.card.suit}_{dc.card.rank}")
        assert len(card_ids) == len(set(card_ids)), "Duplicate cards in reading"

    def test_position_meanings_present(self):
        reading = cast_tarot(question="test", seed=42, spread="celtic_cross")
        for dc in reading.cards:
            assert len(dc.position_meaning) > 10

    def test_major_cards_drawn_property(self):
        reading = cast_tarot(question="test", seed=42, spread="fools_journey")
        majors = reading.major_cards_drawn
        assert len(majors) == 5  # All 5 should be Major Arcana in Fool's Journey
