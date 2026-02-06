from pydoover import ui


class AgbotUI:
    def __init__(self):
        # -- Tank Info Submodule --
        self.tank_info = ui.Submodule("tank_info", "Tank Monitoring")

        self.tank_level = ui.NumericVariable(
            "tank_level",
            "Tank Level",
            precision=1,
            unit="%",
            ranges=[
                ui.Range("Critical", 0, 10, ui.Colour.red),
                ui.Range("Low", 10, 20, ui.Colour.yellow),
                ui.Range("Normal", 20, 50, ui.Colour.yellow),
                ui.Range("Good", 50, 100, ui.Colour.green),
            ],
        )

        self.tank_level_raw = ui.NumericVariable(
            "tank_level_raw",
            "Tank Level (Raw)",
            precision=0,
            unit="L",
        )

        self.low_level_warning = ui.WarningIndicator(
            "low_level_warning",
            "Low Tank Level",
            hidden=True,
        )

        self.critical_level_warning = ui.WarningIndicator(
            "critical_level_warning",
            "Critical Tank Level",
            hidden=True,
        )

        self.tank_info.add_children(
            self.tank_level,
            self.tank_level_raw,
            self.low_level_warning,
            self.critical_level_warning,
        )

        # -- Connection Info Submodule --
        self.connection_info = ui.Submodule("connection_info", "Connection Status")

        self.api_status = ui.TextVariable("api_status", "API Status")
        self.last_sync = ui.DateTimeVariable("last_sync", "Last Sync")
        self.device_status = ui.TextVariable("device_status", "Device Status")

        self.connection_info.add_children(
            self.api_status,
            self.last_sync,
            self.device_status,
        )

        # -- Actions --
        self.refresh = ui.Action("refresh", "Refresh Now", position=1)

    def fetch(self):
        """Return top-level UI elements to register with ui_manager."""
        return (self.tank_info, self.connection_info, self.refresh)

    def update_tank_data(self, level_pct, level_raw, low_threshold, critical_threshold):
        """Update tank level variables and warning indicators."""
        if level_pct is not None:
            self.tank_level.update(level_pct)
        if level_raw is not None:
            self.tank_level_raw.update(level_raw)

        # Update warning indicators based on thresholds
        if level_pct is not None:
            self.low_level_warning.hidden = level_pct >= low_threshold
            self.critical_level_warning.hidden = level_pct >= critical_threshold

    def update_connection(self, status_text, last_sync_ts, device_status_text):
        """Update connection status variables."""
        if status_text is not None:
            self.api_status.update(status_text)
        if last_sync_ts is not None:
            self.last_sync.update(last_sync_ts)
        if device_status_text is not None:
            self.device_status.update(device_status_text)

    def set_error_state(self, error_message):
        """Set UI to reflect an error state."""
        self.api_status.update(f"Error: {error_message}")
        self.device_status.update("Unknown")
