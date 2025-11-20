"""Prevention Systems

Proactive systems to prevent common issues before they occur.
Winter of Yin focus: prevent drift, not just fix it.
"""

from .version_sync import VersionSyncSystem
from .doc_guardian import DocumentationGuardian
from .test_guardian import TestGuardian

__all__ = [
    'VersionSyncSystem',
    'DocumentationGuardian', 
    'TestGuardian'
]
