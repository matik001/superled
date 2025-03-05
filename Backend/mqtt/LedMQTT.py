import json
from typing import Dict, Any

from led_room_manager import LedRoomManager, ColorMode
from mqtt.ActionHandlers import ActionHandlers
from mqtt.MQTTManager import MQTTManager


class LedMQTT:
    def __init__(self, action_handler: ActionHandlers):
        self.action_handler = action_handler
        self.mqtt = MQTTManager()

    async def on_milight_event(self, payload: str, topic: str):
        obj = json.loads(payload)

        house_name = 'rycerska'
        room_name = 'sypialnia'

        if "brightness" in obj:
            brightness = obj['brightness']
            print(f"Ustawiona jasność: {brightness}") # 0-255
            await self.action_handler.adc_change_absolute(house_name, room_name, brightness/255.0, ColorMode.BRIGHTNESS)

        if obj.get("button_id") == 3:
            cct_color = obj.get('argument')  # 0 - 100
            print(f"Color: {cct_color}")
            # await self.action_handler.switch_change(house_name, room_name, True)
            await self.action_handler.adc_change_absolute(house_name, room_name, cct_color/100.0, ColorMode.HUE)

        if "state" in obj:
            is_on = 1 if obj["state"] == "ON" else 0
            print(f'IS_ON: {is_on}')
            await self.action_handler.switch_change(house_name, room_name, is_on)

        if obj.get("command") == 'night_mode':
            await self.action_handler.switch_change(house_name, room_name, True)
            await self.action_handler.adc_change_absolute(house_name, room_name, 0.1, ColorMode.HUE)



    def start(self):
        self.mqtt.connect_mqtt()
        self.mqtt.subscribe('milight/update/0xC3B/fut089/#', self.on_milight_event)
        self.mqtt.run()
