"""Tests for protocol versioning utilities."""

import pytest
from chuk_mcp.protocol.types.versioning import (
    SUPPORTED_VERSIONS,
    CURRENT_VERSION,
    MINIMUM_VERSION,
    ProtocolVersion,
    validate_version_compatibility,
    negotiate_version,
    get_version_info,
    format_version_list,
)


class TestVersionConstants:
    """Test version constants."""

    def test_supported_versions(self):
        """Test SUPPORTED_VERSIONS is defined."""
        assert isinstance(SUPPORTED_VERSIONS, list)
        assert len(SUPPORTED_VERSIONS) > 0
        assert "2025-06-18" in SUPPORTED_VERSIONS

    def test_current_version(self):
        """Test CURRENT_VERSION is defined."""
        assert isinstance(CURRENT_VERSION, str)
        assert CURRENT_VERSION == SUPPORTED_VERSIONS[0]

    def test_minimum_version(self):
        """Test MINIMUM_VERSION is defined."""
        assert isinstance(MINIMUM_VERSION, str)
        assert MINIMUM_VERSION == SUPPORTED_VERSIONS[-1]


class TestProtocolVersionValidation:
    """Test ProtocolVersion validation methods."""

    def test_validate_format_valid(self):
        """Test validating valid version formats."""
        assert ProtocolVersion.validate_format("2025-06-18") is True
        assert ProtocolVersion.validate_format("2024-11-05") is True
        assert ProtocolVersion.validate_format("2023-01-01") is True

    def test_validate_format_invalid(self):
        """Test validating invalid version formats."""
        assert (
            ProtocolVersion.validate_format("2025-6-18") is False
        )  # Missing leading zero
        assert ProtocolVersion.validate_format("25-06-18") is False  # Wrong year format
        assert ProtocolVersion.validate_format("2025/06/18") is False  # Wrong separator
        assert ProtocolVersion.validate_format("2025-06") is False  # Missing day
        assert ProtocolVersion.validate_format("not-a-version") is False
        assert ProtocolVersion.validate_format("") is False

    def test_is_supported(self):
        """Test checking if version is supported."""
        assert ProtocolVersion.is_supported("2025-06-18") is True
        assert ProtocolVersion.is_supported("2024-11-05") is True
        assert ProtocolVersion.is_supported("2020-01-01") is False
        assert ProtocolVersion.is_supported("invalid") is False

    def test_parse_version_valid(self):
        """Test parsing valid versions."""
        year, month, day = ProtocolVersion.parse_version("2025-06-18")
        assert year == 2025
        assert month == 6
        assert day == 18

        year, month, day = ProtocolVersion.parse_version("2024-11-05")
        assert year == 2024
        assert month == 11
        assert day == 5

    def test_parse_version_invalid(self):
        """Test parsing invalid versions."""
        with pytest.raises(ValueError, match="Invalid version format"):
            ProtocolVersion.parse_version("invalid")

        with pytest.raises(ValueError, match="Invalid version format"):
            ProtocolVersion.parse_version("2025-6-18")

    def test_compare_equal(self):
        """Test comparing equal versions."""
        assert ProtocolVersion.compare("2025-06-18", "2025-06-18") == 0
        assert ProtocolVersion.compare("2024-11-05", "2024-11-05") == 0

    def test_compare_newer(self):
        """Test comparing newer version."""
        assert ProtocolVersion.compare("2025-06-18", "2024-11-05") == 1
        assert ProtocolVersion.compare("2025-12-31", "2025-01-01") == 1

    def test_compare_older(self):
        """Test comparing older version."""
        assert ProtocolVersion.compare("2024-11-05", "2025-06-18") == -1
        assert ProtocolVersion.compare("2025-01-01", "2025-12-31") == -1

    def test_compare_invalid_version1(self):
        """Test comparing with invalid first version."""
        with pytest.raises(ValueError, match="Invalid version format"):
            ProtocolVersion.compare("invalid", "2025-06-18")

    def test_compare_invalid_version2(self):
        """Test comparing with invalid second version."""
        with pytest.raises(ValueError, match="Invalid version format"):
            ProtocolVersion.compare("2025-06-18", "invalid")

    def test_is_newer(self):
        """Test is_newer method."""
        assert ProtocolVersion.is_newer("2025-06-18", "2024-11-05") is True
        assert ProtocolVersion.is_newer("2024-11-05", "2025-06-18") is False
        assert ProtocolVersion.is_newer("2025-06-18", "2025-06-18") is False

    def test_is_older(self):
        """Test is_older method."""
        assert ProtocolVersion.is_older("2024-11-05", "2025-06-18") is True
        assert ProtocolVersion.is_older("2025-06-18", "2024-11-05") is False
        assert ProtocolVersion.is_older("2025-06-18", "2025-06-18") is False

    def test_get_latest_supported(self):
        """Test getting latest supported version."""
        latest = ProtocolVersion.get_latest_supported()
        assert latest == CURRENT_VERSION
        assert latest == SUPPORTED_VERSIONS[0]

    def test_get_minimum_supported(self):
        """Test getting minimum supported version."""
        minimum = ProtocolVersion.get_minimum_supported()
        assert minimum == MINIMUM_VERSION
        assert minimum == SUPPORTED_VERSIONS[-1]

    def test_get_all_supported(self):
        """Test getting all supported versions."""
        all_versions = ProtocolVersion.get_all_supported()
        assert all_versions == SUPPORTED_VERSIONS
        # Verify it's a copy, not the original
        all_versions.append("test")
        assert "test" not in SUPPORTED_VERSIONS


class TestVersionCompatibility:
    """Test version compatibility checking."""

    def test_validate_version_compatibility_same_supported(self):
        """Test compatibility with same supported version."""
        assert validate_version_compatibility("2025-06-18", "2025-06-18") is True
        assert validate_version_compatibility("2024-11-05", "2024-11-05") is True

    def test_validate_version_compatibility_different(self):
        """Test compatibility with different versions."""
        assert validate_version_compatibility("2025-06-18", "2024-11-05") is False
        assert validate_version_compatibility("2024-11-05", "2025-06-18") is False

    def test_validate_version_compatibility_unsupported(self):
        """Test compatibility with unsupported version."""
        assert validate_version_compatibility("2020-01-01", "2020-01-01") is False


class TestVersionNegotiation:
    """Test version negotiation."""

    def test_negotiate_version_first_match(self):
        """Test negotiating version with first match."""
        client_versions = ["2025-06-18", "2024-11-05"]
        server_versions = ["2025-06-18", "2024-11-05"]

        version = negotiate_version(client_versions, server_versions)
        assert version == "2025-06-18"

    def test_negotiate_version_second_match(self):
        """Test negotiating version with second match."""
        client_versions = ["2026-01-01", "2025-06-18"]
        server_versions = ["2025-06-18", "2024-11-05"]

        version = negotiate_version(client_versions, server_versions)
        assert version == "2025-06-18"

    def test_negotiate_version_prefer_client_order(self):
        """Test that negotiation prefers client's preferred order."""
        client_versions = ["2024-11-05", "2025-06-18"]
        server_versions = ["2025-06-18", "2024-11-05"]

        version = negotiate_version(client_versions, server_versions)
        assert version == "2024-11-05"  # Client's first choice

    def test_negotiate_version_no_match(self):
        """Test negotiating version with no compatible version."""
        client_versions = ["2026-01-01", "2026-02-01"]
        server_versions = ["2025-06-18", "2024-11-05"]

        with pytest.raises(ValueError, match="No compatible protocol version found"):
            negotiate_version(client_versions, server_versions)

    def test_negotiate_version_empty_lists(self):
        """Test negotiating version with empty lists."""
        with pytest.raises(ValueError, match="No compatible protocol version found"):
            negotiate_version([], ["2025-06-18"])

        with pytest.raises(ValueError, match="No compatible protocol version found"):
            negotiate_version(["2025-06-18"], [])


class TestVersionInfo:
    """Test version info utility."""

    def test_get_version_info_current(self):
        """Test getting info for current version."""
        info = get_version_info("2025-06-18")

        assert info["version"] == "2025-06-18"
        assert info["is_valid"] is True
        assert info["is_supported"] is True
        assert info["is_current"] is True
        assert info["year"] == 2025
        assert info["month"] == 6
        assert info["day"] == 18
        assert info["is_newer_than_current"] is False
        assert "is_older_than_minimum" in info

    def test_get_version_info_older_supported(self):
        """Test getting info for older supported version."""
        info = get_version_info("2024-11-05")

        assert info["version"] == "2024-11-05"
        assert info["is_valid"] is True
        assert info["is_supported"] is True
        assert info["is_current"] is False
        assert info["year"] == 2024
        assert info["month"] == 11
        assert info["day"] == 5
        assert info["is_newer_than_current"] is False

    def test_get_version_info_future(self):
        """Test getting info for future version."""
        info = get_version_info("2026-01-01")

        assert info["version"] == "2026-01-01"
        assert info["is_valid"] is True
        assert info["is_supported"] is False
        assert info["is_current"] is False
        assert info["is_newer_than_current"] is True

    def test_get_version_info_invalid(self):
        """Test getting info for invalid version."""
        info = get_version_info("invalid")

        assert info["version"] == "invalid"
        assert info["is_valid"] is False
        assert info["is_supported"] is False
        assert info["is_current"] is False
        # Should not have parsed fields
        assert "year" not in info
        assert "month" not in info
        assert "day" not in info


class TestFormatVersionList:
    """Test version list formatting."""

    def test_format_version_list_empty(self):
        """Test formatting empty version list."""
        assert format_version_list([]) == "None"

    def test_format_version_list_single(self):
        """Test formatting single version."""
        assert format_version_list(["2025-06-18"]) == "2025-06-18"

    def test_format_version_list_two(self):
        """Test formatting two versions."""
        result = format_version_list(["2025-06-18", "2024-11-05"])
        assert result == "2025-06-18 and 2024-11-05"

    def test_format_version_list_three(self):
        """Test formatting three versions."""
        result = format_version_list(["2025-06-18", "2025-03-26", "2024-11-05"])
        assert result == "2025-06-18, 2025-03-26 and 2024-11-05"

    def test_format_version_list_many(self):
        """Test formatting many versions."""
        versions = ["v1", "v2", "v3", "v4", "v5"]
        result = format_version_list(versions)
        assert result == "v1, v2, v3, v4 and v5"
