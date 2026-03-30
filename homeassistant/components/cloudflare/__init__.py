"""Update the IP addresses of your Cloudflare DNS records."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_RECORDS, DOMAIN, SERVICE_UPDATE_RECORDS
from .coordinator import CloudflareConfigEntry, CloudflareCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    if config_entry.version == 1:
        # Version 1 only had A records; prefix them with "A:"
        _LOGGER.debug("Migrating Cloudflare config entry from version 1 to 2")
        old_records: list[str] = config_entry.data[CONF_RECORDS]
        new_records = [f"A:{record}" for record in old_records]
        hass.config_entries.async_update_entry(
            config_entry,
            data={**config_entry.data, CONF_RECORDS: new_records},
            version=2,
        )
        _LOGGER.debug("Migration to version 2 successful")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: CloudflareConfigEntry) -> bool:
    """Set up Cloudflare from a config entry."""
    entry.runtime_data = CloudflareCoordinator(hass, entry)
    await entry.runtime_data.async_config_entry_first_refresh()

    # Since we are not using coordinator for data reads, we need to add dummy listener
    entry.async_on_unload(entry.runtime_data.async_add_listener(lambda: None))

    async def update_records_service(_: ServiceCall) -> None:
        """Set up service for manual trigger."""
        await entry.runtime_data.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_UPDATE_RECORDS, update_records_service)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: CloudflareConfigEntry) -> bool:
    """Unload Cloudflare config entry."""

    return True
