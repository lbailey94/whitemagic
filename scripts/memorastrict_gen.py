#!/usr/bin/env python3
"""MemoraStrict scenario generator — pure Python, no LLM.

Generates parameterized life-simulation scenarios with deterministic ground
truth for 10 test categories (T1–T10). Output is JSON compatible with the
existing longmemeval_bench.py harness format, extended with MemoraStrict
metadata.

Usage:
    python3 scripts/memorastrict_gen.py --seeds 5 --output benchmarks/data/memorastrict/
    python3 scripts/memorastrict_gen.py --categories T1 T4 T9 --seeds 3
    python3 scripts/memorastrict_gen.py --list-categories
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

# ─── Data Pools ──────────────────────────────────────────────────────────────

NAMES = [
    "Jordan", "Casey", "Riley", "Morgan", "Avery", "Quinn", "Blake",
    "Sam", "Drew", "Reese", "Taylor", "Cameron", "Skylar", "Harper",
    "Phoenix", "Rowan", "Sage", "Wren", "Finley", "Emerson",
]

OCCUPATIONS = [
    "data scientist", "software engineer", "graphic designer", "teacher",
    "nurse", "marketing manager", "research analyst", "product manager",
    "physical therapist", "architect", "journalist", "chef",
]

CITIES = [
    "Boston", "Austin", "Seattle", "Denver", "Portland", "Chicago",
    "Nashville", "Atlanta", "Phoenix", "Minneapolis", "Boulder", "Miami",
]

COFFEE_TYPES = ["light roast", "dark roast", "cold brew", "espresso", "latte", "oat milk latte"]
PROGRAMMING_LANGUAGES = ["Python", "Rust", "TypeScript", "Go", "JavaScript", "Ruby", "Kotlin"]
HOBBIES = ["rock climbing", "watercolor painting", "board games", "bird watching",
           "sourdough baking", "film photography", "pottery", "geocaching"]
MUSIC_GENRES = ["jazz", "indie rock", "classical", "electronic", "folk", "hip hop", "ambient"]
FOOD_CUISINES = ["Thai", "Mexican", "Italian", "Japanese", "Ethiopian", "Korean", "Lebanese"]
SPORTS = ["running", "cycling", "swimming", "yoga", "hiking", "tennis", "soccer"]
PETS = ["cat", "dog", "rabbit", "parrot", "fish", "hamster"]
BOOK_GENRES = ["mystery", "sci-fi", "biography", "cookbooks", "history", "fantasy"]
TRANSPORT = ["bus", "subway", "biking", "walking", "car", "scooter"]

# Topics for noise turns (unrelated to signal topics)
NOISE_TOPICS = [
    "weather", "traffic", "weekend plans", "tv shows", "movies",
    "news", "sleep", "dreams", "coffee shop reviews", "local events",
    "home repairs", "gardening", "laundry", "shopping", "haircuts",
    "dentist appointments", "package delivery", "neighbors", "commute",
    "lunch ideas", "birthdays", "holidays", "gifts", "emails",
]

# Activities for noise turns
NOISE_ACTIVITIES = [
    "went for a walk in the park", "tried a new recipe for dinner",
    "watched a documentary about nature", "cleaned the apartment",
    "visited a friend", "went to the gym", "read a few chapters of a book",
    "organized my closet", "called my mom", "did some laundry",
    "went grocery shopping", "fixed a leaky faucet", "repotted my plants",
    "took a nap", "listened to a podcast", "browsed the internet",
    "played video games", "went to the library", "cooked breakfast",
    "watered the garden", "replied to emails", "did some stretching",
]

# Signal topic pools (used for fact generation)
SIGNAL_TOPICS = {
    "coffee": COFFEE_TYPES,
    "programming_language": PROGRAMMING_LANGUAGES,
    "hobby": HOBBIES,
    "music": MUSIC_GENRES,
    "food": FOOD_CUISINES,
    "sport": SPORTS,
    "pet": PETS,
    "book_genre": BOOK_GENRES,
    "transport": TRANSPORT,
}

ALL_TEST_CATEGORIES = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10"]


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class PreferenceChange:
    topic: str
    values: list[str]  # ordered list of values over time
    change_sessions: list[int]  # sessions where value changes


@dataclass
class Persona:
    name: str
    age: int
    occupation: str
    location: str
    preferences: list[PreferenceChange] = field(default_factory=list)


@dataclass
class Fact:
    id: str
    content: str
    category: str
    session_idx: int
    turn_idx: int
    valid_from: int
    valid_until: int | None
    superseded_by: str | None
    mention_count: int = 1  # for T5 consolidation


@dataclass
class Turn:
    role: str  # "user" or "assistant"
    content: str
    has_answer: bool = False
    fact_id: str | None = None
    is_signal: bool = False


@dataclass
class Session:
    id: str
    index: int
    timestamp: str
    turns: list[Turn] = field(default_factory=list)


@dataclass
class Question:
    id: str
    test_category: str
    question: str
    answer: str
    answer_session_ids: list[str]
    verification_type: str  # "exact", "set", "numeric", "count", "abstention", "supersession"
    answer_facts: list[str] = field(default_factory=list)  # fact IDs
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scenario:
    persona: Persona
    sessions: list[Session]
    facts: list[Fact]
    questions: list[Question]
    seed: int
    config: dict[str, Any]


# ─── Noise Turn Generators ───────────────────────────────────────────────────

def gen_noise_turn(rng: random.Random, persona: Persona) -> Turn:
    """Generate a noise turn (small talk, opinions, unrelated activities)."""
    style = rng.randint(0, 3)
    if style == 0:
        # Activity report
        activity = rng.choice(NOISE_ACTIVITIES)
        content = f"I {activity} yesterday."
    elif style == 1:
        # Opinion / small talk
        topic = rng.choice(NOISE_TOPICS)
        templates = [
            f"The {topic} has been pretty crazy lately.",
            f"I was thinking about {topic} the other day.",
            f"My friend was telling me about {topic}.",
            f"I can't stop thinking about {topic}.",
        ]
        content = rng.choice(templates)
    elif style == 2:
        # Question to assistant
        topic = rng.choice(NOISE_TOPICS)
        content = f"Can you help me with something about {topic}?"
    else:
        # Casual mention with some entity overlap potential
        activity = rng.choice(NOISE_ACTIVITIES)
        topic = rng.choice(NOISE_TOPICS)
        content = f"I {activity} and then thought about {topic}."
    return Turn(role="user", content=content)


def gen_assistant_turn(rng: random.Random, user_turn: Turn) -> Turn:
    """Generate a minimal assistant response."""
    responses = [
        "That sounds great!",
        "Interesting, tell me more.",
        "I can help with that.",
        "Thanks for sharing.",
        "Good to know!",
        "Sounds like a productive day.",
        "I understand. What else?",
        "That's really interesting.",
    ]
    return Turn(role="assistant", content=rng.choice(responses))


def gen_adversarial_distractor(
    rng: random.Random,
    query_keywords: list[str],
    answer_keywords: list[str],
    topic: str,
) -> Turn:
    """Generate a distractor turn with HIGHER keyword overlap than the answer.

    The distractor mentions the query keywords more prominently than the
    answer turn does, making BM25 likely to rank it higher.
    """
    # Build a sentence that densely packs query keywords
    kw = query_keywords[:3]  # use top 3 query keywords
    templates = [
        f"I was wondering about my {' '.join(kw)} situation lately.",
        f"My {' '.join(kw)} has been on my mind recently.",
        f"I need to figure out my {' '.join(kw)} plans soon.",
        f"Someone asked me about my {' '.join(kw)} preferences the other day.",
        f"I've been reading a lot about {' '.join(kw)} lately.",
        f"My {' '.join(kw)} options are getting complicated.",
    ]
    content = rng.choice(templates)
    # Add extra keyword density
    if rng.random() < 0.5:
        content += f" The {' '.join(kw[:2])} thing is really important to me."
    return Turn(role="user", content=content)


# ─── Signal Turn Generators ──────────────────────────────────────────────────

def gen_preference_statement(
    rng: random.Random, topic: str, value: str, persona: Persona
) -> str:
    """Generate a natural preference statement."""
    templates = [
        f"My favorite {topic} is {value}.",
        f"I really love {value} when it comes to {topic}.",
        f"I've been really into {value} lately for {topic}.",
        f"For {topic}, I always go with {value}.",
        f"I prefer {value} for my {topic}.",
    ]
    return rng.choice(templates)


def gen_preference_change_statement(
    rng: random.Random, topic: str, old_value: str, new_value: str
) -> str:
    """Generate a preference change statement."""
    templates = [
        f"I've actually switched from {old_value} to {new_value} for {topic}.",
        f"I used to prefer {old_value} but now I'm all about {new_value} for {topic}.",
        f"I've changed my mind about {topic} — I now prefer {new_value} over {old_value}.",
        f"Recently I switched to {new_value} for {topic}. I used to be into {old_value}.",
    ]
    return rng.choice(templates)


def gen_fact_statement(
    rng: random.Random, template_vars: dict[str, str]
) -> str:
    """Generate a factual statement from template variables."""
    template = rng.choice(template_vars["templates"])
    return template.format(**template_vars)


def gen_contradiction_statement(
    rng: random.Random, topic: str, old_value: str, new_value: str
) -> str:
    """Generate a statement that contradicts a previous fact."""
    templates = [
        f"Actually, I've started eating {new_value} again. I know I said I was {old_value} but I changed my mind.",
        f"I had an amazing {new_value} dinner last night. I'm not really {old_value} anymore.",
        f"I've been eating {new_value} a lot lately. Being {old_value} was just a phase.",
    ]
    return rng.choice(templates)


# ─── Persona Generator ───────────────────────────────────────────────────────

def gen_persona(rng: random.Random, num_prefs: int = 3) -> Persona:
    name = rng.choice(NAMES)
    age = rng.randint(25, 40)
    occupation = rng.choice(OCCUPATIONS)
    location = rng.choice(CITIES)

    preferences: list[PreferenceChange] = []
    available_topics = rng.sample(list(SIGNAL_TOPICS.keys()), min(num_prefs, len(SIGNAL_TOPICS)))

    for topic in available_topics:
        values = rng.sample(SIGNAL_TOPICS[topic], min(3, len(SIGNAL_TOPICS[topic])))
        # Schedule changes across sessions
        num_changes = len(values) - 1
        if num_changes == 0:
            change_sessions = []
        elif num_changes == 1:
            change_sessions = [rng.randint(5, 15)]
        else:
            change_sessions = sorted(rng.sample(range(4, 20), num_changes))

        preferences.append(PreferenceChange(
            topic=topic,
            values=values,
            change_sessions=change_sessions,
        ))

    return Persona(
        name=name, age=age, occupation=occupation, location=location,
        preferences=preferences,
    )


# ─── Session Generator ───────────────────────────────────────────────────────

def gen_sessions(
    rng: random.Random,
    persona: Persona,
    num_sessions: int = 20,
    turns_per_session: tuple[int, int] = (10, 25),
    noise_ratio: float = 0.8,
) -> list[Session]:
    """Generate sessions with controlled noise/signal ratio.

    Signal turns are generated from persona preferences and inserted at
    scheduled sessions. The rest are noise.
    """
    sessions: list[Session] = []
    base_day = 1

    for si in range(num_sessions):
        sid = f"session_{si+1:03d}"
        num_turns = rng.randint(*turns_per_session)
        session = Session(id=sid, index=si, timestamp=f"2026-0{1 + si // 30:02d}-{1 + (si % 30):02d}")

        # Determine which preferences change in this session
        active_prefs: list[tuple[str, str, int]] = []  # (topic, current_value, value_idx)
        for pref in persona.preferences:
            value_idx = 0
            for cs in pref.change_sessions:
                if si >= cs:
                    value_idx += 1
            current_value = pref.values[value_idx]
            active_prefs.append((pref.topic, current_value, value_idx))

        # Generate turns
        signal_turns_needed = max(1, int(num_turns * (1 - noise_ratio)))
        signal_positions = rng.sample(range(num_turns), min(signal_turns_needed, num_turns))

        for ti in range(num_turns):
            if ti in signal_positions and active_prefs:
                # Pick a preference to mention
                topic, value, vidx = rng.choice(active_prefs)
                # Check if this session is a change session
                pref = next(p for p in persona.preferences if p.topic == topic)
                is_change = si in pref.change_sessions

                if is_change and vidx > 0:
                    old_value = pref.values[vidx - 1]
                    content = gen_preference_change_statement(rng, topic, old_value, value)
                else:
                    content = gen_preference_statement(rng, topic, value, persona)

                turn = Turn(role="user", content=content, is_signal=True)
                session.turns.append(turn)
            else:
                turn = gen_noise_turn(rng, persona)
                session.turns.append(turn)

            # Add assistant response every other turn
            if ti % 2 == 0 and ti < num_turns - 1:
                asst = gen_assistant_turn(rng, session.turns[-1])
                session.turns.append(asst)

        sessions.append(session)
        base_day += rng.randint(3, 14)  # days between sessions

    return sessions


# ─── Fact Tracker ────────────────────────────────────────────────────────────

def extract_facts_from_sessions(
    sessions: list[Session], persona: Persona
) -> list[Fact]:
    """Extract ground-truth facts from sessions based on persona preferences."""
    facts: list[Fact] = []
    fact_counter = 0

    for pref in persona.preferences:
        # Track when each value becomes active
        value_start_sessions = [0] + pref.change_sessions
        for vi, value in enumerate(pref.values):
            valid_from = value_start_sessions[vi]
            valid_until = value_start_sessions[vi + 1] if vi + 1 < len(pref.values) else None
            superseded_by = f"fact_{fact_counter + 2}" if vi + 1 < len(pref.values) else None

            # Find the session and turn where this value is first stated
            session_idx = valid_from
            turn_idx = 0
            for si in range(valid_from, len(sessions)):
                for ti, turn in enumerate(sessions[si].turns):
                    if turn.is_signal and value in turn.content and pref.topic in turn.content:
                        session_idx = si
                        turn_idx = ti
                        break
                else:
                    continue
                break

            fact = Fact(
                id=f"fact_{fact_counter}",
                content=f"{persona.name}'s {pref.topic} preference: {value}",
                category=pref.topic,
                session_idx=session_idx,
                turn_idx=turn_idx,
                valid_from=valid_from,
                valid_until=valid_until,
                superseded_by=superseded_by,
            )
            facts.append(fact)
            fact_counter += 1

    return facts


# ─── Question Generators per Test Category ───────────────────────────────────

def gen_questions_T1_temporal_supersession(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T1: Temporal Supersession — prefer current facts over old ones."""
    questions: list[Question] = []

    for pref in persona.preferences:
        if len(pref.values) < 2:
            continue

        # Query for current value
        current_value = pref.values[-1]
        old_value = pref.values[0]
        change_session = pref.change_sessions[-1]

        # Find the session where the new value is stated
        answer_sid = f"session_{change_session + 1:03d}"

        q = Question(
            id=f"T1_{pref.topic}",
            test_category="T1",
            question=f"What's my current favorite {pref.topic.replace('_', ' ')}?",
            answer=current_value,
            answer_session_ids=[answer_sid],
            verification_type="supersession",
            answer_facts=[f.id for f in facts if f.category == pref.topic and f.valid_until is None],
            metadata={
                "old_value": old_value,
                "current_value": current_value,
                "change_session": change_session,
            },
        )
        questions.append(q)

    return questions


def gen_questions_T2_abstention(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T2: Abstention — correctly return 'I don't know' for unknown topics."""
    questions: list[Question] = []

    # Topics never discussed
    discussed_topics = {p.topic for p in persona.preferences}
    all_topics = set(SIGNAL_TOPICS.keys())
    undiscussed_topics = all_topics - discussed_topics

    # Add some topics outside our signal pool entirely
    fully_unknown = ["podcast", "video_game", "car_model", "phone_brand", "shoe_brand",
                     "wine", "tea", "energy_drink", "snack", "dessert"]

    for topic in list(undiscussed_topics)[:2]:
        q = Question(
            id=f"T2_unknown_{topic}",
            test_category="T2",
            question=f"What's my favorite {topic.replace('_', ' ')}?",
            answer="I don't know",
            answer_session_ids=[],
            verification_type="abstention",
            metadata={"topic": topic, "reason": "topic_never_discussed"},
        )
        questions.append(q)

    for topic in rng.sample(fully_unknown, 2):
        q = Question(
            id=f"T2_novel_{topic}",
            test_category="T2",
            question=f"What's my favorite {topic.replace('_', ' ')}?",
            answer="I don't know",
            answer_session_ids=[],
            verification_type="abstention",
            metadata={"topic": topic, "reason": "topic_completely_novel"},
        )
        questions.append(q)

    # Also add a true positive (discussed topic) for TPR measurement
    if persona.preferences:
        pref = persona.preferences[0]
        current_val = pref.values[-1]
        answer_sids = []
        for si, session in enumerate(sessions):
            for turn in session.turns:
                if turn.is_signal and current_val in turn.content and pref.topic in turn.content:
                    answer_sids.append(session.id)
                    break

        q = Question(
            id=f"T2_positive_{pref.topic}",
            test_category="T2",
            question=f"What's my favorite {pref.topic.replace('_', ' ')}?",
            answer=current_val,
            answer_session_ids=answer_sids[:1],
            verification_type="exact",
            metadata={"topic": pref.topic, "reason": "true_positive_control"},
        )
        questions.append(q)

    return questions


def gen_questions_T3_multi_hop(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T3: Multi-Hop — connect facts across sessions."""
    questions: list[Question] = []

    # Generate synthetic multi-hop scenarios
    items = [
        ("bookshelf", "IKEA", "assemble", "4 hours", "assemble the thing I bought from IKEA"),
        ("desk", "Wayfair", "put together", "3 hours", "put together the thing I bought from Wayfair"),
        ("wardrobe", "Target", "assemble", "2 hours", "assemble the thing I bought from Target"),
    ]

    for item, store, action, duration, query_phrase in items:
        # Place fact A in an early session, fact B in a later session
        session_a = rng.randint(2, 8)
        session_b = rng.randint(session_a + 3, min(session_a + 10, len(sessions) - 1))
        # Distractor session between them
        session_d = rng.randint(session_a + 1, session_b - 1)

        # Insert fact A
        fact_a_content = f"I bought a {item} from {store}."
        # Insert fact B
        fact_b_content = f"It took me {duration} to {action} the {item}."
        # Insert distractor
        distractor_content = f"I helped my friend {action} her {store} desk last weekend."

        # Find or create turns in those sessions
        sid_a = sessions[session_a].id
        sid_b = sessions[session_b].id

        # Add turns to sessions (we'll mark them as signal)
        sessions[session_a].turns.append(Turn(
            role="user", content=fact_a_content, has_answer=True, is_signal=True,
        ))
        sessions[session_b].turns.append(Turn(
            role="user", content=fact_b_content, has_answer=True, is_signal=True,
        ))
        sessions[session_d].turns.append(Turn(
            role="user", content=distractor_content, is_signal=True,
        ))

        q = Question(
            id=f"T3_{item}",
            test_category="T3",
            question=f"How long did it take to {query_phrase}?",
            answer=duration,
            answer_session_ids=[sid_a, sid_b],
            verification_type="exact",
            metadata={
                "fact_a": fact_a_content,
                "fact_b": fact_b_content,
                "distractor": distractor_content,
                "fact_a_session": sid_a,
                "fact_b_session": sid_b,
            },
        )
        questions.append(q)

    return questions


def gen_questions_T4_distractor_resistance(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T4: Distractor Resistance — signal buried in 50+ noise turns."""
    questions: list[Question] = []

    allergies = [
        ("shellfish", "I'm allergic to shellfish.", "What food allergy do I have?"),
        ("peanuts", "I found out I'm allergic to peanuts.", "What food allergy do I have?"),
        ("gluten", "I have a gluten intolerance.", "What food allergy do I have?"),
    ]

    for allergen, signal_text, query in allergies:
        # Pick a session and bury the signal in 50+ cooking-related noise turns
        target_session = rng.randint(5, len(sessions) - 5)
        session = sessions[target_session]

        # Generate 50+ cooking noise turns with keyword overlap
        cooking_noise = [
            "I made a great shellfish pasta yesterday.",
            "My friend has a peanut allergy, it's really serious.",
            "I love cooking Thai food with peanuts.",
            "I tried a new shellfish recipe last weekend.",
            "I'm thinking about making a peanut sauce for dinner.",
            "I had shellfish for the first time at a restaurant.",
            "My coworker brought peanut cookies to the office.",
            "I watched a cooking show about shellfish preparation.",
            "I bought some peanut butter for baking.",
            "Shellfish is supposed to be really healthy, right?",
            "I'm making a peanut stir-fry tonight.",
            "I read an article about shellfish sustainability.",
            "I tried making peanut soup, it was interesting.",
            "I found a great shellfish market nearby.",
            "My neighbor is allergic to peanuts too.",
            "I cooked shellfish for my family dinner.",
            "I made peanut brittle for the holidays.",
            "I'm looking for a good shellfish restaurant.",
            "I made a peanut dressing for my salad.",
            "I heard shellfish can cause allergic reactions in some people.",
        ]

        # Insert signal at a random position
        signal_pos = rng.randint(10, 30)
        for i, noise_text in enumerate(cooking_noise * 3):  # ~60 noise turns
            if i == signal_pos:
                session.turns.append(Turn(
                    role="user", content=signal_text, has_answer=True, is_signal=True,
                ))
            session.turns.append(Turn(role="user", content=noise_text))
            if i % 3 == 0:
                session.turns.append(Turn(role="assistant", content="Interesting!"))

        q = Question(
            id=f"T4_{allergen}",
            test_category="T4",
            question=query,
            answer=allergen,
            answer_session_ids=[session.id],
            verification_type="exact",
            metadata={
                "signal_text": signal_text,
                "noise_turn_count": len(cooking_noise) * 3,
                "signal_position": signal_pos,
            },
        )
        questions.append(q)

    return questions


def gen_questions_T5_consolidation_benefit(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T5: Consolidation Benefit — repeated mention improves retrieval."""
    questions: list[Question] = []

    # Pick two facts: one mentioned once, one mentioned 5 times
    topics = rng.sample(list(SIGNAL_TOPICS.keys()), 2)
    single_value = rng.choice(SIGNAL_TOPICS[topics[0]])
    multi_value = rng.choice(SIGNAL_TOPICS[topics[1]])

    # Single-mention fact
    single_session = rng.randint(0, 5)
    single_content = gen_preference_statement(rng, topics[0], single_value, persona)
    sessions[single_session].turns.append(Turn(
        role="user", content=single_content, has_answer=True, is_signal=True,
    ))

    # Multi-mention fact (5 times across different sessions)
    multi_sessions = rng.sample(range(0, len(sessions)), 5)
    for ms in multi_sessions:
        multi_content = gen_preference_statement(rng, topics[1], multi_value, persona)
        sessions[ms].turns.append(Turn(
            role="user", content=multi_content, has_answer=True, is_signal=True,
        ))

    questions.append(Question(
        id=f"T5_single_{topics[0]}",
        test_category="T5",
        question=f"What's my favorite {topics[0].replace('_', ' ')}?",
        answer=single_value,
        answer_session_ids=[sessions[single_session].id],
        verification_type="exact",
        metadata={"mention_count": 1, "topic": topics[0]},
    ))

    questions.append(Question(
        id=f"T5_multi_{topics[1]}",
        test_category="T5",
        question=f"What's my favorite {topics[1].replace('_', ' ')}?",
        answer=multi_value,
        answer_session_ids=[sessions[multi_sessions[0]].id],
        verification_type="exact",
        metadata={"mention_count": 5, "topic": topics[1]},
    ))

    return questions


def gen_questions_T6_memory_budget(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T6: Memory Budget — recall under storage constraints.

    Generates the same questions as T1 but with budget metadata.
    The evaluation harness will run with different budget fractions.
    """
    base_questions = gen_questions_T1_temporal_supersession(rng, persona, sessions, facts)
    for q in base_questions:
        q.id = q.id.replace("T1_", "T6_")
        q.test_category = "T6"
        q.metadata["budget_fractions"] = [1.0, 0.75, 0.5, 0.25]
    return base_questions


def gen_questions_T7_scale_stress(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T7: Scale Stress — recall at different haystack sizes.

    Generates questions with metadata indicating the target scale. The
    evaluation harness can use this metadata to generate appropriately-sized
    haystacks at query time. Since all questions share one haystack in the
    current format, T7 questions test retrieval at the base haystack size
    (~766 turns) and the metadata records what scale was intended.

    For true scale testing, generate separate scenarios with larger
    num_sessions parameter.
    """
    questions: list[Question] = []

    if not persona.preferences:
        return questions

    pref = persona.preferences[0]
    current_value = pref.values[-1]

    # Find the answer session
    answer_sids = []
    for si, session in enumerate(sessions):
        for turn in session.turns:
            if turn.is_signal and current_value in turn.content and pref.topic in turn.content:
                answer_sids.append(session.id)
                break

    current_turn_count = sum(len(s.turns) for s in sessions)

    for scale in [1000, 10000, 50000, 100000]:
        q = Question(
            id=f"T7_scale_{scale}",
            test_category="T7",
            question=f"What's my favorite {pref.topic.replace('_', ' ')}?",
            answer=current_value,
            answer_session_ids=answer_sids[:1],
            verification_type="exact",
            metadata={
                "target_turns": scale,
                "actual_turns": current_turn_count,
                "topic": pref.topic,
                "note": "Scale testing requires separate scenario generation with larger num_sessions",
            },
        )
        questions.append(q)

    return questions


def gen_questions_T8_contradiction_detection(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T8: Contradiction Detection — identify conflicting memories."""
    questions: list[Question] = []

    contradictions = [
        ("vegetarian", "steak", "eats", "Do I have any dietary restrictions?"),
        ("vegan", "cheese", "eats", "Do I have any dietary restrictions?"),
        ("teetotaler", "wine", "drinks", "Do I drink alcohol?"),
    ]

    for old_label, new_item, verb, query in contradictions:
        session_old = rng.randint(2, 8)
        session_new = rng.randint(session_old + 3, min(session_old + 8, len(sessions) - 1))

        old_content = f"I'm {old_label} now. I decided to stop eating animal products."
        new_content = gen_contradiction_statement(rng, old_label, old_label, new_item)

        sessions[session_old].turns.append(Turn(
            role="user", content=old_content, has_answer=True, is_signal=True,
        ))
        sessions[session_new].turns.append(Turn(
            role="user", content=new_content, has_answer=True, is_signal=True,
        ))

        q = Question(
            id=f"T8_{old_label}_{new_item}",
            test_category="T8",
            question=query,
            answer=f"CONFLICT: was {old_label}, now {verb} {new_item}",
            answer_session_ids=[sessions[session_old].id, sessions[session_new].id],
            verification_type="set",
            metadata={
                "old_fact": old_content,
                "new_fact": new_content,
                "old_session": sessions[session_old].id,
                "new_session": sessions[session_new].id,
                "conflict_type": "dietary_contradiction",
            },
        )
        questions.append(q)

    return questions


def gen_questions_T9_preference_drift(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T9: Preference Drift — track changes over time."""
    questions: list[Question] = []

    for pref in persona.preferences:
        if len(pref.values) < 3:
            continue

        # Current value
        current = pref.values[-1]
        # Previous value (before last change)
        previous = pref.values[-2]
        # Number of transitions
        num_transitions = len(pref.change_sessions)

        # Find answer sessions
        current_sid = f"session_{pref.change_sessions[-1] + 1:03d}"
        previous_sid = f"session_{pref.change_sessions[-2] + 1:03d}" if len(pref.change_sessions) >= 2 else "session_001"

        # Q1: current value
        questions.append(Question(
            id=f"T9_current_{pref.topic}",
            test_category="T9",
            question=f"What's my current favorite {pref.topic.replace('_', ' ')}?",
            answer=current,
            answer_session_ids=[current_sid],
            verification_type="exact",
            metadata={"drift_position": "current", "topic": pref.topic},
        ))

        # Q2: previous value
        questions.append(Question(
            id=f"T9_previous_{pref.topic}",
            test_category="T9",
            question=f"What was my favorite {pref.topic.replace('_', ' ')} before I switched?",
            answer=previous,
            answer_session_ids=[previous_sid],
            verification_type="exact",
            metadata={"drift_position": "previous", "topic": pref.topic},
        ))

        # Q3: transition count
        questions.append(Question(
            id=f"T9_count_{pref.topic}",
            test_category="T9",
            question=f"How many times have I changed my mind about {pref.topic.replace('_', ' ')}?",
            answer=str(num_transitions),
            answer_session_ids=[],
            verification_type="count",
            metadata={"drift_position": "count", "topic": pref.topic, "expected_count": num_transitions},
        ))

    return questions


def gen_questions_T10_cross_session_synthesis(
    rng: random.Random, persona: Persona, sessions: list[Session], facts: list[Fact]
) -> list[Question]:
    """T10: Cross-Session Synthesis — combine facts from multiple sessions."""
    questions: list[Question] = []

    # Generate a learning journey: start → project → job
    skills = [
        ("Rust", "CLI tool", "systems engineer"),
        ("Go", "web API", "backend engineer"),
        ("TypeScript", "React app", "frontend engineer"),
    ]

    for skill, project, job in skills:
        s1 = rng.randint(2, 6)
        s2 = rng.randint(s1 + 3, s1 + 8)
        s3 = rng.randint(s2 + 3, min(s2 + 8, len(sessions) - 1))

        content1 = f"I started learning {skill}."
        content2 = f"I finished my first {skill} project, a {project}."
        content3 = f"I got a job as a {job} using {skill}."

        sessions[s1].turns.append(Turn(role="user", content=content1, has_answer=True, is_signal=True))
        sessions[s2].turns.append(Turn(role="user", content=content2, has_answer=True, is_signal=True))
        sessions[s3].turns.append(Turn(role="user", content=content3, has_answer=True, is_signal=True))

        # Compute time span (in sessions)
        span = s3 - s1

        q = Question(
            id=f"T10_{skill}",
            test_category="T10",
            question=f"How long did it take from starting {skill} to getting a job using it?",
            answer=f"{span} sessions",
            answer_session_ids=[sessions[s1].id, sessions[s2].id, sessions[s3].id],
            verification_type="numeric",
            metadata={
                "fact_a": content1,
                "fact_b": content2,
                "fact_c": content3,
                "start_session": sessions[s1].id,
                "end_session": sessions[s3].id,
                "session_span": span,
            },
        )
        questions.append(q)

    return questions


# ─── Question Generator Registry ─────────────────────────────────────────────

QUESTION_GENERATORS = {
    "T1": gen_questions_T1_temporal_supersession,
    "T2": gen_questions_T2_abstention,
    "T3": gen_questions_T3_multi_hop,
    "T4": gen_questions_T4_distractor_resistance,
    "T5": gen_questions_T5_consolidation_benefit,
    "T6": gen_questions_T6_memory_budget,
    "T7": gen_questions_T7_scale_stress,
    "T8": gen_questions_T8_contradiction_detection,
    "T9": gen_questions_T9_preference_drift,
    "T10": gen_questions_T10_cross_session_synthesis,
}


# ─── Scenario Generator ──────────────────────────────────────────────────────

def gen_scenario(
    seed: int,
    categories: list[str],
    num_sessions: int = 20,
    noise_ratio: float = 0.8,
) -> Scenario:
    """Generate a complete MemoraStrict scenario."""
    rng = random.Random(seed)

    persona = gen_persona(rng, num_prefs=4)
    sessions = gen_sessions(rng, persona, num_sessions=num_sessions, noise_ratio=noise_ratio)
    facts = extract_facts_from_sessions(sessions, persona)

    questions: list[Question] = []
    for cat in categories:
        gen_fn = QUESTION_GENERATORS.get(cat)
        if gen_fn:
            cat_questions = gen_fn(rng, persona, sessions, facts)
            questions.extend(cat_questions)

    return Scenario(
        persona=persona,
        sessions=sessions,
        facts=facts,
        questions=questions,
        seed=seed,
        config={
            "num_sessions": num_sessions,
            "noise_ratio": noise_ratio,
            "categories": categories,
        },
    )


# ─── JSON Output ─────────────────────────────────────────────────────────────

def scenario_to_bench_format(scenario: Scenario) -> list[dict[str, Any]]:
    """Convert scenario to JSON format compatible with longmemeval_bench.py."""
    # Build haystack sessions
    haystack_sessions: list[list[dict[str, Any]]] = []
    haystack_session_ids: list[str] = []

    for session in scenario.sessions:
        turns_data: list[dict[str, Any]] = []
        for turn in session.turns:
            turns_data.append({
                "content": turn.content,
                "role": turn.role,
                "has_answer": turn.has_answer,
            })
        haystack_sessions.append(turns_data)
        haystack_session_ids.append(session.id)

    # Build questions
    questions_data: list[dict[str, Any]] = []
    for q in scenario.questions:
        questions_data.append({
            "question_id": q.id,
            "question_type": q.test_category,
            "question": q.question,
            "answer": q.answer,
            "haystack_sessions": haystack_sessions,
            "haystack_session_ids": haystack_session_ids,
            # MemoraStrict extensions
            "test_category": q.test_category,
            "verification_type": q.verification_type,
            "answer_session_ids": q.answer_session_ids,
            "answer_facts": q.answer_facts,
            "metadata": q.metadata,
        })

    return questions_data


def scenario_to_full_json(scenario: Scenario) -> dict[str, Any]:
    """Full scenario JSON with persona, facts, and metadata."""
    return {
        "seed": scenario.seed,
        "config": scenario.config,
        "persona": {
            "name": scenario.persona.name,
            "age": scenario.persona.age,
            "occupation": scenario.persona.occupation,
            "location": scenario.persona.location,
            "preferences": [
                {
                    "topic": p.topic,
                    "values": p.values,
                    "change_sessions": p.change_sessions,
                }
                for p in scenario.persona.preferences
            ],
        },
        "facts": [
            {
                "id": f.id,
                "content": f.content,
                "category": f.category,
                "session_idx": f.session_idx,
                "turn_idx": f.turn_idx,
                "valid_from": f.valid_from,
                "valid_until": f.valid_until,
                "superseded_by": f.superseded_by,
                "mention_count": f.mention_count,
            }
            for f in scenario.facts
        ],
        "sessions": [
            {
                "id": s.id,
                "index": s.index,
                "timestamp": s.timestamp,
                "turns": [
                    {
                        "role": t.role,
                        "content": t.content,
                        "has_answer": t.has_answer,
                        "is_signal": t.is_signal,
                        "fact_id": t.fact_id,
                    }
                    for t in s.turns
                ],
            }
            for s in scenario.sessions
        ],
        "questions": [
            {
                "id": q.id,
                "test_category": q.test_category,
                "question": q.question,
                "answer": q.answer,
                "answer_session_ids": q.answer_session_ids,
                "verification_type": q.verification_type,
                "answer_facts": q.answer_facts,
                "metadata": q.metadata,
            }
            for q in scenario.questions
        ],
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MemoraStrict scenario generator"
    )
    parser.add_argument(
        "--seeds", type=int, default=5,
        help="Number of random seeds (default: 5)",
    )
    parser.add_argument(
        "--categories", nargs="+", default=ALL_TEST_CATEGORIES,
        help=f"Test categories to generate (default: all {ALL_TEST_CATEGORIES})",
    )
    parser.add_argument(
        "--num-sessions", type=int, default=20,
        help="Number of sessions per scenario (default: 20)",
    )
    parser.add_argument(
        "--noise-ratio", type=float, default=0.8,
        help="Fraction of noise turns (default: 0.8)",
    )
    parser.add_argument(
        "--output", type=str, default=os.path.join(REPO_ROOT, "benchmarks", "data", "memorastrict"),
        help="Output directory",
    )
    parser.add_argument(
        "--format", choices=["bench", "full", "both"], default="both",
        help="Output format: bench (compatible with longmemeval_bench.py), full (with metadata), or both",
    )
    parser.add_argument(
        "--list-categories", action="store_true",
        help="List all test categories and exit",
    )
    args = parser.parse_args()

    if args.list_categories:
        for cat in ALL_TEST_CATEGORIES:
            gen_fn = QUESTION_GENERATORS[cat]
            print(f"  {cat}: {gen_fn.__doc__.split('—')[0].strip()}")
        return

    # Validate categories
    invalid = set(args.categories) - set(ALL_TEST_CATEGORIES)
    if invalid:
        print(f"Error: unknown categories: {invalid}", file=sys.stderr)
        print(f"Valid: {ALL_TEST_CATEGORIES}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    total_questions = 0
    for seed in range(1, args.seeds + 1):
        scenario = gen_scenario(
            seed=seed,
            categories=args.categories,
            num_sessions=args.num_sessions,
            noise_ratio=args.noise_ratio,
        )

        if args.format in ("bench", "both"):
            bench_data = scenario_to_bench_format(scenario)
            bench_path = output_dir / f"bench_seed{seed}.json"
            bench_path.write_text(json.dumps(bench_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  Seed {seed}: {len(bench_data)} questions → {bench_path}")

        if args.format in ("full", "both"):
            full_data = scenario_to_full_json(scenario)
            full_path = output_dir / f"scenario_seed{seed}.json"
            full_path.write_text(json.dumps(full_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  Seed {seed}: full scenario → {full_path}")

        total_questions += len(scenario.questions)

    # Write a manifest
    manifest = {
        "seeds": list(range(1, args.seeds + 1)),
        "categories": args.categories,
        "num_sessions": args.num_sessions,
        "noise_ratio": args.noise_ratio,
        "total_questions": total_questions,
        "total_scenarios": args.seeds,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nGenerated {total_questions} questions across {args.seeds} scenarios.")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
