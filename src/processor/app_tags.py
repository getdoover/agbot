from pydoover.tags import Tag, Tags


class AgbotTags(Tags):
    fill_level = Tag("number", default=None)
    litres = Tag("number", default=None)
    depth = Tag("number", default=None)
    daily_consumption = Tag("number", default=None)
    battery_voltage = Tag("number", default=None)
    device_online = Tag("boolean", default=None)
    last_telemetry = Tag("string", default=None)
