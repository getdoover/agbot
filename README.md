# Agbot

<img src="https://raw.githubusercontent.com/getdoover/agbot/main/assets/icon.png" alt="App Icon" style="max-width: 100px;">

**Populates a UI in the Doover WebApp by connecting to the AgBot API**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/getdoover/agbot)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/getdoover/agbot/blob/main/LICENSE)

[Getting Started](#getting-started) | [Configuration](#configuration) | [Developer](https://github.com/getdoover/agbot/blob/main/DEVELOPMENT.md) | [Need Help?](#need-help)

<br/>

## Overview

Agbot is a Doover processor that integrates with the AgBot remote water monitoring platform. It periodically polls the AgBot API to retrieve tank level data and presents it through a rich UI in the Doover WebApp, giving operators real-time visibility into water storage levels without leaving the Doover dashboard.

The processor automatically fetches sensor readings on a configurable schedule, calculates tank fill percentages, and triggers visual warnings when levels drop below user-defined thresholds. Connection status and last sync timestamps are tracked so operators always know whether data is current and reliable.

Agbot is designed for agricultural and remote water monitoring use cases where tanks are instrumented with AgBot sensors. By bridging the AgBot API into Doover, it eliminates the need to switch between platforms and enables unified fleet-level monitoring alongside other Doover-managed devices.

### Features

- Scheduled polling of the AgBot API for tank level data
- Real-time tank level display with percentage and raw volume (litres)
- Configurable low and critical level warning thresholds with colour-coded indicators
- Connection status tracking with last sync timestamp and device status
- Manual refresh action for on-demand data updates
- Enable/disable toggle to pause polling without removing the processor
- Persistent state via tags for seamless recovery between invocations

<br/>

## Getting Started

### Prerequisites

1. A Doover account with access to the Doover WebApp
2. An AgBot account with API access (API key or authentication token)
3. At least one AgBot-monitored tank or device registered on the AgBot platform

### Installation

Install the Agbot processor onto a Doover deployment using the Doover CLI or the Doover WebApp:

1. Navigate to your target deployment in the Doover WebApp
2. Add the **Agbot** processor from the app catalogue
3. Configure the required settings (see [Configuration](#configuration) below)

### Quick Start

1. Add the Agbot processor to your Doover deployment
2. Enter your **API Key** from the AgBot platform
3. Set a **Schedule** (e.g., every 5 minutes) for automatic polling
4. Add one or more **Channel Subscriptions** for command handling
5. The processor will begin polling and populating the UI on its next scheduled run

<br/>

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| **Subscription** | A list of channels to subscribe to (e.g., `cmds` for manual refresh commands) | *Required* |
| **Schedule** | Specify a schedule to run this task (controls how often the AgBot API is polled) | *Required* |
| **API Base URL** | Base URL for the AgBot API | `https://api.agbot.tech` |
| **API Key** | API key or authentication token for AgBot API access | *Required* |
| **Poll Interval Display** | Display label for the polling interval (actual interval is set in the Schedule setting) | `5 minutes` |
| **Tank Low Threshold (%)** | Percentage threshold for low tank level warning | `20.0` |
| **Tank Critical Threshold (%)** | Percentage threshold for critical tank level warning | `10.0` |
| **Enabled** | Enable or disable API polling | `true` |

### Example Configuration

```json
{
  "dv_proc_subscriptions": ["cmds"],
  "dv_proc_schedules": "rate(5 minutes)",
  "api_base_url": "https://api.agbot.tech",
  "api_key": "your-agbot-api-key",
  "poll_interval_display": "5 minutes",
  "tank_low_threshold_(%)": 20.0,
  "tank_critical_threshold_(%)": 10.0,
  "enabled": true
}
```

<br/>

## Tags

This processor exposes the following status tags:

| Tag | Description |
|-----|-------------|
| **device_data** | Stores the latest sensor readings including `level_pct`, `level_raw`, `device_status`, and the full `raw_response` from the API |
| **last_sync** | ISO 8601 timestamp of the most recent successful API poll |
| **api_status** | Current API connection status: `ok`, `error`, `pending`, or `disabled` |
| **last_error** | Error message from the most recent failed API poll, or `null` if the last poll succeeded |

<br/>

## UI Elements

This processor provides the following UI elements in the Doover WebApp:

**Tank Monitoring (Submodule)**

| Element | Type | Description |
|---------|------|-------------|
| **Tank Level** | Numeric Variable | Current tank fill level as a percentage (0-100%), with colour-coded ranges: red (0-10%), yellow (10-50%), green (50-100%) |
| **Tank Level (Raw)** | Numeric Variable | Current tank volume in litres |
| **Low Tank Level** | Warning Indicator | Appears when tank level drops below the low threshold (default 20%) |
| **Critical Tank Level** | Warning Indicator | Appears when tank level drops below the critical threshold (default 10%) |

**Connection Status (Submodule)**

| Element | Type | Description |
|---------|------|-------------|
| **API Status** | Text Variable | Current connection state (Connected, Polling..., Error, Pending, Disabled) |
| **Last Sync** | DateTime Variable | Timestamp of the last successful data fetch |
| **Device Status** | Text Variable | Status of the monitored AgBot device as reported by the API |

**Actions**

| Element | Description |
|---------|-------------|
| **Refresh Now** | Triggers an immediate API poll outside the regular schedule |

<br/>

## How It Works

1. **Deployment**: When the processor is first installed, `on_deployment` initialises default tags (`last_sync`, `api_status`, `device_data`, `last_error`) so the system starts in a known state.
2. **Scheduled Polling**: On each schedule tick, `on_schedule` calls the AgBot API at the configured base URL, authenticating with the provided API key via a Bearer token.
3. **Data Processing**: The API response is parsed to extract tank level percentage, raw volume, and device status. The processor handles multiple response formats gracefully (top-level fields, nested `devices` array, or flat device list).
4. **UI Update**: Tank level variables are updated and warning indicators are shown or hidden based on the configured low and critical thresholds. Connection status, last sync time, and device status are refreshed.
5. **State Persistence**: Sensor data and status are stored as tags so the UI can be pre-populated from the last known state on the next invocation, avoiding blank displays between polls.
6. **Manual Refresh**: Users can click the "Refresh Now" action in the UI, which sends a command on the `cmds` channel. The `on_message_create` handler detects the `refresh` action and triggers an immediate API poll.

<br/>

## Integrations

This processor works with:

- **AgBot Platform** (gen3.agbot.tech): Remote water monitoring system providing tank level sensor data via API
- **Doover WebApp**: Renders the tank monitoring UI, connection status, and warning indicators for operator visibility
- **Doover Channels**: Subscribes to channels for receiving manual refresh commands

<br/>

## Need Help?

- Email: support@doover.com
- [Doover Documentation](https://docs.doover.com)
- [App Developer Documentation](https://github.com/getdoover/agbot/blob/main/DEVELOPMENT.md)

<br/>

## Version History

### v0.1.0 (Current)
- Initial release
- AgBot API integration with configurable base URL and API key
- Tank level monitoring with percentage and raw volume display
- Configurable low and critical level warning thresholds
- Scheduled polling with manual refresh action
- Connection status tracking with last sync timestamp
- Enable/disable toggle for API polling

<br/>

## License

This app is licensed under the [Apache License 2.0](https://github.com/getdoover/agbot/blob/main/LICENSE).
