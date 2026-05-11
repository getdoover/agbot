import logging
from datetime import datetime, timezone, timedelta

from pydoover.processor import Application
from pydoover.models import MessageCreateEvent, ConnectionStatus

from .app_config import AgbotProcessorConfig
from .app_tags import AgbotTags
from .app_ui import AgbotUI

log = logging.getLogger(__name__)


class AgbotProcessor(Application):
    config: AgbotProcessorConfig
    config_cls = AgbotProcessorConfig
    tags_cls = AgbotTags
    ui_cls = AgbotUI

    async def setup(self):
        pass

    async def on_message_create(self, event: MessageCreateEvent):
        """
        Handle incoming AgBot events forwarded from the integration.

        The integration parses the webhook and forwards individual
        device records to the on_agbot_event channel on each device agent.
        """
        if event.channel.name != "on_agbot_event":
            return

        data = event.message.data
        log.info(f"Processing AgBot event: {data}")

        # Skip records we've already processed. AgBot batches historical
        # readings into one webhook, so the same device sees several records
        # per delivery; only the one with a newer AssetReadingEpoch than the
        # last we stored represents fresh sensor data.
        reading_epoch = data.get("AssetReadingEpoch")
        last_epoch = self.tags.last_reading_epoch.get()
        if reading_epoch is None:
            log.debug("Record has no AssetReadingEpoch, skipping")
            return
        if last_epoch is not None and reading_epoch <= last_epoch:
            log.debug(
                f"Record reading_epoch={reading_epoch} <= last={last_epoch}, skipping"
            )
            return

        now = datetime.now(timezone.utc)

        # Set tags — UI auto-updates via tag binding
        for key in ("LocationCalibratedFillLevel", "AssetReadingFillLevel", "AssetRawFillLevel"):
            if key in data:
                await self.tags.fill_level.set(data[key])
                break

        if "AssetReportedLitres" in data:
            await self.tags.litres.set(data["AssetReportedLitres"])

        if "AssetDepth" in data:
            await self.tags.depth.set(data["AssetDepth"])

        if "DeviceBatteryVoltage" in data:
            await self.tags.battery_voltage.set(data["DeviceBatteryVoltage"])

        if "DeviceOnline" in data:
            await self.tags.device_online.set(data["DeviceOnline"])

        if "AssetLastRawTelemetryTimestamp" in data:
            await self.tags.last_telemetry.set(data["AssetLastRawTelemetryTimestamp"])

        # Track when this webhook was received by Doover
        await self.tags.last_server_push.set(now.isoformat())

        # Mark this reading as processed so we skip duplicates / older batched records
        await self.tags.last_reading_epoch.set(reading_epoch)

        # Publish location only when it has changed since the last push
        lat = data.get("AssetLatestReportedLat") or data.get("LocationLat")
        lng = data.get("AssetLatestReportedLng") or data.get("LocationLng")
        if lat is not None and lng is not None:
            if lat != self.tags.last_lat.get() or lng != self.tags.last_lng.get():
                position = {"lat": lat, "long": lng}
                await self.api.update_channel_aggregate("location", position, replace_data=True)
                await self.api.create_message("location", position)
                await self.tags.last_lat.set(lat)
                await self.tags.last_lng.set(lng)

        # Update connection status using the device's last telemetry time
        # so the Doover header bar reflects when the device actually reported
        device_online = data.get("DeviceOnline", False)
        telemetry_epoch = data.get("DeviceLastTelemetryEpoch")

        if telemetry_epoch is not None:
            online_at = datetime.fromtimestamp(telemetry_epoch, tz=timezone.utc)
        else:
            online_at = now

        if device_online:
            # Device is online — set offline threshold to 20 hours from last telemetry
            offline_at = online_at + timedelta(hours=20)
        else:
            # Device is offline — set offline_at in the past so it shows offline immediately
            offline_at = online_at

        await self.ping_connection(
            online_at=online_at,
            connection_status=ConnectionStatus.periodic_unknown,
            offline_at=offline_at,
        )
