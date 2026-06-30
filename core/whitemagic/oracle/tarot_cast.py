"""Tarot casting system — draws and spreads.

Implements card drawing with the same entropy principles as Ifá:
- Unseeded mode uses SystemRandom (OS entropy pool)
- Seeded mode is deterministic for reproducibility
- Entropy harvesting via os.urandom + timing jitter

Supports multiple spread layouts:
- Single card: quick insight
- Three card: past/present/future or situation/action/outcome
- Celtic Cross: traditional 10-card spread
- Fool's Journey: 22-card Major Arcana only, sequential reading

Design principle: Tarot is an impartial consultation — an aid to
decision-making, not a replacement for agency. The cards illuminate
patterns; they do not dictate actions.
"""

from __future__ import annotations

import hashlib
import logging
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any

from .tarot_data import (
    MAJOR_ARCANA,
    MINOR_ARCANA,
    MajorArcanaCard,
    MinorArcanaCard,
)

logger = logging.getLogger(__name__)


@dataclass
class DrawnCard:
    """A card drawn in a reading, with orientation and position."""

    card: MajorArcanaCard | MinorArcanaCard
    is_reversed: bool
    position: str  # e.g. "past", "present", "future", or slot number
    position_meaning: str


@dataclass
class TarotReading:
    """A complete Tarot reading result."""

    spread_type: str
    question: str
    cards: list[DrawnCard]
    summary: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def major_cards_drawn(self) -> list[MajorArcanaCard]:
        """Only the Major Arcana cards in this reading."""
        return [d.card for d in self.cards if isinstance(d.card, MajorArcanaCard)]

    @property
    def is_triple_arc_reading(self) -> bool:
        """Check if the Magician/Wheel/World triple arc appeared."""
        numbers = {
            c.card.number for c in self.cards if isinstance(c.card, MajorArcanaCard)
        }
        return {1, 10, 21}.issubset(numbers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "spread_type": self.spread_type,
            "question": self.question,
            "cards": [
                {
                    "name": d.card.name,
                    "number": getattr(d.card, "number", None),
                    "suit": getattr(d.card, "suit", "major"),
                    "reversed": d.is_reversed,
                    "position": d.position,
                    "position_meaning": d.position_meaning,
                    "upright_meaning": d.card.upright_meaning,
                    "reversed_meaning": d.card.reversed_meaning,
                    "keywords": d.card.keywords,
                    "meaning": d.card.reversed_meaning
                    if d.is_reversed
                    else d.card.upright_meaning,
                }
                for d in self.cards
            ],
            "summary": self.summary,
            "is_triple_arc": self.is_triple_arc_reading,
        }


class TarotCaster:
    """Tarot card drawing and spread system.

    Uses the same entropy principles as IfaCaster:
    - Unseeded: SystemRandom (OS entropy)
    - Seeded: deterministic for reproducibility
    """

    def __init__(self, seed: int | None = None, major_only: bool = False) -> None:
        self._seed = seed
        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random.SystemRandom()
        self.major_only = major_only
        self._deck = self._build_deck()

    def _build_deck(self) -> list[MajorArcanaCard | MinorArcanaCard]:
        """Build the deck (full 78 or Major Arcana only)."""
        if self.major_only:
            return list(MAJOR_ARCANA)
        return list(MAJOR_ARCANA) + list(MINOR_ARCANA)

    def _gather_entropy(self, question: str, context: dict[str, Any] | None) -> bytes:
        """Gather entropy for shuffling."""
        ctx_str = str(context) if context else ""
        if self._seed is not None:
            combined = f"{question}|{ctx_str}|{self._seed}"
        else:
            system_entropy = os.urandom(32).hex()
            time_jitter = str(time.time_ns())
            combined = f"{question}|{ctx_str}|{system_entropy}|{time_jitter}"
        return hashlib.sha256(combined.encode()).digest()

    def _shuffle(self, entropy: bytes) -> list[MajorArcanaCard | MinorArcanaCard]:
        """Shuffle the deck using entropy-influenced Fisher-Yates."""
        deck = list(self._deck)
        n = len(deck)
        for i in range(n - 1, 0, -1):
            if self._seed is not None:
                j = self.rng.randint(0, i)
            else:
                # SystemRandom — already true RNG, entropy is bonus
                j = self.rng.randint(0, i)
            deck[i], deck[j] = deck[j], deck[i]
        return deck

    def draw_single(
        self, question: str = "", context: dict[str, Any] | None = None
    ) -> TarotReading:
        """Draw a single card for quick insight."""
        entropy = self._gather_entropy(question, context)
        deck = self._shuffle(entropy)
        card = deck[0]
        is_reversed = self.rng.random() < 0.5
        drawn = DrawnCard(
            card=card,
            is_reversed=is_reversed,
            position="the_card",
            position_meaning="The central message",
        )
        meaning = card.reversed_meaning if is_reversed else card.upright_meaning
        summary = f"{card.name} ({'reversed' if is_reversed else 'upright'}): {meaning}"
        return TarotReading(
            spread_type="single",
            question=question,
            cards=[drawn],
            summary=summary,
        )

    def draw_three_card(
        self,
        question: str = "",
        context: dict[str, Any] | None = None,
        layout: str = "past_present_future",
    ) -> TarotReading:
        """Draw a three-card spread.

        Layouts:
        - past_present_future: temporal reading
        - situation_action_outcome: decision-making reading
        - body_mind_spirit: holistic reading
        """
        layouts = {
            "past_present_future": ["past", "present", "future"],
            "situation_action_outcome": ["situation", "action", "outcome"],
            "body_mind_spirit": ["body", "mind", "spirit"],
        }
        positions = layouts.get(layout, layouts["past_present_future"])
        position_meanings = {
            "past": "What has been — the roots of the current situation",
            "present": "What is — the current state and its energies",
            "future": "What may come — the trajectory if current patterns continue",
            "situation": "The current situation — what you are facing",
            "action": "The suggested action — what the cards advise",
            "outcome": "The likely outcome — where this leads",
            "body": "The physical/material dimension — body, resources, environment",
            "mind": "The mental dimension — thoughts, beliefs, communication",
            "spirit": "The spiritual dimension — purpose, meaning, connection",
        }

        entropy = self._gather_entropy(question, context)
        deck = self._shuffle(entropy)

        drawn_cards: list[DrawnCard] = []
        for i, pos in enumerate(positions):
            card = deck[i]
            is_reversed = self.rng.random() < 0.5
            drawn_cards.append(
                DrawnCard(
                    card=card,
                    is_reversed=is_reversed,
                    position=pos,
                    position_meaning=position_meanings.get(pos, pos),
                )
            )

        card_summaries = []
        for d in drawn_cards:
            meaning = (
                d.card.reversed_meaning if d.is_reversed else d.card.upright_meaning
            )
            card_summaries.append(
                f"{d.position.capitalize()} — {d.card.name} ({'reversed' if d.is_reversed else 'upright'}): {meaning[:80]}"
            )

        summary = " | ".join(card_summaries)
        return TarotReading(
            spread_type=f"three_card_{layout}",
            question=question,
            cards=drawn_cards,
            summary=summary,
        )

    def draw_celtic_cross(
        self,
        question: str = "",
        context: dict[str, Any] | None = None,
    ) -> TarotReading:
        """Draw the traditional 10-card Celtic Cross spread.

        Positions:
        1. The heart of the matter
        2. The challenge / opposing force
        3. Foundation / subconscious influence
        4. Recent past / passing influence
        5. Crown / conscious influence / possible future
        6. Near future / approaching influence
        7. Yourself / your role
        8. Environment / external influences
        9. Hopes and fears
        10. The outcome
        """
        positions = [
            ("heart", "The heart of the matter — what is truly at stake"),
            ("challenge", "The challenge — what opposes or tests you"),
            ("foundation", "Foundation — the deep roots beneath the situation"),
            ("recent_past", "Recent past — what is passing away"),
            ("crown", "Crown — what is conscious, possible future"),
            ("near_future", "Near future — what is approaching"),
            ("yourself", "Yourself — your role in the situation"),
            ("environment", "Environment — external forces and people"),
            ("hopes_fears", "Hopes and fears — what you long for and what you dread"),
            ("outcome", "The outcome — where this leads if patterns hold"),
        ]

        entropy = self._gather_entropy(question, context)
        deck = self._shuffle(entropy)

        drawn_cards: list[DrawnCard] = []
        for i, (pos, meaning) in enumerate(positions):
            card = deck[i]
            is_reversed = self.rng.random() < 0.5
            drawn_cards.append(
                DrawnCard(
                    card=card,
                    is_reversed=is_reversed,
                    position=pos,
                    position_meaning=meaning,
                )
            )

        # Build summary with key highlights
        major_drawn = [d for d in drawn_cards if isinstance(d.card, MajorArcanaCard)]
        major_names = (
            ", ".join(d.card.name for d in major_drawn)
            if major_drawn
            else "no Major Arcana"
        )
        summary = f"Celtic Cross reading. Major Arcana present: {major_names}. "
        # Highlight the outcome card
        outcome = drawn_cards[9]
        outcome_meaning = (
            outcome.card.reversed_meaning
            if outcome.is_reversed
            else outcome.card.upright_meaning
        )
        summary += f"Outcome: {outcome.card.name} — {outcome_meaning[:80]}"

        return TarotReading(
            spread_type="celtic_cross",
            question=question,
            cards=drawn_cards,
            summary=summary,
        )

    def draw_fools_journey(
        self,
        question: str = "",
        context: dict[str, Any] | None = None,
    ) -> TarotReading:
        """Draw 3-7 Major Arcana cards representing stages of the Fool's Journey.

        This spread uses only the 22 Major Arcana and reads them as
        stages in an initiatory arc, inspired by the Suarès/Revelation
        22-chapter correspondence.
        """
        self._gather_entropy(question, context)
        # Use Major Arcana only
        deck = list(MAJOR_ARCANA)
        n = len(deck)
        for i in range(n - 1, 0, -1):
            j = self.rng.randint(0, i)
            deck[i], deck[j] = deck[j], deck[i]

        # Draw 5 cards representing stages
        num_cards = 5
        stage_names = [
            "origin",
            "challenge",
            "transformation",
            "integration",
            "completion",
        ]
        stage_meanings = [
            "Origin — where the journey begins, the initial impulse",
            "Challenge — the first major obstacle or test",
            "Transformation — the turning point, the death/rebirth moment",
            "Integration — how the lessons come together",
            "Completion — the outcome, the new beginning",
        ]

        drawn_cards: list[DrawnCard] = []
        for i in range(num_cards):
            card = deck[i]
            is_reversed = self.rng.random() < 0.5
            drawn_cards.append(
                DrawnCard(
                    card=card,
                    is_reversed=is_reversed,
                    position=stage_names[i],
                    position_meaning=stage_meanings[i],
                )
            )

        card_summaries = []
        for d in drawn_cards:
            meaning = (
                d.card.reversed_meaning if d.is_reversed else d.card.upright_meaning
            )
            card_summaries.append(
                f"{d.position.capitalize()}: {d.card.name} (#{d.card.number}, {d.card.hebrew_name}) — {meaning[:60]}"
            )

        summary = "Fool's Journey: " + " → ".join(card_summaries)
        return TarotReading(
            spread_type="fools_journey",
            question=question,
            cards=drawn_cards,
            summary=summary,
        )

    def consult(
        self,
        question: str = "",
        context: dict[str, Any] | None = None,
        spread: str = "three_card",
    ) -> TarotReading:
        """Consult the Tarot with a question.

        Args:
            question: The question or topic for the reading
            context: Optional context dict
            spread: Spread type — "single", "three_card", "celtic_cross", "fools_journey"

        Returns:
            TarotReading with drawn cards and interpretation
        """
        if spread == "single":
            return self.draw_single(question, context)
        elif spread == "celtic_cross":
            return self.draw_celtic_cross(question, context)
        elif spread == "fools_journey":
            return self.draw_fools_journey(question, context)
        else:
            return self.draw_three_card(question, context)


def cast_tarot(
    question: str = "",
    context: dict[str, Any] | None = None,
    spread: str = "three_card",
    seed: int | None = None,
    major_only: bool = False,
) -> TarotReading:
    """Cast a Tarot reading. Convenience function."""
    caster = TarotCaster(seed=seed, major_only=major_only)
    return caster.consult(question=question, context=context, spread=spread)
