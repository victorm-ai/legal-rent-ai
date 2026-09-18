"""Expected clause categories by lease type (RF-21)."""

from __future__ import annotations

RESIDENTIAL_ESSENTIAL: frozenset[str] = frozenset(
    {
        "object",
        "rent",
        "deposit",
        "term",
        "maintenance",
        "services",
        "termination",
        "jurisdiction",
        "penalties",
        "renewal",
    }
)

COMMERCIAL_ESSENTIAL: frozenset[str] = frozenset(
    RESIDENTIAL_ESSENTIAL
    | {
        "sublease",
        "guarantees",
        "insurance",
        "liability",
    }
)

LEASE_TYPE_CATALOG: dict[str, frozenset[str]] = {
    "residential": RESIDENTIAL_ESSENTIAL,
    "commercial": COMMERCIAL_ESSENTIAL,
    "default": RESIDENTIAL_ESSENTIAL,
}


def essential_categories(lease_type: str = "residential") -> frozenset[str]:
    return LEASE_TYPE_CATALOG.get(lease_type, LEASE_TYPE_CATALOG["default"])
