from pathlib import Path

from pydoover import config
from pydoover.cloud.processor import ManySubscriptionConfig, ScheduleConfig


class AgbotConfig(config.Schema):
    def __init__(self):
        # Processor subscription and schedule configuration
        self.subscription = ManySubscriptionConfig()
        self.schedule = ScheduleConfig()

        # AgBot API configuration
        self.api_base_url = config.String(
            "API Base URL",
            description="Base URL for the AgBot API",
            default="https://api.agbot.tech",
        )
        self.api_key = config.String(
            "API Key",
            description="API key or authentication token for AgBot API access",
        )

        # Display settings
        self.poll_interval_display = config.String(
            "Poll Interval Display",
            description="Display label for the polling interval (actual interval set in Schedule Config)",
            default="5 minutes",
        )

        # Alert thresholds
        self.tank_low_threshold = config.Number(
            "Tank Low Threshold (%)",
            description="Percentage threshold for low tank level warning",
            default=20.0,
        )
        self.tank_critical_threshold = config.Number(
            "Tank Critical Threshold (%)",
            description="Percentage threshold for critical tank level warning",
            default=10.0,
        )

        # Feature toggle
        self.enabled = config.Boolean(
            "Enabled",
            description="Enable or disable API polling",
            default=True,
        )


def export():
    """Export configuration schema to doover_config.json."""
    AgbotConfig().export(Path(__file__).parents[2] / "doover_config.json", "agbot")


if __name__ == "__main__":
    export()
