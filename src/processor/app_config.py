from pathlib import Path

from pydoover import config
from pydoover.processor import SubscriptionConfig, SerialNumberConfig


class AgbotProcessorConfig(config.Schema):
    serial_number = SerialNumberConfig(description="AgBot Device Serial Number")

    subscription = SubscriptionConfig(default="on_agbot_event")
    position = config.ApplicationPosition()


def export():
    AgbotProcessorConfig.export(
        Path(__file__).parents[2] / "doover_config.json",
        "agbot_device",
    )


if __name__ == "__main__":
    export()
