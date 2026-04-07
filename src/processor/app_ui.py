from pydoover import ui

from .app_tags import AgbotTags


class AgbotUI(ui.UI):
    fill_level = ui.NumericVariable(
        "Fill Level (%)",
        precision=1,
        unit="%",
        form=ui.Widget.radial,
        value=AgbotTags.fill_level,
        ranges=[
            ui.Range("Critical", 0, 10, ui.Colour.red, show_on_graph=True),
            ui.Range("Low", 10, 25, ui.Colour.yellow, show_on_graph=True),
            ui.Range("Normal", 25, 75, ui.Colour.blue, show_on_graph=True),
            ui.Range("Full", 75, 100, ui.Colour.green, show_on_graph=True),
        ],
    )

    litres = ui.NumericVariable(
        "Volume (L)",
        precision=0,
        value=AgbotTags.litres,
    )

    depth = ui.NumericVariable(
        "Depth (m)",
        precision=2,
        value=AgbotTags.depth,
    )

    daily_consumption = ui.NumericVariable(
        "Daily Consumption (%)",
        precision=2,
        value=AgbotTags.daily_consumption,
    )

    battery_voltage = ui.NumericVariable(
        "Battery (V)",
        precision=2,
        value=AgbotTags.battery_voltage,
        ranges=[
            ui.Range("Low", 3.0, 3.4, ui.Colour.red, show_on_graph=True),
            ui.Range("OK", 3.4, 3.6, ui.Colour.yellow, show_on_graph=True),
            ui.Range("Good", 3.6, 4.2, ui.Colour.green, show_on_graph=True),
        ],
    )

    device_online = ui.BooleanVariable(
        "Device Online",
        value=AgbotTags.device_online,
    )

    last_telemetry = ui.Timestamp(
        "Last Telemetry",
        value=AgbotTags.last_telemetry,
    )

    async def setup(self):
        pass
