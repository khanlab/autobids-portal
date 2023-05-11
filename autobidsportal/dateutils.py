"""Utilities for dealing with time."""

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore[missingImport]

TIME_ZONE = zoneinfo.ZoneInfo("America/Toronto")
