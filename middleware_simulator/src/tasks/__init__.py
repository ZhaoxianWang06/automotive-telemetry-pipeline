from src.tasks.battery_temp_sensor import BatteryTempSensor
from src.tasks.can_gateway import CanGateway
from src.tasks.coolant_plant import CoolantPlant
from src.tasks.thermal_controller import ThermalController

TASK_TYPES = {
    "BatteryTempSensor": BatteryTempSensor,
    "CoolantPlant": CoolantPlant,
    "ThermalController": ThermalController,
    "CanGateway": CanGateway,
}
