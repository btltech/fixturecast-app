#!/usr/bin/env python3
"""Legacy entry point for historical multi-league collection."""

try:
    from .collect_all_leagues import main as collect_all_supported_leagues
except ImportError:
    from collect_all_leagues import main as collect_all_supported_leagues


def collect_all_leagues():
    """Run the canonical all-leagues collector."""
    return collect_all_supported_leagues()


if __name__ == "__main__":
    collect_all_leagues()
