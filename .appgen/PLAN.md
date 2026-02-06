# Build Plan

## App Summary
- Name: agbot
- Type: processor
- Description: Populates a UI in the Doover WebApp by connecting to the AgBot API to display remote water tank monitoring data from AgBot Gen3 sensors.

## External Integration
- Service: AgBot (gen3.agbot.tech) - Remote Water Monitoring Platform by Gasbot Pty Ltd
- Documentation: No public REST API documentation found. AgBot's API endpoints are described as "standardised API endpoints" for integration with external platforms (ERP, fleet management, farm management). No Swagger/OpenAPI spec, developer portal, or public SDK was discovered.
- Authentication: Unknown (likely API key or bearer token based on industry standards). The user will need to provide API credentials or documentation.
- Website: https://gen3.agbot.tech/
- App Store: https://apps.apple.com/us/app/agbot/id1601745398
- Developer: Gasbot Pty Ltd (Australia)

### AgBot Platform Summary (from research)
AgBot Gen3 is a remote water/liquid monitoring hardware platform that:
- Monitors liquid levels in tanks, dams, troughs, and diesel tanks
- Sensors check every 15 minutes and send instant alerts on threshold breaches
- Connects via Telstra NB-IoT/CAT-M1 cellular or Skylo NTN satellite
- Provides dashboards on mobile (iOS/Android) and web
- Supports SMS and email notifications with customisable alert rules
- Integrates with AgriWebb and other farm management systems
- Data includes: liquid levels, fill percentages, alert thresholds, asset locations

### API Documentation Gap
No public API documentation was found despite thorough searching. The build phase should implement the integration with a configurable base URL and authentication mechanism so the user can supply their API details. The processor should be designed to be resilient to API documentation gaps by:
1. Making the API base URL configurable
2. Making the authentication method configurable (API key header)
3. Providing clear error logging when API calls fail
4. Allowing the user to configure specific endpoint paths

## Data Flow
- Inputs:
  - Schedule trigger (periodic polling of AgBot API for sensor data)
  - Channel messages (optional: `cmds` channel for manual refresh commands)
- Processing:
  1. On schedule trigger, authenticate with the AgBot API
  2. Fetch sensor/device data from the AgBot API (tank levels, status, alerts)
  3. Parse and transform the response data
  4. Update UI variables with current tank levels and status
  5. Update connection status (ping_connection) to reflect last successful API poll
  6. Store last fetched data in tags for persistence
  7. Check for alert conditions (low levels, missed reports) and update warning indicators
- Outputs:
  - UI updates (tank levels, status, alerts via ui_manager.push_async)
  - Tags (last_sync, device_data, last_error, api_status)
  - Connection status updates (ping_connection)

## Configuration Schema
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| api_base_url | String | yes | https://api.agbot.tech | Base URL for the AgBot API |
| api_key | String | yes | (none) | API key or authentication token for AgBot API access |
| poll_interval_display | String | no | 5 minutes | Display label for the polling interval (actual interval set in ScheduleConfig) |
| tank_low_threshold | Number | no | 20.0 | Percentage threshold for low tank level warning |
| tank_critical_threshold | Number | no | 10.0 | Percentage threshold for critical tank level warning |
| enabled | Boolean | no | true | Enable or disable API polling |

### Subscriptions
- Channel pattern: `cmds` (for manual refresh triggers from other apps or user actions)
- Message types: command messages (e.g., `{"action": "refresh"}`)

### Schedule
- Interval: `rate(5 minutes)` (configurable via ScheduleConfig)
- Purpose: Periodically poll the AgBot API for updated sensor data and refresh the UI

## Event Handlers
| Handler | Trigger | Description |
|---------|---------|-------------|
| setup | Invocation start | Initialize UI components, load last known state from tags |
| on_schedule | rate(5 minutes) | Poll AgBot API, update UI with tank data, update connection status |
| on_message_create | Channel message on `cmds` | Handle manual refresh commands or configuration updates |
| on_deployment | First install | Initialize default tags (last_sync, api_status) |
| close | Invocation end | Clean up resources |

### Handler Details

#### setup
- Initialize AgbotUI and register with ui_manager
- Set UI variant to `ApplicationVariant.stacked`
- Load last known data from tags to pre-populate UI (avoids blank UI between polls)

#### on_schedule
1. Check if `enabled` config is true; skip if disabled
2. Authenticate with AgBot API using configured credentials
3. Fetch sensor data (GET request to API endpoint)
4. Parse response JSON for tank levels, device status, alerts
5. Update UI variables (tank level, status text, last update time, warning indicators)
6. Call `ui_manager.push_async()` to push updates to connected clients
7. Call `ping_connection()` with current timestamp and periodic connection type
8. Save fetched data to tags (`device_data`, `last_sync`, `api_status`)
9. On error: log the error, set `last_error` tag, update UI status to show error

#### on_message_create
1. Check channel name (expect `cmds`)
2. Parse command message
3. If action is `refresh`, trigger an immediate API poll (same logic as on_schedule)

#### on_deployment
1. Set initial tags: `last_sync` = null, `api_status` = "pending", `device_data` = {}

## Tags (Output)
| Tag Name | Type | Description |
|----------|------|-------------|
| device_data | object | Last fetched data from AgBot API (all sensor readings) |
| last_sync | string (ISO datetime) | Timestamp of the last successful API poll |
| last_error | string | Description of the last error encountered (null if none) |
| api_status | string | Current API connection status: "ok", "error", "pending", "disabled" |

## UI Elements (has_ui: true)

### Variables (Display on Device)
| Name | Type | Description |
|------|------|-------------|
| api_status | TextVariable | Current connection status to AgBot API (e.g., "Connected", "Error", "Polling...") |
| last_sync | DateTimeVariable | Timestamp of the last successful data sync |
| tank_level | NumericVariable | Primary tank level percentage (0-100%) with range coloring (red < 20%, yellow 20-50%, green > 50%) |
| tank_level_raw | NumericVariable | Raw tank level reading (litres or sensor units) |
| device_status | TextVariable | AgBot device/sensor status (e.g., "Online", "Offline", "Low Battery") |
| low_level_warning | WarningIndicator | Shown when tank level drops below configured threshold |
| critical_level_warning | WarningIndicator | Shown when tank level drops below critical threshold |

### Submodules
| Name | Contents | Description |
|------|----------|-------------|
| tank_info | tank_level, tank_level_raw, low_level_warning, critical_level_warning | Tank level monitoring group |
| connection_info | api_status, last_sync, device_status | Connection and sync status group |

### Actions
| Name | Type | Description |
|------|------|-------------|
| refresh | Action | Manual refresh button to trigger immediate API poll |

## Documentation Chunks

### Required Chunks
- `config-schema.md` - Configuration types and patterns (String, Number, Boolean, Schema export)
- `cloud-handler.md` - Handler entry point, Application class, event handlers (on_schedule, on_message_create, on_deployment)
- `cloud-project.md` - Project setup, build.sh, package.zip deployment, pyproject.toml
- `processor-features.md` - ManySubscriptionConfig, ScheduleConfig, UI management (ui_manager, push_async), connection status (ping_connection)

### Recommended Chunks
- `docker-ui.md` - UI component patterns (Variables, Actions, WarningIndicator, Submodule, Range coloring) - needed because has_ui is true
- `tags-channels.md` - Tag operations (get_tag, set_tag) for persistent state, channel publishing

### Discovery Keywords
subscription, schedule, rate, ui_manager, push_async, ping_connection, connection, set_tag, get_tag, warning, submodule, range, colour, action, TextVariable, NumericVariable, DateTimeVariable, BooleanVariable, WarningIndicator

## Implementation Notes
- **Processor pattern (not Docker):** This app runs as a serverless Lambda function, not a Docker container. The existing template files (`__init__.py`, `application.py`, etc.) must be rewritten to use `pydoover.cloud.processor` imports instead of `pydoover.docker`. Remove `app_state.py` (StateMachine is for device apps with continuous loops).
- **HTTP client:** Use `aiohttp` or Python's built-in `urllib.request` for API calls. Since this is a Lambda function, prefer lightweight dependencies. `aiohttp` is recommended since the handler is async.
- **External packages needed:** `aiohttp` (add to pyproject.toml dependencies)
- **API resilience:** Since AgBot's public API documentation is not available, implement the integration with maximum configurability. Use configurable URL patterns and provide clear error messages. The user will need to supply their API base URL, authentication credentials, and potentially adjust endpoint paths.
- **Cold start awareness:** Each Lambda invocation is a cold start. Do not cache data in memory between invocations. Use tags for all persistent state.
- **Idempotent handlers:** The on_schedule handler should be safe to run multiple times (just re-fetches and overwrites).
- **Error handling:** Wrap all API calls in try/except. Log errors and store in `last_error` tag. Update UI to reflect error state. Do not re-raise exceptions unless retry is desired.
- **UI push pattern:** After updating UI variables, always call `await self.ui_manager.push_async()` to send updates to connected WebApp clients.
- **Connection status:** Call `ping_connection()` after each successful API poll to update the device's connection indicator in the Doover WebApp.
- **File cleanup:** Remove `app_state.py` (no state machine needed). Remove any Docker/simulator references. Ensure `__init__.py` uses the cloud processor handler pattern.
- **Build script:** Ensure `build.sh` is present and executable for zip-based deployment. The `.gitignore` should exclude `packages_export/`, `package.zip`, and `requirements.txt`.
