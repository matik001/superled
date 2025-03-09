import json
from typing import Dict, Any

from db.models.room import Room, ColorType
from led_room_manager import ColorMode
from mqtt.ActionHandlers import ActionHandlers
from mqtt.MQTTManager import MQTTManager


class LedMQTT:
    def __init__(self, action_handler: ActionHandlers):
        self.action_handler = action_handler
        self.mqtt = MQTTManager()
        self.rooms = []
        for house_name, rooms in self.action_handler.managers_dict.items():
            for room in rooms.values():
                # if room.room.mqtt_topic:
                self.rooms.append((house_name, room.room))

    def get_room_milight_event_cct(self, house_name: str, room: Room):
        room_name = room.name

        def on_milight_event_cct(payload: str, topic: str):
            obj = json.loads(payload)
            if "brightness" in obj:
                brightness = obj['brightness']
                print(f"Ustawiona jasność: {brightness}")  # 0-255
                self.action_handler.adc_change_absolute(house_name, room_name, brightness / 255.0,
                                                              ColorMode.BRIGHTNESS)

            if obj.get("button_id") == 3:
                cct_color = obj.get('argument')  # 0 - 100
                print(f"Color: {cct_color}")
                # await self.action_handler.switch_change(house_name, room_name, True)
                self.action_handler.adc_change_absolute(house_name, room_name, cct_color / 100.0, ColorMode.HUE)

            if "state" in obj:
                is_on = 1 if obj["state"] == "ON" else 0
                print(f'IS_ON: {is_on}')
                self.action_handler.switch_change(house_name, room_name, is_on)

            # if obj.get("command") == 'night_mode':
            #     self.action_handler.switch_change(house_name, room_name, True)
            #     self.action_handler.adc_change_absolute(house_name, room_name, 0.1, ColorMode.HUE)

        return on_milight_event_cct


    def get_room_custom_event_cct(self, house_name: str, room: Room):
        room_name = room.name

        def on_custom_event_cct(payload: str, topic: str):
            obj = json.loads(payload)
            if "adc" in obj:
                adc_value = int(obj['adc'])
                print(f"ADC: {adc_value}")  # 0-255
                self.action_handler.adc_change(house_name, room_name, adc_value)

            if "state" in obj:
                is_on = 1 if obj["state"] == "ON" else 0
                print(f'IS_ON: {is_on}')
                self.action_handler.switch_change(house_name, room_name, is_on)

        return on_custom_event_cct

    def start(self):
        self.mqtt.connect_mqtt()
        for house_name, room in self.rooms:
            if room.type == ColorType.CCT_BLEBOX:
                print(f'subscribing mqtt for {room.name} in {house_name} on topic {room.mqtt_topic}')
                if room.mqtt_topic:
                    self.mqtt.subscribe(room.mqtt_topic, self.get_room_milight_event_cct(house_name, room))
                self.mqtt.subscribe(f"custom/update/{house_name}/{room.name}", self.get_room_custom_event_cct(house_name, room))
        self.mqtt.run()
