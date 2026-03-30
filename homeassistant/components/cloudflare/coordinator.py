"""Contains the Coordinator for updating the IP addresses of your Cloudflare DNS records."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from logging import getLogger
import socket

import pycfdns

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_ZONE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.location import async_detect_location_info
from homeassistant.util.network import is_ipv4_address, is_ipv6_address

from .const import CONF_RECORDS, DEFAULT_UPDATE_INTERVAL

_LOGGER = getLogger(__name__)

type CloudflareConfigEntry = ConfigEntry[CloudflareCoordinator]


class CloudflareCoordinator(DataUpdateCoordinator[None]):
    """Coordinates records updates."""

    config_entry: CloudflareConfigEntry
    client: pycfdns.Client
    zone: pycfdns.ZoneModel

    def __init__(
        self, hass: HomeAssistant, config_entry: CloudflareConfigEntry
    ) -> None:
        """Initialize an coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=config_entry.title,
            update_interval=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
        )

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        self.client = pycfdns.Client(
            api_token=self.config_entry.data[CONF_API_TOKEN],
            client_session=async_get_clientsession(self.hass),
        )

        try:
            self.zone = next(
                zone
                for zone in await self.client.list_zones()
                if zone["name"] == self.config_entry.data[CONF_ZONE]
            )
        except pycfdns.AuthenticationException as e:
            raise ConfigEntryAuthFailed from e
        except pycfdns.ComunicationException as e:
            raise UpdateFailed("Error communicating with API") from e

    async def _async_update_data(self) -> None:
        """Update records."""
        _LOGGER.debug("Starting update for zone %s", self.zone["name"])
        try:
            target_records: list[str] = self.config_entry.data[CONF_RECORDS]

            # Determine which record types are configured
            a_targets = {
                r.removeprefix("A:") for r in target_records if r.startswith("A:")
            }
            aaaa_targets = {
                r.removeprefix("AAAA:") for r in target_records if r.startswith("AAAA:")
            }

            # Fetch only the record types we need
            records: list[pycfdns.RecordModel] = []
            fetch_tasks: list[asyncio.Task[list[pycfdns.RecordModel]]] = []
            if a_targets:
                fetch_tasks.append(
                    self.client.list_dns_records(
                        zone_id=self.zone["id"], type="A"
                    )
                )
            if aaaa_targets:
                fetch_tasks.append(
                    self.client.list_dns_records(
                        zone_id=self.zone["id"], type="AAAA"
                    )
                )

            if fetch_tasks:
                results = await asyncio.gather(*fetch_tasks)
                for result in results:
                    records.extend(result)

            _LOGGER.debug("Records: %s", records)

            # Detect IP addresses only for needed families
            ipv4_address: str | None = None
            ipv6_address: str | None = None

            detect_tasks: dict[str, asyncio.Task[object]] = {}
            if a_targets:
                detect_tasks["ipv4"] = async_detect_location_info(
                    async_get_clientsession(self.hass, family=socket.AF_INET)
                )
            if aaaa_targets:
                detect_tasks["ipv6"] = async_detect_location_info(
                    async_get_clientsession(self.hass, family=socket.AF_INET6)
                )

            if detect_tasks:
                detect_results = await asyncio.gather(*detect_tasks.values())
                detect_keys = list(detect_tasks.keys())
                for i, key in enumerate(detect_keys):
                    location_info = detect_results[i]
                    if key == "ipv4" and location_info and is_ipv4_address(
                        location_info.ip
                    ):
                        ipv4_address = location_info.ip
                    elif key == "ipv6" and location_info and is_ipv6_address(
                        location_info.ip
                    ):
                        ipv6_address = location_info.ip

            # Check that we got the addresses we need
            errors: list[str] = []
            if a_targets and not ipv4_address:
                errors.append("IPv4")
            if aaaa_targets and not ipv6_address:
                errors.append("IPv6")

            if errors:
                raise UpdateFailed(
                    f"Could not get external {' and '.join(errors)}"
                    f" address{'es' if len(errors) > 1 else ''}"
                )

            # Filter records that need updating
            filtered_records: list[tuple[pycfdns.RecordModel, str]] = []
            for record in records:
                if record["type"] == "A" and record["name"] in a_targets:
                    assert ipv4_address is not None
                    if record["content"] != ipv4_address:
                        filtered_records.append((record, ipv4_address))
                elif record["type"] == "AAAA" and record["name"] in aaaa_targets:
                    assert ipv6_address is not None
                    if record["content"] != ipv6_address:
                        filtered_records.append((record, ipv6_address))

            if len(filtered_records) == 0:
                _LOGGER.debug("All target records are up to date")
                return

            await asyncio.gather(
                *[
                    self.client.update_dns_record(
                        zone_id=self.zone["id"],
                        record_id=record["id"],
                        record_content=ip,
                        record_name=record["name"],
                        record_type=record["type"],
                        record_proxied=record["proxied"],
                    )
                    for record, ip in filtered_records
                ]
            )

            _LOGGER.debug("Update for zone %s is complete", self.zone["name"])

        except (
            pycfdns.AuthenticationException,
            pycfdns.ComunicationException,
        ) as e:
            raise UpdateFailed(
                f"Error updating zone {self.config_entry.data[CONF_ZONE]}"
            ) from e
