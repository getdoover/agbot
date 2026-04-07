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

        # Set tags — UI auto-updates via tag binding
        if "LocationCalibratedFillLevel" in data:
            await self.tags.fill_level.set(data["LocationCalibratedFillLevel"])

        if "AssetReportedLitres" in data:
            await self.tags.litres.set(data["AssetReportedLitres"])

        if "AssetDepth" in data:
            await self.tags.depth.set(data["AssetDepth"])

        if "LocationDailyConsumption" in data:
            await self.tags.daily_consumption.set(data["LocationDailyConsumption"])

        if "DeviceBatteryVoltage" in data:
            await self.tags.battery_voltage.set(data["DeviceBatteryVoltage"])

        if "DeviceOnline" in data:
            await self.tags.device_online.set(data["DeviceOnline"])

        if "AssetLastRawTelemetryTimestamp" in data:
            await self.tags.last_telemetry.set(data["AssetLastRawTelemetryTimestamp"])

        # Publish location if coordinates are present
        lat = data.get("AssetLatestReportedLat") or data.get("LocationLat")
        lng = data.get("AssetLatestReportedLng") or data.get("LocationLng")
        if lat is not None and lng is not None:
            position = {"lat": lat, "long": lng}
            await self.api.update_channel_aggregate("location", position, replace_data=True)
            await self.api.create_message("location", position)

        # Update connection status — AgBot devices report periodically
        await self.ping_connection(
            online_at=datetime.now(timezone.utc),
            connection_status=ConnectionStatus.periodic_unknown,
            offline_at=datetime.now(timezone.utc) + timedelta(hours=6),
        )
