from typing import Any
from pydoover.cloud.processor import run_app
from .application import AgbotApplication
from .app_config import AgbotConfig


def handler(event: dict[str, Any], context):
    """Lambda handler entry point."""
    AgbotConfig.clear_elements()
    run_app(
        AgbotApplication(config=AgbotConfig()),
        event,
        context,
    )
