from pathlib import Path

from pydoover import config
from pydoover.processor import IngestionEndpointConfig, ExtendedPermissionsConfig


class AgbotIntegrationConfig(config.Schema):
    integration = IngestionEndpointConfig()
    permissions = ExtendedPermissionsConfig()


def export():
    AgbotIntegrationConfig.export(
        Path(__file__).parents[2] / "doover_config.json",
        "agbot_integration",
    )
