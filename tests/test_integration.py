import base64

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from integration.application import AgbotIntegration, parse_agbot_payload


SAMPLE_WEBHOOK = (
    '{"LocationCalibratedFillLevel":37.43,"LocationDailyConsumption":2.78e-07,'
    '"LocationLat":-29.70,"LocationLng":149.47,'
    '"AssetSerialNumber":"Glenroy Pumps Diesel Tank",'
    '"AssetProfileName":"Glenroy Pumps Diesel Tank",'
    '"AssetProfileWaterCapacity":52102.5,"AssetProfileMaxDepth":2.7,'
    '"AssetReportedLitres":19720.75,"AssetDepth":1.09,'
    '"AssetLastRawTelemetryTimestamp":"2026-04-07 03:00:00",'
    '"AssetLatestReportedLat":-29.70,"AssetLatestReportedLng":149.47,'
    '"DeviceSerialNumber":"0000141398","DeviceState":1,"DeviceOnline":true,'
    '"DeviceLastTelemetryEpoch":1775530800.0,"DeviceBatteryVoltage":3.66}\n'
    '{"LocationCalibratedFillLevel":17.99,"LocationDailyConsumption":0.15,'
    '"LocationLat":-29.74,"LocationLng":149.46,'
    '"AssetSerialNumber":"Krui big storage lift",'
    '"AssetProfileName":"Krui big storage lift",'
    '"AssetProfileWaterCapacity":11197.58,"AssetProfileMaxDepth":2.18,'
    '"AssetReportedLitres":2014.28,"AssetDepth":0.51,'
    '"AssetLastRawTelemetryTimestamp":"2026-04-07 04:44:49",'
    '"AssetLatestReportedLat":-29.74,"AssetLatestReportedLng":149.46,'
    '"DeviceSerialNumber":"0000141400","DeviceState":1,"DeviceOnline":true,'
    '"DeviceLastTelemetryEpoch":1775537089.0,"DeviceBatteryVoltage":3.65}'
)


# --- parse_agbot_payload tests ---


def test_parse_multiple_records():
    records = parse_agbot_payload(SAMPLE_WEBHOOK)
    assert len(records) == 2
    assert records[0]["DeviceSerialNumber"] == "0000141398"
    assert records[1]["DeviceSerialNumber"] == "0000141400"


def test_parse_single_record():
    single = '{"DeviceSerialNumber":"123","DeviceBatteryVoltage":3.5}'
    records = parse_agbot_payload(single)
    assert len(records) == 1
    assert records[0]["DeviceSerialNumber"] == "123"


def test_parse_empty_payload():
    assert parse_agbot_payload("") == []
    assert parse_agbot_payload("   \n\n  ") == []


def test_parse_skips_bad_lines():
    payload = '{"DeviceSerialNumber":"123"}\nnot json\n{"DeviceSerialNumber":"456"}'
    records = parse_agbot_payload(payload)
    assert len(records) == 2
    assert records[0]["DeviceSerialNumber"] == "123"
    assert records[1]["DeviceSerialNumber"] == "456"


def test_parse_preserves_all_fields():
    records = parse_agbot_payload(SAMPLE_WEBHOOK)
    first = records[0]
    assert first["LocationCalibratedFillLevel"] == 37.43
    assert first["AssetReportedLitres"] == 19720.75
    assert first["AssetDepth"] == 1.09
    assert first["DeviceBatteryVoltage"] == 3.66
    assert first["DeviceOnline"] is True
    assert first["AssetProfileWaterCapacity"] == 52102.5
    assert first["AssetLatestReportedLat"] == -29.70
    assert first["AssetLatestReportedLng"] == 149.47


# --- parse_ingestion_event_payload tests ---


def test_ingestion_payload_decodes_base64_and_wraps_records():
    integration = AgbotIntegration.__new__(AgbotIntegration)
    encoded = base64.b64encode(SAMPLE_WEBHOOK.encode()).decode()
    result = integration.parse_ingestion_event_payload(encoded)
    assert result is not None
    assert "records" in result
    assert len(result["records"]) == 2


def test_ingestion_payload_returns_none_for_empty():
    integration = AgbotIntegration.__new__(AgbotIntegration)
    # base64 of empty string
    encoded = base64.b64encode(b"").decode()
    assert integration.parse_ingestion_event_payload(encoded) is None
    encoded_whitespace = base64.b64encode(b"   ").decode()
    assert integration.parse_ingestion_event_payload(encoded_whitespace) is None


# --- on_ingestion_endpoint tests ---


@pytest.mark.asyncio
async def test_routes_records_to_correct_agents():
    integration = AgbotIntegration.__new__(AgbotIntegration)
    integration.api = AsyncMock()
    integration.tag_manager = MagicMock()
    integration.tag_manager.get_tag.return_value = {
        "0000141398": "agent-aaa",
        "0000141400": "agent-bbb",
    }

    event = MagicMock()
    event.payload = {"records": parse_agbot_payload(SAMPLE_WEBHOOK)}

    await integration.on_ingestion_endpoint(event)

    # Should store both raw events on integration agent
    assert integration.api.create_message.call_count == 4  # 2 raw + 2 forwarded

    # Check the forwarded calls
    forwarded_calls = [
        c for c in integration.api.create_message.call_args_list
        if c.args[0] == "on_agbot_event"
    ]
    assert len(forwarded_calls) == 2
    assert forwarded_calls[0].kwargs["agent_id"] == "agent-aaa"
    assert forwarded_calls[1].kwargs["agent_id"] == "agent-bbb"


@pytest.mark.asyncio
async def test_skips_unmapped_serial_numbers():
    integration = AgbotIntegration.__new__(AgbotIntegration)
    integration.api = AsyncMock()
    integration.tag_manager = MagicMock()
    integration.tag_manager.get_tag.return_value = {
        "0000141398": "agent-aaa",
        # 0000141400 NOT mapped
    }

    event = MagicMock()
    event.payload = {"records": parse_agbot_payload(SAMPLE_WEBHOOK)}

    await integration.on_ingestion_endpoint(event)

    # 2 raw events stored + 1 forwarded (only the mapped one)
    assert integration.api.create_message.call_count == 3
    forwarded_calls = [
        c for c in integration.api.create_message.call_args_list
        if c.args[0] == "on_agbot_event"
    ]
    assert len(forwarded_calls) == 1
    assert forwarded_calls[0].kwargs["agent_id"] == "agent-aaa"


@pytest.mark.asyncio
async def test_skips_when_no_serial_lookup_tag():
    integration = AgbotIntegration.__new__(AgbotIntegration)
    integration.api = AsyncMock()
    integration.tag_manager = MagicMock()
    integration.tag_manager.get_tag.side_effect = KeyError("not found")

    event = MagicMock()
    event.payload = {"records": parse_agbot_payload(SAMPLE_WEBHOOK)}

    await integration.on_ingestion_endpoint(event)

    # No messages should be created
    integration.api.create_message.assert_not_called()


@pytest.mark.asyncio
async def test_skips_empty_payload():
    integration = AgbotIntegration.__new__(AgbotIntegration)
    integration.api = AsyncMock()

    event = MagicMock()
    event.payload = None

    await integration.on_ingestion_endpoint(event)
    integration.api.create_message.assert_not_called()
