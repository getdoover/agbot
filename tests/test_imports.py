def test_import_integration():
    from integration.application import AgbotIntegration
    assert AgbotIntegration


def test_import_processor():
    from processor.application import AgbotProcessor
    assert AgbotProcessor
    assert AgbotProcessor.config_cls is not None
    assert AgbotProcessor.tags_cls is not None
    assert AgbotProcessor.ui_cls is not None


def test_integration_config():
    from integration.app_config import AgbotIntegrationConfig
    schema = AgbotIntegrationConfig.to_schema()
    assert isinstance(schema, dict)
    assert len(schema["properties"]) > 0


def test_processor_config():
    from processor.app_config import AgbotProcessorConfig
    schema = AgbotProcessorConfig.to_schema()
    assert isinstance(schema, dict)
    assert len(schema["properties"]) > 0


def test_processor_tags():
    from processor.app_tags import AgbotTags
    assert AgbotTags


def test_processor_ui():
    from processor.app_ui import AgbotUI
    from pydoover.ui import UI
    assert issubclass(AgbotUI, UI)
