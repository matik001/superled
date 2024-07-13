import datetime
from enum import Enum

import requests

from sunrise_api import SunriseSunsetAPI


class Room(str, Enum):
    LIVING_ROOM = 'http://duzypokoj.light'
    # SOUTH = 'south'

class Color:
    def __init__(self, r:int, g:int, b:int, w:int):
        self.r = r
        self.g = g
        self.b = b
        self.w = w
    def __str__(self):
        return f'{self.r:02x}{self.g:02x}{self.b:02x}{self.w:02x}00'
# 0000000000  - none
# ff00000000  - red
# 00ff000000  - green
# 0000ff0000  - blue
# 000000ff00  - white
class LedRoomManager:
    def __init__(self, room: Room, sunrise_api: SunriseSunsetAPI, color: Color, duration_seconds: int):
        self.room = room
        self.last_move = datetime.datetime.now()
        self.sunrise_api = sunrise_api
        self.color = color
        self.is_on = False
        self.duration_seconds = duration_seconds
        self.is_detection_enabled = True

    def _set_color(self, color:Color) -> None:
        response = requests.get(f'{self.room}/s/{color}/colorFadeMs/300')
        response.close()

    def switch(self, on:bool) -> None:
        self.is_on = on
        if on:
            self._set_color(self.color)
        else:
            self._set_color(Color(0,0,0,0))

    def handle_detected_move(self) -> None:
        if not self.is_detection_enabled:
            return None
        if self.sunrise_api.is_daylight_now():
            return None
        prev_move = self.last_move
        self.last_move = datetime.datetime.utcnow()
        if self.is_on:
            return None
        self.switch(True)

    def should_switch_off_light(self) -> bool:
        if not self.is_detection_enabled:
            return
        if not self.is_on:
            return False
        switch_off_time = self.last_move + datetime.timedelta(seconds=self.duration_seconds)
        if self.sunrise_api.is_daylight_now() or switch_off_time < datetime.datetime.utcnow():
            return True
        return False

    def switch_off_lights_if_needed(self) -> None:
        if self.should_switch_off_light():
            self.switch(False)

    def change_detection_mode(self, enabled:bool) -> None:
        if enabled == self.is_detection_enabled:
            return
        self.is_detection_enabled = enabled
        if enabled:
            self.handle_detected_move()
        else:
            self.switch(False)

