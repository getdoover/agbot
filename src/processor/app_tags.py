from pydoover.tags import Tag, Tags


class AgbotTags(Tags):
    fill_level = Tag("number", default=None)
    litres = Tag("number", default=None)
    depth = Tag("number", default=None)
    battery_voltage = Tag("number", default=None)
    device_online = Tag("boolean", default=None)
    last_telemetry = Tag("string", default=None)
    last_server_push = Tag("string", default=None)
    last_lat = Tag("number", default=None)
    last_lng = Tag("number", default=None)
    last_reading_epoch = Tag("number", default=None)
