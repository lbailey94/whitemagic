"""Sangha - Collective Consciousness Module"""

from whitemagic.sangha.collective_memory import CollectiveMemory, get_collective
from whitemagic.sangha.pattern_federation import PatternFederation, get_federation
from whitemagic.sangha.session_handoff import SessionHandoff, get_handoff
from whitemagic.sangha.community_dharma import CommunityDharma, get_community_dharma

__all__ = [
    'CollectiveMemory',
    'PatternFederation',
    'SessionHandoff',
    'CommunityDharma',
    'get_collective',
    'get_federation',
    'get_handoff',
    'get_community_dharma',
]

__version__ = "2.6.5"
