"""🌸 Garden Virtual Filesystem — Physical Organization Layer.

Provides a virtual directory structure organized by gardens,
allowing navigation by garden without physically moving files.

Architecture:
- Virtual paths: /garden/{garden_name}/{file_type}/...
- Physical paths remain unchanged
- Symlink-like resolution for tools
- Garden-aware file operations
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VirtualNode:
    """A node in the virtual garden filesystem."""

    virtual_path: str
    physical_path: str | None = None  # None for directories
    node_type: str = "directory"  # "directory" or "file"
    garden: str = ""
    children: dict[str, VirtualNode] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class GardenVirtualFS:
    """Virtual filesystem organized by gardens."""

    def __init__(self, root: Path, registry_path: Path | None = None):
        self.root = root
        self.registry_path = registry_path or root / "data" / "garden_file_registry.json"
        self._tree: VirtualNode | None = None
        self._garden_nodes: dict[str, VirtualNode] = {}
        self._loaded = False

    def build_tree(self, file_mappings: dict[str, Any]) -> VirtualNode:
        """Build the virtual filesystem tree from file mappings."""
        # Root node
        root_node = VirtualNode(virtual_path="/", node_type="directory")

        # Create garden nodes
        gardens_node = VirtualNode(virtual_path="/gardens", node_type="directory")
        root_node.children["gardens"] = gardens_node

        # Track all gardens
        gardens_seen: set[str] = set()

        for fp, mapping in file_mappings.items():
            garden = mapping.get("primary_garden", "mystery")
            file_type = mapping.get("file_type", "unknown")

            gardens_seen.add(garden)

            # Get or create garden node
            if garden not in self._garden_nodes:
                garden_node = VirtualNode(
                    virtual_path=f"/gardens/{garden}",
                    node_type="directory",
                    garden=garden,
                )
                garden_node.metadata = {
                    "gana": mapping.get("gana", ""),
                    "element": mapping.get("element", ""),
                    "quadrant": mapping.get("quadrant", ""),
                }
                gardens_node.children[garden] = garden_node
                self._garden_nodes[garden] = garden_node
            else:
                garden_node = self._garden_nodes[garden]

            # Get or create file type node
            if file_type not in garden_node.children:
                type_node = VirtualNode(
                    virtual_path=f"/gardens/{garden}/{file_type}",
                    node_type="directory",
                    garden=garden,
                )
                garden_node.children[file_type] = type_node
            else:
                type_node = garden_node.children[file_type]

            # Create file node
            file_name = Path(fp).name
            file_node = VirtualNode(
                virtual_path=f"/gardens/{garden}/{file_type}/{file_name}",
                physical_path=fp,
                node_type="file",
                garden=garden,
                metadata={
                    "loc_count": mapping.get("loc_count", 0),
                    "confidence": mapping.get("confidence", 0),
                    "gana_tool": mapping.get("gana_tool", ""),
                },
            )
            type_node.children[file_name] = file_node

        # Create systems node
        systems_node = VirtualNode(virtual_path="/systems", node_type="directory")
        root_node.children["systems"] = systems_node

        # Load system mappings if available
        system_registry = self.root / "data" / "garden_system_registry.json"
        if system_registry.exists():
            system_data = json.loads(system_registry.read_text())
            for system_id, sys_mapping in system_data.items():
                system_node = VirtualNode(
                    virtual_path=f"/systems/{system_id}",
                    node_type="directory",
                    garden=sys_mapping.get("primary_garden", "mystery"),
                    metadata={
                        "description": sys_mapping.get("description", ""),
                        "operating_gardens": sys_mapping.get("operating_gardens", []),
                        "file_count": sys_mapping.get("file_count", 0),
                    },
                )
                systems_node.children[system_id] = system_node

        self._tree = root_node
        self._loaded = True
        return root_node

    def load(self) -> bool:
        """Load and build the virtual filesystem."""
        if self._loaded:
            return True

        if not self.registry_path.exists():
            return False

        try:
            data = json.loads(self.registry_path.read_text())
            self.build_tree(data.get("file_mappings", {}))
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    def resolve(self, virtual_path: str) -> VirtualNode | None:
        """Resolve a virtual path to a node."""
        if not self._tree:
            return None

        parts = [p for p in virtual_path.strip("/").split("/") if p]
        current = self._tree

        for part in parts:
            if part not in current.children:
                return None
            current = current.children[part]

        return current

    def list_directory(self, virtual_path: str) -> list[VirtualNode]:
        """List contents of a virtual directory."""
        node = self.resolve(virtual_path)
        if not node or node.node_type != "directory":
            return []
        return list(node.children.values())

    def get_physical_path(self, virtual_path: str) -> str | None:
        """Get the physical path for a virtual file."""
        node = self.resolve(virtual_path)
        if node and node.node_type == "file":
            return node.physical_path
        return None

    def get_garden_files(self, garden: str, file_type: str | None = None) -> list[VirtualNode]:
        """Get all files for a garden, optionally filtered by type."""
        garden_node = self._garden_nodes.get(garden)
        if not garden_node:
            return []

        files = []

        def collect_files(node: VirtualNode) -> None:
            if node.node_type == "file":
                if file_type is None or file_type in node.virtual_path:
                    files.append(node)
            for child in node.children.values():
                collect_files(child)

        collect_files(garden_node)
        return files

    def search(self, query: str, gardens: list[str] | None = None) -> list[VirtualNode]:
        """Search for files by name across gardens."""
        results = []
        query_lower = query.lower()

        search_gardens = gardens or list(self._garden_nodes.keys())

        for garden in search_gardens:
            garden_node = self._garden_nodes.get(garden)
            if not garden_node:
                continue

            def search_node(node: VirtualNode) -> None:
                if node.node_type == "file":
                    if query_lower in node.virtual_path.lower() or (node.physical_path and query_lower in node.physical_path.lower()):
                        results.append(node)
                for child in node.children.values():
                    search_node(child)

            search_node(garden_node)

        return results

    def get_tree_summary(self) -> dict[str, Any]:
        """Get a summary of the virtual filesystem."""
        if not self._tree:
            return {}

        summary: dict[str, Any] = {
            "gardens": {},
            "total_files": 0,
            "total_directories": 0,
        }

        for garden_name, garden_node in self._garden_nodes.items():
            file_count = 0
            type_counts: dict[str, int] = {}

            for type_name, type_node in garden_node.children.items():
                count = len(type_node.children)
                type_counts[type_name] = count
                file_count += count

            summary["gardens"][garden_name] = {
                "files": file_count,
                "types": type_counts,
                "gana": garden_node.metadata.get("gana", ""),
                "element": garden_node.metadata.get("element", ""),
            }
            summary["total_files"] += file_count

        summary["total_directories"] = len(self._garden_nodes)

        return summary

    def to_json(self) -> str:
        """Export the virtual filesystem as JSON."""
        def node_to_dict(node: VirtualNode) -> dict[str, Any]:
            return {
                "virtual_path": node.virtual_path,
                "physical_path": node.physical_path,
                "node_type": node.node_type,
                "garden": node.garden,
                "metadata": node.metadata,
                "children": {k: node_to_dict(v) for k, v in node.children.items()},
            }

        tree_dict = node_to_dict(self._tree) if self._tree else {}
        return json.dumps(tree_dict, indent=2)


# Singleton
_virtual_fs: GardenVirtualFS | None = None


def get_garden_virtual_fs(root: Path | None = None) -> GardenVirtualFS:
    """Get the global virtual filesystem instance."""
    global _virtual_fs
    if _virtual_fs is None:
        from pathlib import Path as P
        root = root or P.cwd()
        _virtual_fs = GardenVirtualFS(root)
        _virtual_fs.load()
    return _virtual_fs


def resolve_virtual_path(virtual_path: str) -> str | None:
    """Convenience function to resolve a virtual path."""
    return get_garden_virtual_fs().get_physical_path(virtual_path)


def list_garden_directory(virtual_path: str) -> list[VirtualNode]:
    """Convenience function to list a virtual directory."""
    return get_garden_virtual_fs().list_directory(virtual_path)


if __name__ == "__main__":
    print("=" * 60)
    print("GARDEN VIRTUAL FILESYSTEM")
    print("=" * 60)

    vfs = get_garden_virtual_fs()
    summary = vfs.get_tree_summary()

    print(f"Total files: {summary.get('total_files', 0)}")
    print(f"Gardens: {len(summary.get('gardens', {}))}")
    print()
    print("Virtual paths:")
    print("  /gardens/{garden}/{file_type}/{file}")
    print("  /systems/{system}/")
    print()
    print("Example:")
    print("  /gardens/wisdom/python/sqlite_backend.py")
    print("  → whitemagic/core/memory/sqlite_backend.py")
