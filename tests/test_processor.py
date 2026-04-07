import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from processor.application import AgbotProcessor


SAMPLE_RECORD = {
    "LocationCalibratedFillLevel": 37.43,
    "LocationDailyConsumption": 2.78e-07,
    "LocationLat": -29.70,
    "LocationLng": 149.47,
    "AssetSerialNumber": "Glenroy Pumps Diesel Tank",
    "AssetProfileName": "Glenroy Pumps Diesel Tank",
    "AssetProfileWaterCapacity": 52102.5,
    "AssetProfileMaxDepth": 2.7,
    "AssetReportedLitres": 19720.75,
    "AssetDepth": 1.09,
    "AssetLastRawTelemetryTimestamp": "2026-04-07 03:00:00",
    "AssetLatestReportedLat": -29.70,
    "AssetLatestReportedLng": 149.47,
    "DeviceSerialNumber": "0000141398",
    "DeviceState": 1,
    "DeviceOnline": True,
    "DeviceLastTelemetryEpoch": 1775530800.0,
    "DeviceBatteryVoltage": 3.66,
}


def _make_processor():
    """Create an AgbotProcessor with mocked framework dependencies."""
    proc = AgbotProcessor.__new__(AgbotProcessor)

    # Mock tags — each tag is an async-settable mock
    proc.tags = MagicMock()
    for tag_name in [
        "fill_level", "litres", "depth", "daily_consumption",
        "battery_voltage", "device_online", "last_telemetry",
    ]:
        tag = MagicMock()
        tag.set = AsyncMock()
        setattr(proc.tags, tag_name, tag)

    # Mock API and connection
    proc.api = AsyncMock()
    proc.ping_connection = AsyncMock()
    type(proc).agent_id = PropertyMock(return_value="test-agent-id")

    return proc


def _make_event(channel_name: str, data: dict):
    event = MagicMock()
    event.channel.name = channel_name
    event.message.data = data
    return event


# --- on_message_create tests ---


@pytest.mark.asyncio
async def test_processes_full_agbot_record():
    proc = _make_processor()
    event = _make_event("on_agbot_event", SAMPLE_RECORD)

    await proc.on_message_create(event)

    proc.tags.fill_level.set.assert_awaited_once_with(37.43)
    proc.tags.litres.set.assert_awaited_once_with(19720.75)
    proc.tags.depth.set.assert_awaited_once_with(1.09)
    proc.tags.daily_consumption.set.assert_awaited_once_with(2.78e-07)
    proc.tags.battery_voltage.set.assert_awaited_once_with(3.66)
    proc.tags.device_online.set.assert_awaited_once_with(True)
    proc.tags.last_telemetry.set.assert_awaited_once_with("2026-04-07 03:00:00")


@pytest.mark.asyncio
async def test_publishes_location():
    proc = _make_processor()
    event = _make_event("on_agbot_event", SAMPLE_RECORD)

    await proc.on_message_create(event)

    proc.api.update_channel_aggregate.assert_awaited_once_with(
        "location",
        {"lat": -29.70, "long": 149.47},
        replace_data=True,
    )
    proc.api.create_message.assert_awaited_once_with(
        "location",
        {"lat": -29.70, "long": 149.47},
    )


@pytest.mark.asyncio
async def test_pings_connection():
    proc = _make_processor()
    event = _make_event("on_agbot_event", SAMPLE_RECORD)

    await proc.on_message_create(event)

    proc.ping_connection.assert_awaited_once()


@pytest.mark.asyncio
async def test_ignores_other_channels():
    proc = _make_processor()
    event = _make_event("some_other_channel", SAMPLE_RECORD)

    await proc.on_message_create(event)

    # Nothing should be called
    proc.tags.fill_level.set.assert_not_awaited()
    proc.api.update_aggregate.assert_not_awaited()
    proc.ping_connection.assert_not_awaited()


@pytest.mark.asyncio
async def test_handles_partial_data():
    """Only the fields present in the data should be set."""
    proc = _make_processor()
    partial = {
        "LocationCalibratedFillLevel": 50.0,
        "DeviceBatteryVoltage": 3.5,
    }
    event = _make_event("on_agbot_event", partial)

    await proc.on_message_create(event)

    proc.tags.fill_level.set.assert_awaited_once_with(50.0)
    proc.tags.battery_voltage.set.assert_awaited_once_with(3.5)
    # These should NOT have been called
    proc.tags.litres.set.assert_not_awaited()
    proc.tags.depth.set.assert_not_awaited()
    proc.tags.daily_consumption.set.assert_not_awaited()
    proc.tags.device_online.set.assert_not_awaited()
    proc.tags.last_telemetry.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_location_without_coordinates():
    """If no lat/lng in data, location should not be published."""
    proc = _make_processor()
    no_location = {
        "LocationCalibratedFillLevel": 50.0,
        "DeviceBatteryVoltage": 3.5,
    }
    event = _make_event("on_agbot_event", no_location)

    await proc.on_message_create(event)

    proc.api.update_channel_aggregate.assert_not_awaited()
    proc.api.create_message.assert_not_awaited()
