# ruff: noqa: BLE001
"""Warp Marketplace — P2P Warp Preset Trading.

Extends the existing marketplace bridge to support trading Warp presets
between WhiteMagic nodes. Warps are declarative agent configurations that
can be published, discovered, negotiated, and imported across the mesh.

This module bridges the WarpManager (agents/warps.py) and the
MarketplaceBridge (marketplace/bridge.py) to enable:

1. **Publish**: Export a warp as a marketplace listing
2. **Discover**: Search for warps by capability, domain, or name
3. **Negotiate**: Make offers on interesting warps
4. **Import**: Download and install a warp from the marketplace
5. **Share via Mesh**: Broadcast warp listings to peer nodes

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │  WarpMarketplace                                    │
    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
    │  │ Publish  │→ │ Discover │→ │ Negotiate    │       │
    │  └──────────┘  └──────────┘  └──────┬───────┘       │
    │                                     │               │
    │  ┌──────────┐  ┌──────────┐  ┌──────▼───────┐       │
    │  │ Import   │← │ Export   │← │ Complete     │       │
    │  └──────────┘  └──────────┘  └──────────────┘       │
    └─────────────────────────────────────────────────────┘
            │                              │
    ┌───────▼──────┐               ┌───────▼──────┐
    │ WarpManager  │               │ Marketplace  │
    │ (local)      │               │ Bridge       │
    └──────────────┘               └──────────────┘
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WarpListing:
    """A warp preset listed on the marketplace."""

    listing_id: str
    warp_name: str
    warp_data: dict[str, Any]  # Serialized Warp.to_dict()
    author_id: str = ""
    author_name: str = ""
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    research_domains: list[str] = field(default_factory=list)
    inference_tier: str = ""
    execution_mode: str = ""
    price_xrp: float = 0.0
    rating: float = 0.0
    downloads: int = 0
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "warp_name": self.warp_name,
            "warp_data": self.warp_data,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "description": self.description,
            "capabilities": self.capabilities,
            "research_domains": self.research_domains,
            "inference_tier": self.inference_tier,
            "execution_mode": self.execution_mode,
            "price_xrp": self.price_xrp,
            "rating": round(self.rating, 2),
            "downloads": self.downloads,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
        }

    def matches_query(self, query: str) -> float:
        """Relevance score for a search query."""
        q = query.lower()
        score = 0.0
        if q in self.warp_name.lower():
            score += 3.0
        if q in self.description.lower():
            score += 1.5
        for cap in self.capabilities:
            if q in cap.lower():
                score += 1.0
        for domain in self.research_domains:
            if q in domain.lower():
                score += 0.5
        return score


class WarpMarketplace:
    """P2P warp preset marketplace.

    Manages warp listings locally and optionally syncs them
    across the mesh network.
    """

    _instance: WarpMarketplace | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._listings: dict[str, WarpListing] = {}
        self._downloads: dict[str, dict[str, Any]] = {}  # download_id -> metadata
        self._data_lock = threading.Lock()
        self._stats = {
            "total_published": 0,
            "total_downloaded": 0,
            "total_negotiated": 0,
        }

    @classmethod
    def get_instance(cls) -> WarpMarketplace:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def publish(
        self,
        warp_name: str,
        warp_data: dict[str, Any],
        author_id: str = "",
        author_name: str = "",
        description: str = "",
        price_xrp: float = 0.0,
    ) -> dict[str, Any]:
        """Publish a warp preset to the marketplace.

        Args:
            warp_name: Name of the warp preset
            warp_data: Serialized Warp.to_dict() data
            author_id: Author's agent ID
            author_name: Author's display name
            description: Human-readable description
            price_xrp: Price in XRP (0 = free)

        Returns:
            Listing creation result with listing_id
        """
        # Compute content hash for dedup
        content_str = str(sorted(warp_data.items()))
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]

        # Check for existing listing with same hash
        with self._data_lock:
            for existing in self._listings.values():
                if existing.content_hash == content_hash:
                    return {
                        "status": "exists",
                        "listing_id": existing.listing_id,
                        "message": "Warp already listed",
                    }

        listing_id = hashlib.sha256(
            f"{warp_name}:{content_hash}:{time.time()}".encode()
        ).hexdigest()[:12]

        # Extract metadata from warp data
        capabilities = warp_data.get("tools_allowed") or []
        if not isinstance(capabilities, list):
            capabilities = []
        research_domains = warp_data.get("research_domains", [])
        inference_tier = warp_data.get("inference_tier", "")
        execution_mode = warp_data.get("execution_mode", "")

        listing = WarpListing(
            listing_id=listing_id,
            warp_name=warp_name,
            warp_data=warp_data,
            author_id=author_id,
            author_name=author_name,
            description=description or warp_data.get("description", ""),
            capabilities=capabilities,
            research_domains=research_domains,
            inference_tier=inference_tier,
            execution_mode=execution_mode,
            price_xrp=price_xrp,
            content_hash=content_hash,
        )

        with self._data_lock:
            self._listings[listing_id] = listing
            self._stats["total_published"] += 1

        logger.info("Warp marketplace: published '%s' (%s)", warp_name, listing_id)

        return {
            "status": "success",
            "listing_id": listing_id,
            "warp_name": warp_name,
            "content_hash": content_hash,
        }

    def discover(
        self,
        query: str = "",
        capability: str = "",
        domain: str = "",
        inference_tier: str = "",
        max_price: float = 0.0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Discover warp presets on the marketplace.

        Args:
            query: Free-text search
            capability: Required tool capability
            domain: Research domain filter
            inference_tier: Filter by inference tier
            max_price: Maximum price (0 = no limit)
            limit: Max results

        Returns:
            List of matching warp listings
        """
        with self._data_lock:
            listings = list(self._listings.values())

        # Apply filters
        results = listings

        if capability:
            results = [l for l in results if capability in l.capabilities]
        if domain:
            results = [l for l in results if domain in l.research_domains]
        if inference_tier:
            results = [l for l in results if l.inference_tier == inference_tier]
        if max_price > 0:
            results = [l for l in results if l.price_xrp <= max_price]

        # Score by relevance
        if query:
            scored = [(l, l.matches_query(query)) for l in results]
            scored = [(l, s) for l, s in scored if s > 0]
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [l for l, _ in scored[:limit]]
        else:
            results = sorted(results, key=lambda x: x.downloads, reverse=True)[:limit]

        return {
            "status": "success",
            "results": [l.to_dict() for l in results],
            "total": len(results),
        }

    def negotiate(
        self,
        listing_id: str,
        offer_xrp: float = 0.0,
        message: str = "",
    ) -> dict[str, Any]:
        """Negotiate for a warp listing (auto-accept if free or offer meets price)."""
        with self._data_lock:
            listing = self._listings.get(listing_id)

        if not listing:
            return {"status": "error", "error": "Listing not found"}

        # Free warps auto-accept
        if listing.price_xrp == 0.0 or offer_xrp >= listing.price_xrp:
            self._stats["total_negotiated"] += 1
            return {
                "status": "accepted",
                "listing_id": listing_id,
                "warp_name": listing.warp_name,
                "offer_xrp": offer_xrp,
                "message": "Offer accepted — warp ready for download",
            }

        return {
            "status": "pending",
            "listing_id": listing_id,
            "listing_price": listing.price_xrp,
            "offer_xrp": offer_xrp,
            "message": message or "Offer submitted to author",
        }

    def download(
        self,
        listing_id: str,
        target_warp_name: str | None = None,
    ) -> dict[str, Any]:
        """Download and import a warp from the marketplace.

        Args:
            listing_id: The listing to download
            target_warp_name: Override name for the imported warp

        Returns:
            The warp data ready for import into WarpManager
        """
        with self._data_lock:
            listing = self._listings.get(listing_id)

        if not listing:
            return {"status": "error", "error": "Listing not found"}

        # Increment download count
        with self._data_lock:
            listing.downloads += 1
            self._stats["total_downloaded"] += 1

        warp_data = dict(listing.warp_data)
        if target_warp_name:
            warp_data["name"] = target_warp_name
        else:
            warp_data["name"] = listing.warp_name

        # Import into WarpManager
        try:
            from whitemagic.agents.warps import Warp, WarpManager
            warp = Warp.from_dict(warp_data)
            wm = WarpManager.get_instance()
            wm.create_warp(warp, persist=True)
        except Exception as e:
            logger.debug("Warp import: %s", e, exc_info=True)
            return {
                "status": "downloaded",
                "warp_data": warp_data,
                "imported": False,
                "error": str(e),
            }

        return {
            "status": "success",
            "warp_name": warp_data["name"],
            "warp_data": warp_data,
            "imported": True,
            "downloads": listing.downloads,
        }

    def remove(self, listing_id: str) -> dict[str, Any]:
        """Remove a warp listing from the marketplace."""
        with self._data_lock:
            if listing_id not in self._listings:
                return {"status": "error", "error": "Listing not found"}
            name = self._listings[listing_id].warp_name
            del self._listings[listing_id]

        logger.info("Warp marketplace: removed '%s' (%s)", name, listing_id)
        return {"status": "success", "removed": listing_id}

    def get_listing(self, listing_id: str) -> dict[str, Any] | None:
        """Get a specific listing by ID."""
        with self._data_lock:
            listing = self._listings.get(listing_id)
            return listing.to_dict() if listing else None

    def get_status(self) -> dict[str, Any]:
        """Get marketplace status."""
        with self._data_lock:
            return {
                "total_listings": len(self._listings),
                "total_published": self._stats["total_published"],
                "total_downloaded": self._stats["total_downloaded"],
                "total_negotiated": self._stats["total_negotiated"],
                "warp_names": [l.warp_name for l in self._listings.values()],
            }

    def broadcast_listing(self, listing_id: str) -> dict[str, Any]:
        """Broadcast a warp listing to mesh peers.

        Uses the mesh client to share the listing with other nodes.
        """
        with self._data_lock:
            listing = self._listings.get(listing_id)

        if not listing:
            return {"status": "error", "error": "Listing not found"}

        try:
            from whitemagic.mesh.client import get_mesh_client
            client = get_mesh_client()
            result = client.broadcast_signal(
                signal_type="warp_listing",
                payload=listing.to_dict().__str__(),
            )
            return {
                "status": "success" if result.success else "failed",
                "message": result.message,
                "listing_id": listing_id,
            }
        except Exception as e:
            logger.debug("Broadcast listing: %s", e, exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "listing_id": listing_id,
            }


# ── Singleton ────────────────────────────────────────────────────────────

def get_warp_marketplace() -> WarpMarketplace:
    """Get the global WarpMarketplace singleton."""
    return WarpMarketplace.get_instance()
