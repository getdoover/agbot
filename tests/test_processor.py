from datetime import datetime, timezone, timedelta

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from pydoover.models import ConnectionStatus
from processor.application import AgbotProcessor


SAMPLE_RECORD = {
    "LocationCalibratedFillLevel": 37.43,
    "LocationLat": -29.70,
    "LocationLng": 149.47,
    "AssetSerialNumber": "Glenroy Pumps Diesel Tank",
    "AssetProfileName": "Glenroy Pumps Diesel Tank",
    "AssetProfileWaterCapacity": 52102.5,
    "AssetProfileMaxDepth": 2.7,
    "AssetReportedLitres": 19720.75,
    "AssetDepth": 1.09,
    "AssetReadingEpoch": 1775530800,
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
        "fill_level", "litres", "depth",
        "battery_voltage", "device_online", "last_telemetry",
        "last_server_push", "last_lat", "last_lng",
        "last_reading_epoch",
    ]:
        tag = MagicMock()
        tag.set = AsyncMock()
        tag.get = MagicMock(return_value=None)
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
    proc.tags.battery_voltage.set.assert_awaited_once_with(3.66)
    proc.tags.device_online.set.assert_awaited_once_with(True)
    proc.tags.last_telemetry.set.assert_awaited_once_with("2026-04-07 03:00:00")
    proc.tags.last_server_push.set.assert_awaited_once()


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
    proc.tags.last_lat.set.assert_awaited_once_with(-29.70)
    proc.tags.last_lng.set.assert_awaited_once_with(149.47)


@pytest.mark.asyncio
async def test_skips_location_when_unchanged():
    """If lat/lng match the last published values, no update or message is sent."""
    proc = _make_processor()
    proc.tags.last_lat.get = MagicMock(return_value=-29.70)
    proc.tags.last_lng.get = MagicMock(return_value=149.47)
    event = _make_event("on_agbot_event", SAMPLE_RECORD)

    await proc.on_message_create(event)

    proc.api.update_channel_aggregate.assert_not_awaited()
    proc.api.create_message.assert_not_awaited()
    proc.tags.last_lat.set.assert_not_awaited()
    proc.tags.last_lng.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_pings_connection_with_telemetry_time():
    proc = _make_processor()
    event = _make_event("on_agbot_event", SAMPLE_RECORD)

    await proc.on_message_create(event)

    proc.ping_connection.assert_awaited_once()
    call_kwargs = proc.ping_connection.call_args.kwargs
    # online_at should be derived from DeviceLastTelemetryEpoch, not current time
    expected_online = datetime.fromtimestamp(1775530800.0, tz=timezone.utc)
    assert call_kwargs["online_at"] == expected_online
    assert call_kwargs["connection_status"] == ConnectionStatus.periodic_unknown
    # Device is online, so offline_at should be 20 hours after telemetry
    assert call_kwargs["offline_at"] == expected_online + timedelta(hours=20)


@pytest.mark.asyncio
async def test_offline_device_shows_offline():
    proc = _make_processor()
    offline_record = {**SAMPLE_RECORD, "DeviceOnline": False}
    event = _make_event("on_agbot_event", offline_record)

    await proc.on_message_create(event)

    call_kwargs = proc.ping_connection.call_args.kwargs
    expected_online = datetime.fromtimestamp(1775530800.0, tz=timezone.utc)
    # offline_at == online_at means it shows offline immediately
    assert call_kwargs["offline_at"] == expected_online


@pytest.mark.asyncio
async def test_ignores_other_channels():
    proc = _make_processor()
    event = _make_event("some_other_channel", SAMPLE_RECORD)

    await proc.on_message_create(event)

    # Nothing should be called
    proc.tags.fill_level.set.assert_not_awaited()
    proc.api.update_channel_aggregate.assert_not_awaited()
    proc.ping_connection.assert_not_awaited()


@pytest.mark.asyncio
async def test_handles_partial_data():
    """Only the fields present in the data should be set."""
    proc = _make_processor()
    partial = {
        "LocationCalibratedFillLevel": 50.0,
        "DeviceBatteryVoltage": 3.5,
        "AssetReadingEpoch": 1775530800,
    }
    event = _make_event("on_agbot_event", partial)

    await proc.on_message_create(event)

    proc.tags.fill_level.set.assert_awaited_once_with(50.0)
    proc.tags.battery_voltage.set.assert_awaited_once_with(3.5)
    # These should NOT have been called
    proc.tags.litres.set.assert_not_awaited()
    proc.tags.depth.set.assert_not_awaited()
    proc.tags.device_online.set.assert_not_awaited()
    proc.tags.last_telemetry.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_fill_level_falls_back_to_asset_reading():
    """When LocationCalibratedFillLevel is absent, AssetReadingFillLevel is used."""
    proc = _make_processor()
    payload = {
        "AssetReadingFillLevel": 52.47,
        "AssetRawFillLevel": 99.99,
        "AssetReadingEpoch": 1775530800,
    }
    event = _make_event("on_agbot_event", payload)

    await proc.on_message_create(event)

    proc.tags.fill_level.set.assert_awaited_once_with(52.47)


@pytest.mark.asyncio
async def test_fill_level_falls_back_to_raw():
    """When only AssetRawFillLevel is present, it is used."""
    proc = _make_processor()
    payload = {"AssetRawFillLevel": 42.0, "AssetReadingEpoch": 1775530800}
    event = _make_event("on_agbot_event", payload)

    await proc.on_message_create(event)

    proc.tags.fill_level.set.assert_awaited_once_with(42.0)


@pytest.mark.asyncio
async def test_no_location_without_coordinates():
    """If no lat/lng in data, location should not be published."""
    proc = _make_processor()
    no_location = {
        "LocationCalibratedFillLevel": 50.0,
        "DeviceBatteryVoltage": 3.5,
        "AssetReadingEpoch": 1775530800,
    }
    event = _make_event("on_agbot_event", no_location)

    await proc.on_message_create(event)

    proc.api.update_channel_aggregate.assert_not_awaited()
    proc.api.create_message.assert_not_awaited()
