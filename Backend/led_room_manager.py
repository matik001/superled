import datetime
from enum import Enum
from typing import List

import requests

from sunrise_api import SunriseSunsetAPI
import colorsys

class Color:
    def __init__(self, h:float, s:float, v:float, w:float) -> None:
        self.h = h
        self.s = s
        self.v = v
        self.w = w

    def from_str_blebox(text: str):
        r = int(text[0:2], 16)
        g = int(text[2:4], 16)
        b = int(text[4:6], 16)
        w = int(text[6:8], 16)
        ret = Color(r, g, b, w)
        ret.from_rgb(r, g, b, w)
        return ret

    def from_rgb(self, r:int, g:int, b:int, w:int):
        (h, s, v) = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        self.h = h
        self.s = s
        self.v = v
        self.w = w
    #
    def to_rgbw(self):
        (r, g, b) = colorsys.hsv_to_rgb(self.h, self.s, self.v)
        r = int(255*r)
        g = int(255*g)
        b = int(255*b)
        return r, g, b, self.w


    def __str__(self):
        (r,g,b,w) = self.to_rgbw()
        return f'{r:02x}{g:02x}{b:02x}{w:02x}00'


# 0000000000  - none
# ff00000000  - red
# 00ff000000  - green
# 0000ff0000  - blue
# 000000ff00  - white

class HistoryEvent:
    is_on: bool
    date: datetime.datetime

    def __init__(self, is_on: bool, date: datetime.datetime):
        super().__init__()
        self.is_on = is_on
        self.date = date

class ColorMode(Enum):
    BRIGHTNESS = 1
    HUE = 2
    SATURATION = 3
    WHITE = 4
    CRAZY = 5

class LedRoomManager:
    def __init__(self, url: str, sunrise_api: SunriseSunsetAPI, color: Color, duration_seconds: int, max_adc: int, min_adc: int):
        self.url = url
        self.last_move = datetime.datetime.now()
        self.sunrise_api = sunrise_api
        self.color = color
        self.is_light_on = False
        self.is_enabled = True
        self.duration_seconds = duration_seconds
        self.max_adc = max_adc
        self.min_adc = min_adc
        self.history:List[HistoryEvent] = []

    def _apply_color(self, color: Color, fade_ms = 300) -> None:
        url = f'{self.url}/s/{color}'
        if fade_ms > 0:
            url += f'/colorFadeMs/{fade_ms}'
        response = requests.get(url)
        print("Apply color: " + str(color))
        response.close()

    def set_enable(self, enabled: bool) -> None:
        if enabled == self.is_enabled:
            return
        self.is_enabled = enabled
        if enabled:
            self.handle_detected_move()
            self.set_light(True)
        else:
            self.set_light(False)

        self.history.append(HistoryEvent(self.is_light_on, datetime.datetime.utcnow()))
        mode = self.get_current_mode()
        if mode == ColorMode.CRAZY:
            print("PANIC!!!!")

    def set_light(self, on: bool) -> None:
        self.is_light_on = on
        if on:
            self._apply_color(self.color)
        else:
            self._apply_color(Color(0, 0, 0, 0))


    def handle_detected_move(self) -> None:
        if not self.is_enabled:
            return None
        if self.sunrise_api.is_daylight_now():
            return None
        self.last_move = datetime.datetime.utcnow()
        if self.is_light_on:
            return None
        self.set_light(True)

    def should_switch_off_light(self) -> bool:
        if not self.is_enabled:
            return False
        if not self.is_light_on:
            return False
        switch_off_time = self.last_move + datetime.timedelta(seconds=self.duration_seconds)
        if self.sunrise_api.is_daylight_now() or switch_off_time < datetime.datetime.utcnow():
            return True
        return False

    def switch_off_lights_if_needed(self) -> None:
        if self.should_switch_off_light():
            self.set_light(False)


    def get_current_mode(self) -> ColorMode:
        from_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
        offs = filter(lambda c: c.date > from_time and not c.is_light_on, self.history)
        if len(offs) == 0:
            return ColorMode.BRIGHTNESS
        elif len(offs) == 1:
            return ColorMode.BRIGHTNESS
        elif len(offs) == 2:
            return ColorMode.SATURATION
        elif len(offs) == 3:
            return ColorMode.WHITE
        elif len(offs) >= 4:
            return ColorMode.CRAZY  # crazy + clear history

    def change_adc(self, value: float) -> None:
        if not self.is_enabled:
            return None

        mode = self.get_current_mode()
        if mode == ColorMode.BRIGHTNESS:
            self.color.v = value
            self._apply_color(self.color)
        if mode == ColorMode.HUE:
            self.color.h = value
            self._apply_color(self.color)
        if mode == ColorMode.SATURATION:
            self.color.s = value
            self._apply_color(self.color)
        if mode == ColorMode.WHITE:
            self.color.w = value
            self._apply_color(self.color)
        if mode == ColorMode.CRAZY:
            print("Crazy adc")

