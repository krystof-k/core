"""Define fixtures available for all tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.util.location import LocationInfo

from . import get_mock_client

LOCATION_PATCH_TARGET = (
    "homeassistant.components.cloudflare.coordinator.async_detect_location_info"
)

MOCK_LOCATION_IPV4 = LocationInfo(
    "0.0.0.0",
    "US",
    "USD",
    "CA",
    "California",
    "San Diego",
    "92122",
    "America/Los_Angeles",
    32.8594,
    -117.2073,
    True,
)

MOCK_LOCATION_IPV6 = LocationInfo(
    "2001:db8::1",
    "US",
    "USD",
    "CA",
    "California",
    "San Diego",
    "92122",
    "America/Los_Angeles",
    32.8594,
    -117.2073,
    True,
)


@pytest.fixture
def cfupdate() -> Generator[MagicMock]:
    """Mock the CloudflareUpdater for easier testing."""
    mock_cfupdate = get_mock_client()
    with patch(
        "homeassistant.components.cloudflare.coordinator.pycfdns.Client",
        return_value=mock_cfupdate,
    ) as mock_api:
        yield mock_api


@pytest.fixture
def cfupdate_flow() -> Generator[MagicMock]:
    """Mock the CloudflareUpdater for easier config flow testing."""
    mock_cfupdate = get_mock_client()
    with patch(
        "homeassistant.components.cloudflare.config_flow.pycfdns.Client",
        return_value=mock_cfupdate,
    ) as mock_api:
        yield mock_api


@pytest.fixture
def location_info() -> Generator[None]:
    """Mock the LocationInfo for easier testing (IPv4 only)."""
    with patch(
        LOCATION_PATCH_TARGET,
        return_value=MOCK_LOCATION_IPV4,
    ):
        yield


@pytest.fixture
def location_info_ipv6() -> Generator[None]:
    """Mock the LocationInfo for IPv6-only testing."""
    with patch(
        LOCATION_PATCH_TARGET,
        return_value=MOCK_LOCATION_IPV6,
    ):
        yield


@pytest.fixture
def location_info_dual_stack() -> Generator[None]:
    """Mock the LocationInfo for dual-stack testing (IPv4 and IPv6)."""
    call_count = 0

    def _side_effect(*args: object, **kwargs: object) -> LocationInfo:
        nonlocal call_count
        call_count += 1
        # First call is IPv4, second call is IPv6
        if call_count % 2 == 1:
            return MOCK_LOCATION_IPV4
        return MOCK_LOCATION_IPV6

    with patch(
        LOCATION_PATCH_TARGET,
        side_effect=_side_effect,
    ):
        yield
