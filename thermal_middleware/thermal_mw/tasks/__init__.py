from thermal_mw.tasks.battery_temp_sensor import BatteryTempSensor
from thermal_mw.tasks.can_gateway import CanGateway
from thermal_mw.tasks.coolant_plant import CoolantPlant
from thermal_mw.tasks.thermal_controller import ThermalController

TASK_TYPES = {
    "BatteryTempSensor": BatteryTempSensor,
    "CoolantPlant": CoolantPlant,
    "ThermalController": ThermalController,
    "CanGateway": CanGateway,
}
