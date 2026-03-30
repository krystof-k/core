"""Tests for the Cloudflare integration."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pycfdns

from homeassistant.components.cloudflare.const import CONF_RECORDS, DOMAIN
from homeassistant.const import CONF_API_TOKEN, CONF_ZONE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import UNDEFINED, UndefinedType

from tests.common import MockConfigEntry

ENTRY_CONFIG = {
    CONF_API_TOKEN: "mock-api-token",
    CONF_ZONE: "mock.com",
    CONF_RECORDS: ["A:ha.mock.com", "A:homeassistant.mock.com"],
}

ENTRY_CONFIG_IPV6 = {
    CONF_API_TOKEN: "mock-api-token",
    CONF_ZONE: "mock.com",
    CONF_RECORDS: ["AAAA:ha.mock.com", "AAAA:homeassistant.mock.com"],
}

ENTRY_CONFIG_DUAL_STACK = {
    CONF_API_TOKEN: "mock-api-token",
    CONF_ZONE: "mock.com",
    CONF_RECORDS: [
        "A:ha.mock.com",
        "A:homeassistant.mock.com",
        "AAAA:ha.mock.com",
        "AAAA:homeassistant.mock.com",
    ],
}

ENTRY_OPTIONS = {}

USER_INPUT = {
    CONF_API_TOKEN: "mock-api-token",
}

USER_INPUT_ZONE = {CONF_ZONE: "mock.com"}

USER_INPUT_RECORDS = {CONF_RECORDS: ["A:ha.mock.com", "A:homeassistant.mock.com"]}

MOCK_ZONE: pycfdns.ZoneModel = {"name": "mock.com", "id": "mock-zone-id"}
MOCK_ZONE_A_RECORDS: list[pycfdns.RecordModel] = [
    {
        "id": "zone-record-id",
        "type": "A",
        "name": "ha.mock.com",
        "proxied": True,
        "content": "127.0.0.1",
    },
    {
        "id": "zone-record-id-2",
        "type": "A",
        "name": "homeassistant.mock.com",
        "proxied": True,
        "content": "127.0.0.1",
    },
    {
        "id": "zone-record-id-3",
        "type": "A",
        "name": "mock.com",
        "proxied": True,
        "content": "127.0.0.1",
    },
]
MOCK_ZONE_AAAA_RECORDS: list[pycfdns.RecordModel] = [
    {
        "id": "zone-record-id-aaaa",
        "type": "AAAA",
        "name": "ha.mock.com",
        "proxied": True,
        "content": "::1",
    },
    {
        "id": "zone-record-id-aaaa-2",
        "type": "AAAA",
        "name": "homeassistant.mock.com",
        "proxied": True,
        "content": "::1",
    },
]


async def init_integration(
    hass: HomeAssistant,
    *,
    data: dict[str, Any] | UndefinedType = UNDEFINED,
    options: dict[str, Any] | UndefinedType = UNDEFINED,
    unique_id: str = MOCK_ZONE["name"],
    skip_setup: bool = False,
) -> MockConfigEntry:
    """Set up the Cloudflare integration in Home Assistant."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_CONFIG if data is UNDEFINED else data,
        options=ENTRY_OPTIONS if options is UNDEFINED else options,
        unique_id=unique_id,
    )
    entry.add_to_hass(hass)

    if not skip_setup:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry


def _mock_list_dns_records(**kwargs: Any) -> list[pycfdns.RecordModel]:
    """Return mock DNS records based on the requested type."""
    record_type = kwargs.get("type", "A")
    if record_type == "AAAA":
        return MOCK_ZONE_AAAA_RECORDS
    return MOCK_ZONE_A_RECORDS


def get_mock_client() -> Mock:
    """Return of Mock of pycfdns.Client."""
    client = Mock()

    client.list_zones = AsyncMock(return_value=[MOCK_ZONE])
    client.list_dns_records = AsyncMock(side_effect=_mock_list_dns_records)
    client.update_dns_record = AsyncMock(return_value=None)

    return client


def patch_async_setup_entry() -> AsyncMock:
    """Patch the async_setup_entry method and return a mock."""
    return patch(
        "homeassistant.components.cloudflare.async_setup_entry",
        return_value=True,
    )
