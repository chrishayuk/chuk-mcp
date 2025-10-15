# chuk_mcp/protocol/types/versioning.py
"""
Protocol version handling for MCP.

This module provides utilities for managing MCP protocol versions,
including validation, compatibility checking, and version negotiation.
"""

from typing import List
import re

# Supported protocol versions (newest first)
SUPPORTED_VERSIONS = [
    "2025-06-18",  # Current protocol version (per official docs)
    "2025-03-26",  # Previous version (from lifecycle doc)
    "2024-11-05",  # Earlier supported version (legitimate older version)
]

CURRENT_VERSION = SUPPORTED_VERSIONS[0]
"""The current/latest supported MCP protocol version."""

MINIMUM_VERSION = SUPPORTED_VERSIONS[-1]
"""The minimum supported MCP protocol version."""


class ProtocolVersion:
    """Protocol version utilities and management."""

    @staticmethod
    def validate_format(version: str) -> bool:
        """
        Validate that a version follows MCP format (YYYY-MM-DD).

        Args:
            version: Version string to validate

        Returns:
            True if the version format is valid
        """
        pattern = r"^\d{4}-\d{2}-\d{2}$"
        return bool(re.match(pattern, version))

    @staticmethod
    def is_supported(version: str) -> bool:
        """
        Check if a version is in our supported versions list.

        Args:
            version: Version string to check

        Returns:
            True if the version is supported
        """
        return version in SUPPORTED_VERSIONS

    @staticmethod
    def parse_version(version: str) -> tuple[int, int, int]:
        """
        Parse a version string into year, month, day components.

        Args:
            version: Version string in YYYY-MM-DD format

        Returns:
            Tuple of (year, month, day) as integers

        Raises:
            ValueError: If version format is invalid
        """
        if not ProtocolVersion.validate_format(version):
            raise ValueError(f"Invalid version format: {version}")

        parts = version.split("-")
        return int(parts[0]), int(parts[1]), int(parts[2])

    @staticmethod
    def compare(version1: str, version2: str) -> int:
        """
        Compare two versions.

        Args:
            version1: First version to compare
            version2: Second version to compare

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2

        Raises:
            ValueError: If either version format is invalid
        """
        if version1 == version2:
            return 0

        # Validate both versions
        if not ProtocolVersion.validate_format(version1):
            raise ValueError(f"Invalid version format: {version1}")
        if not ProtocolVersion.validate_format(version2):
            raise ValueError(f"Invalid version format: {version2}")

        # Simple string comparison works for YYYY-MM-DD format
        return 1 if version1 > version2 else -1

    @staticmethod
    def is_newer(version1: str, version2: str) -> bool:
        """
        Check if version1 is newer than version2.

        Args:
            version1: Version to check
            version2: Version to compare against

        Returns:
            True if version1 is newer than version2
        """
        return ProtocolVersion.compare(version1, version2) > 0

    @staticmethod
    def is_older(version1: str, version2: str) -> bool:
        """
        Check if version1 is older than version2.

        Args:
            version1: Version to check
            version2: Version to compare against

        Returns:
            True if version1 is older than version2
        """
        return ProtocolVersion.compare(version1, version2) < 0

    @staticmethod
    def get_latest_supported() -> str:
        """Get the latest supported protocol version."""
        return CURRENT_VERSION

    @staticmethod
    def get_minimum_supported() -> str:
        """Get the minimum supported protocol version."""
        return MINIMUM_VERSION

    @staticmethod
    def get_all_supported() -> List[str]:
        """Get all supported protocol versions."""
        return SUPPORTED_VERSIONS.copy()


def validate_version_compatibility(client_version: str, server_version: str) -> bool:
    """
    Check if client and server versions are compatible.

    Per MCP specification, client and server must use the exact same
    protocol version - there is no backward/forward compatibility.

    Args:
        client_version: Version requested by client
        server_version: Version supported by server

    Returns:
        True if versions are compatible (identical and supported)
    """
    return client_version == server_version and ProtocolVersion.is_supported(
        client_version
    )


def negotiate_version(client_versions: List[str], server_versions: List[str]) -> str:
    """
    Negotiate the best protocol version between client and server.

    Args:
        client_versions: List of versions supported by client (preferred first)
        server_versions: List of versions supported by server (preferred first)

    Returns:
        The negotiated version string

    Raises:
        ValueError: If no compatible version is found
    """
    # Try to find the first client version that the server also supports
    for client_version in client_versions:
        if client_version in server_versions:
            return client_version

    # No compatible version found
    raise ValueError(
        f"No compatible protocol version found. "
        f"Client supports: {client_versions}, "
        f"Server supports: {server_versions}"
    )


def get_version_info(version: str) -> dict:
    """
    Get detailed information about a protocol version.

    Args:
        version: Version string to analyze

    Returns:
        Dictionary with version information
    """
    info = {
        "version": version,
        "is_valid": ProtocolVersion.validate_format(version),
        "is_supported": ProtocolVersion.is_supported(version),
        "is_current": version == CURRENT_VERSION,
    }

    if info["is_valid"]:
        try:
            year, month, day = ProtocolVersion.parse_version(version)
            info.update(
                {
                    "year": year,
                    "month": month,
                    "day": day,
                    "is_newer_than_current": ProtocolVersion.is_newer(
                        version, CURRENT_VERSION
                    ),
                    "is_older_than_minimum": ProtocolVersion.is_older(
                        version, MINIMUM_VERSION
                    ),
                }
            )
        except ValueError:
            pass

    return info


def format_version_list(versions: List[str]) -> str:
    """
    Format a list of versions for display.

    Args:
        versions: List of version strings

    Returns:
        Formatted string representation
    """
    if not versions:
        return "None"

    if len(versions) == 1:
        return versions[0]

    return f"{', '.join(versions[:-1])} and {versions[-1]}"


__all__ = [
    # Version constants
    "SUPPORTED_VERSIONS",
    "CURRENT_VERSION",
    "MINIMUM_VERSION",
    # Version management class
    "ProtocolVersion",
    # Utility functions
    "validate_version_compatibility",
    "negotiate_version",
    "get_version_info",
    "format_version_list",
]
