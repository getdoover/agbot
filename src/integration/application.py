import base64
import json
import logging

from pydoover.processor import Application
from pydoover.models import IngestionEndpointEvent

from .app_config import AgbotIntegrationConfig

log = logging.getLogger(__name__)


def parse_agbot_payload(raw_payload: str) -> list[dict]:
    """
    Parse an AgBot webhook payload.

    AgBot sends newline-delimited JSON — one JSON object per line,
    each representing a device/asset reading.
    """
    records = []
    seen = set()
    for line in raw_payload.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            log.warning(f"Skipping unparseable line: {line[:100]}")
            continue

        dedup_key = (record.get("DeviceSerialNumber"), record.get("AssetReadingEpoch"))
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        records.append(record)
    return records


class AgbotIntegration(Application):
    config: AgbotIntegrationConfig
    config_cls = AgbotIntegrationConfig

    async def setup(self):
        log.info("AgBot integration initialized")

    def parse_ingestion_event_payload(self, payload: str) -> dict | None:
        """
        Parse the raw ingestion event body.

        The ingestion endpoint delivers the HTTP body as a base64-encoded
        string. We decode it to get the newline-delimited JSON that AgBot
        originally posted.
        """
        try:
            decoded = base64.b64decode(payload).decode("utf-8")
            log.info(f"Raw AgBot payload: {decoded}")
            records = parse_agbot_payload(decoded)
            if not records:
                log.warning("Empty payload after parsing")
                return None
            return {"records": records}
        except Exception as e:
            log.error(f"Failed to parse payload: {e}", exc_info=True)
            return None

    async def on_ingestion_endpoint(self, event: IngestionEndpointEvent):
        """
        Handle incoming webhook data from the AgBot platform.

        Each record contains a DeviceSerialNumber used to route data
        to the correct device agent.
        """
        payload = event.payload
        if payload is None:
            log.warning("Received empty payload")
            return

        records = payload.get("records", [])
        log.info(f"Received AgBot webhook with {len(records)} record(s)")

        # AgBot batches multiple readings per webhook. Forward oldest-first so
        # the processor's reading-epoch gate accepts each new reading in order
        # rather than skipping older historicals after a newer one lands first.
        records.sort(key=lambda r: r.get("AssetReadingEpoch") or 0)


        # Look up serial number → agent ID mapping
        try:
            device_mapping = self.tag_manager.get_tag(
                "serial_number_lookup",
                app_key="agbot_device-1",
                raise_key_error=True,
            )
        except KeyError:
            log.info(
                f"Serial number lookup tag not found. Tags: {self.tag_manager._tag_values}. Skipping..."
            )
            return

        # Highest AssetReadingEpoch ingested per device serial — used to drop
        # readings AgBot re-sends in later batches so each unique reading is
        # stored / forwarded exactly once.
        last_epochs = self.get_tag("agbot_last_reading_epochs", {}) or {}
        seen_epochs = dict(last_epochs)

        for record in records:
            serial_number = record.get("DeviceSerialNumber")
            if not serial_number:
                log.warning("Record missing DeviceSerialNumber, skipping")
                continue

            serial_key = str(serial_number)
            reading_epoch = record.get("AssetReadingEpoch")
            last_seen = seen_epochs.get(serial_key)
            if (
                reading_epoch is not None
                and last_seen is not None
                and reading_epoch <= last_seen
            ):
                log.debug(
                    f"Skipping already-ingested reading for {serial_key}: epoch={reading_epoch}"
                )
                continue
            if reading_epoch is not None:
                seen_epochs[serial_key] = reading_epoch

            agent_id = device_mapping.get(serial_key)

            # Store raw event on integration agent
            await self.api.create_message("agbot_events", record)

            if agent_id:
                log.info(f"Forwarding to agent {agent_id} for serial {serial_number}")
                await self.api.create_message("on_agbot_event", record, agent_id=agent_id)
            else:
                log.warning(
                    f"No agent mapping for serial {serial_number}. Mapping: {device_mapping}"
                )

        if seen_epochs != last_epochs:
            await self.set_tag("agbot_last_reading_epochs", seen_epochs)
