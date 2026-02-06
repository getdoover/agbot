"""
Basic tests for an application.

This ensures all modules are importable and that the config is valid.
"""

def test_import_app():
    from agbot.application import AgbotApplication
    assert AgbotApplication

def test_config():
    from agbot.app_config import AgbotConfig

    config = AgbotConfig()
    assert isinstance(config.to_dict(), dict)

def test_ui():
    from agbot.app_ui import AgbotUI
    assert AgbotUI

def test_state():
    from agbot.app_state import AgbotState
    assert AgbotState