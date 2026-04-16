"""WhiteMagic Mojo/MAX Accelerators"""
__version__ = '17.0.0'

from .embeddings import EmbeddingKernel
from .hot_path import HotPathOptimizer
from .grimoire import GrimoireKernel
from .context_router import ContextRouter

__all__ = [
    'EmbeddingKernel',
    'HotPathOptimizer',
    'GrimoireKernel',
    'ContextRouter',
]
