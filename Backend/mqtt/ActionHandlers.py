from typing import Dict

from led_room_manager import LedRoomManager, ColorMode


class ActionHandlers:
    def __init__(self, managers_dict: Dict[str, Dict[str, LedRoomManager]]):
        self.managers_dict = managers_dict

    async def switch_change(self, house_name: str, room_name: str, switch_state: int):
        is_switched = switch_state == 1
        room = self.managers_dict[house_name][room_name]
        print(f"Switch state is {is_switched}, current_mode_index: {room.current_mode_index}")
        await room.set_enable(is_switched)
        return {"OK": "OK"}

    async def adc_change_absolute(self, house_name: str, room_name: str, adc_value: float, mode:  ColorMode | None):  # adc_value 0-1
        room = self.managers_dict[house_name][room_name]
        await room.change_adc(adc_value, mode, True)
        return {"OK": "OK"}

    async def adc_change(self, house_name: str, room_name: str, adc_value: int):
        adc_value = int(adc_value)
        room = self.managers_dict[house_name][room_name]
        await room.change_adc(adc_value)
        return {"OK": "OK"}
