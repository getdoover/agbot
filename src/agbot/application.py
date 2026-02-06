import json
import logging
from datetime import datetime, timezone, timedelta

import aiohttp

from pydoover.cloud.processor import (
    Application,
    DeploymentEvent,
    MessageCreateEvent,
)
from pydoover.cloud.processor.types import (
    ConnectionStatus,
    ConnectionType,
    ScheduleEvent,
)
from pydoover.ui import ApplicationVariant

from .app_config import AgbotConfig
from .app_ui import AgbotUI

log = logging.getLogger(__name__)


class AgbotApplication(Application):
    config: AgbotConfig

    async def setup(self):
        """Initialize UI components and load last known state from tags."""
        self.ui = AgbotUI()
        self.ui_manager.add_children(*self.ui.fetch())
        self.ui_manager.set_variant(ApplicationVariant.stacked)

        # Pre-populate UI from last known tag data to avoid blank display between polls
        last_data = await self.get_tag("device_data", {})
        last_sync = await self.get_tag("last_sync", None)
        api_status = await self.get_tag("api_status", "pending")

        if last_data:
            level_pct = last_data.get("level_pct")
            level_raw = last_data.get("level_raw")
            device_status = last_data.get("device_status", "Unknown")
            low_threshold = self.config.tank_low_threshold.value
            critical_threshold = self.config.tank_critical_threshold.value

            self.ui.update_tank_data(level_pct, level_raw, low_threshold, critical_threshold)
            self.ui.update_connection(
                self._status_display(api_status),
                last_sync,
                device_status,
            )
        else:
            self.ui.update_connection(self._status_display(api_status), last_sync, "No data yet")

    async def close(self):
        """Clean up resources."""
        pass

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    async def on_deployment(self, event: DeploymentEvent):
        """Initialize default tags on first installation."""
        await self.set_tag("last_sync", None)
        await self.set_tag("api_status", "pending")
        await self.set_tag("device_data", {})
        await self.set_tag("last_error", None)
        log.info("AgBot processor deployed - initial tags set")

    async def on_schedule(self, event: ScheduleEvent):
        """Poll AgBot API on schedule, update UI and connection status."""
        await self._poll_agbot_api()

    async def on_message_create(self, event: MessageCreateEvent):
        """Handle manual refresh commands from the cmds channel."""
        channel = event.channel_name
        if channel != "cmds":
            return

        try:
            data = event.message.data
            if isinstance(data, str):
                data = json.loads(data)

            action = data.get("action") if isinstance(data, dict) else None
        except (json.JSONDecodeError, AttributeError):
            action = None

        if action == "refresh":
            log.info("Manual refresh triggered via cmds channel")
            await self._poll_agbot_api()
        else:
            log.debug("Received unrecognized command on cmds channel: %s", data)

    # -------------------------------------------------------------------------
    # Core API Polling Logic
    # -------------------------------------------------------------------------

    async def _poll_agbot_api(self):
        """Fetch data from the AgBot API and update UI, tags, and connection status."""
        # Check if polling is enabled
        if not self.config.enabled.value:
            await self.set_tag("api_status", "disabled")
            self.ui.update_connection("Disabled", None, None)
            await self.ui_manager.push_async()
            log.info("AgBot polling is disabled via configuration")
            return

        api_base_url = self.config.api_base_url.value
        api_key = self.config.api_key.value

        if not api_key:
            error_msg = "API key is not configured"
            log.warning(error_msg)
            await self._handle_error(error_msg)
            return

        # Update UI to show we are polling
        self.ui.update_connection("Polling...", None, None)
        await self.ui_manager.push_async()

        try:
            device_data = await self._fetch_sensor_data(api_base_url, api_key)
            await self._process_sensor_data(device_data)
        except Exception as e:
            error_msg = str(e)
            log.error("AgBot API poll failed: %s", error_msg, exc_info=True)
            await self._handle_error(error_msg)

    async def _fetch_sensor_data(self, base_url: str, api_key: str) -> dict:
        """Make HTTP request to the AgBot API and return parsed response data.

        The AgBot API does not have public documentation, so this method uses
        a configurable base URL and sends the API key as a Bearer token in the
        Authorization header. Adjust the endpoint path and auth scheme as needed
        once the actual API contract is known.
        """
        url = f"{base_url.rstrip('/')}/devices"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    body = await response.text()
                    raise RuntimeError(
                        f"AgBot API returned HTTP {response.status}: {body[:500]}"
                    )
                return await response.json()

    async def _process_sensor_data(self, raw_data: dict):
        """Parse API response, update UI, tags, and connection status."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # Extract sensor readings from the response.
        # The exact structure depends on the AgBot API which has no public docs.
        # We attempt common patterns and fall back gracefully.
        level_pct = None
        level_raw = None
        device_status = "Unknown"

        if isinstance(raw_data, dict):
            # Try top-level fields
            level_pct = raw_data.get("level_percent") or raw_data.get("level_pct") or raw_data.get("fill_percentage")
            level_raw = raw_data.get("level_litres") or raw_data.get("level_raw") or raw_data.get("volume")
            device_status = raw_data.get("status") or raw_data.get("device_status") or "Online"

            # Try nested "data" or "devices" array
            devices = raw_data.get("devices") or raw_data.get("data")
            if isinstance(devices, list) and len(devices) > 0:
                first_device = devices[0]
                if isinstance(first_device, dict):
                    level_pct = level_pct or first_device.get("level_percent") or first_device.get("fill_percentage")
                    level_raw = level_raw or first_device.get("level_litres") or first_device.get("volume")
                    device_status = first_device.get("status") or first_device.get("device_status") or device_status

        elif isinstance(raw_data, list) and len(raw_data) > 0:
            first_device = raw_data[0]
            if isinstance(first_device, dict):
                level_pct = first_device.get("level_percent") or first_device.get("fill_percentage")
                level_raw = first_device.get("level_litres") or first_device.get("volume")
                device_status = first_device.get("status") or first_device.get("device_status") or "Online"

        # Coerce to float where possible
        level_pct = self._to_float(level_pct)
        level_raw = self._to_float(level_raw)

        low_threshold = self.config.tank_low_threshold.value
        critical_threshold = self.config.tank_critical_threshold.value

        # Update UI
        self.ui.update_tank_data(level_pct, level_raw, low_threshold, critical_threshold)
        self.ui.update_connection("Connected", now_iso, device_status)
        await self.ui_manager.push_async()

        # Update connection status indicator
        await self.ping_connection(
            online_at=datetime.now(timezone.utc),
            connection_status=ConnectionStatus.periodic_unknown,
            connection_type=ConnectionType.periodic,
            offline_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )

        # Persist data in tags
        stored_data = {
            "level_pct": level_pct,
            "level_raw": level_raw,
            "device_status": device_status,
            "raw_response": raw_data,
        }
        await self.set_tag("device_data", stored_data)
        await self.set_tag("last_sync", now_iso)
        await self.set_tag("api_status", "ok")
        await self.set_tag("last_error", None)

        log.info(
            "AgBot poll successful - level: %s%%, raw: %s, status: %s",
            level_pct,
            level_raw,
            device_status,
        )

    async def _handle_error(self, error_message: str):
        """Update UI and tags to reflect an error state."""
        self.ui.set_error_state(error_message)
        await self.ui_manager.push_async()

        await self.set_tag("api_status", "error")
        await self.set_tag("last_error", error_message)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _status_display(status: str) -> str:
        """Convert internal status string to a user-friendly display string."""
        mapping = {
            "ok": "Connected",
            "error": "Error",
            "pending": "Pending",
            "disabled": "Disabled",
        }
        return mapping.get(status, status.title() if status else "Unknown")

    @staticmethod
    def _to_float(value) -> float | None:
        """Safely convert a value to float, returning None on failure."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
