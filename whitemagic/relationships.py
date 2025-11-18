"""Memory relationship management."""

from enum import Enum
from typing import Dict, List, Optional


class RelationType(str, Enum):
    """Types of relationships between memories."""

    DEPENDS_ON = "depends_on"  # This memory requires understanding of related
    IMPLEMENTS = "implements"  # Related is implementation of this design
    SUPERSEDES = "supersedes"  # This replaces/updates related
    INFORMED_BY = "informed_by"  # Related influenced this
    RELATES_TO = "relates_to"  # General connection
    CONTRADICTS = "contradicts"  # Conflicting information


def add_relationship(
    frontmatter: Dict,
    related_filename: str,
    rel_type: RelationType,
    description: Optional[str] = None,
) -> Dict:
    """Add a relationship to memory frontmatter.

    Args:
        frontmatter: Memory frontmatter dict
        related_filename: Filename of related memory
        rel_type: Type of relationship
        description: Optional description

    Returns:
        Updated frontmatter dict
    """
    if "related_to" not in frontmatter:
        frontmatter["related_to"] = []

    # Check if relationship already exists
    for rel in frontmatter["related_to"]:
        if rel.get("filename") == related_filename and rel.get("type") == rel_type.value:
            # Update existing
            if description:
                rel["description"] = description
            return frontmatter

    # Add new relationship
    relationship = {
        "filename": related_filename,
        "type": rel_type.value,  # Convert enum to string
    }
    if description:
        relationship["description"] = description

    frontmatter["related_to"].append(relationship)
    return frontmatter


def get_relationships(frontmatter: Dict, rel_type: Optional[RelationType] = None) -> List[Dict]:
    """Get relationships from frontmatter.

    Args:
        frontmatter: Memory frontmatter dict
        rel_type: Optional filter by relationship type

    Returns:
        List of relationship dicts
    """
    relationships = frontmatter.get("related_to", [])

    if rel_type:
        return [r for r in relationships if r.get("type") == rel_type.value]

    return relationships


def remove_relationship(
    frontmatter: Dict, related_filename: str, rel_type: Optional[RelationType] = None
) -> Dict:
    """Remove relationship(s) from frontmatter.

    Args:
        frontmatter: Memory frontmatter dict
        related_filename: Filename of related memory
        rel_type: Optional filter by type (removes all if None)

    Returns:
        Updated frontmatter dict
    """
    if "related_to" not in frontmatter:
        return frontmatter

    relationships = frontmatter["related_to"]

    if rel_type:
        # Remove specific type only
        frontmatter["related_to"] = [
            r
            for r in relationships
            if not (r.get("filename") == related_filename and r.get("type") == rel_type.value)
        ]
    else:
        # Remove all relationships to this file
        frontmatter["related_to"] = [
            r for r in relationships if r.get("filename") != related_filename
        ]

    return frontmatter
