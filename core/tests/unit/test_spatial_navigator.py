"""Tests for spatial_navigator module."""
import pytest

from whitemagic.tools.spatial_navigator import (
    discover_related,
    find_by_zone,
    find_neighbors,
    search_by_coordinates,
)


class TestSpatialNavigator:
    def test_find_by_zone_unknown_zone(self):
        # Unknown zone should return empty list gracefully
        result = find_by_zone("nonexistent_zone_12345")
        assert isinstance(result, list)

    def test_find_by_zone_core(self):
        result = find_by_zone("core", limit=5)
        assert isinstance(result, list)

    def test_search_by_coordinates_no_backend(self):
        # Without a real backend, returns empty list gracefully
        result = search_by_coordinates(x_range=(-1.0, 1.0), y_range=(-1.0, 1.0))
        assert isinstance(result, list)

    def test_find_neighbors_no_backend(self):
        result = find_neighbors("memory_id_12345", k=5)
        assert isinstance(result, list)

    def test_discover_related_no_backend(self):
        result = discover_related("memory_id_12345", vary_axes=["y"])
        assert isinstance(result, list)

    def test_find_by_zone_alias(self):
        # "inner" is an alias for "inner_rim"
        result = find_by_zone("inner", limit=5)
        assert isinstance(result, list)
