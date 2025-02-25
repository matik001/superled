import asyncio
import datetime
import random
import time
from enum import Enum
from typing import List

import requests

from db.models.room import Room, ColorType
from sunrise_api import SunriseSunsetAPI
import colorsys

CLOSETS_IPS = ['http://192.168.100.43', 'http://192.168.100.54', 'http://192.168.100.57']
class Color:
    # w przypadku CCT (v - janosc, h - stopien bialo-zolty)
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
        self.w = w/255
    #
    def to_rgbw(self):
        (r, g, b) = colorsys.hsv_to_rgb(self.h, self.s, self.v)
        r = int(255*r)
        g = int(255*g)
        b = int(255*b)
        w = int(255*self.w * self.v)
        return r, g, b, w

    def to_cct(self):
        cc = int(min(1.0, self.h*2)*self.v*255)
        cw = int(min(1.0, abs(2.0-2*self.h))*self.v*255)
        return f'{cc:02x}{cw:02x}{cc:02x}{cw:02x}'


    def __str__(self):
        (r,g,b,w) = self.to_rgbw()
        return f'{r:02x}{g:02x}{b:02x}{w:02x}00'


# 0000000000  - none
# ff00000000  - red
# 00ff000000  - green
# 0000ff0000  - blue
# 000000ff00  - white

class HistoryEventType(Enum):
    SWITCH= 1
    ADC = 2
class HistoryEvent:
    is_light_on: bool
    date: datetime.datetime
    type: HistoryEventType
    adc_val: float
    def __init__(self, is_light_on: bool, date: datetime.datetime, type: HistoryEventType, adc_val: float = 0.0) -> None:
        super().__init__()
        self.is_light_on = is_light_on
        self.date = date
        self.type = type
        self.adc_val = adc_val

class ColorMode(Enum):
    BRIGHTNESS = 1
    HUE = 2 # w przypadku CCT bialo zolty mix
    SATURATION = 3
    WHITE = 4
    CLOSET = 5
    CRAZY = 6

class LedRoomManager:
    def __init__(self, url: str, sunrise_api: SunriseSunsetAPI, color: Color, duration_seconds: int, max_adc: int, min_adc: int, room: Room):
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
        self.prev_adc_value = 0
        self.ADC_THRESSHOLD = 20
        self.room = room

    def _apply_color(self, color: Color, fade_ms = 300) -> None:
        color_str = str(color)
        if self.room.type == ColorType.CCT_BLEBOX:
            color_str = color.to_cct()

        url = f'{self.url}/s/{color_str}'
        if fade_ms > 0:
            url += f'/colorFadeMs/{fade_ms}'
        response = requests.get(url)
        print(f"Apply color: {color.h} {color.s} {color.v} {color.w} {color}")
        response.close()


    def _set_closet_color(self, brightness: float) -> None:
        value = int(brightness*255)
        print(f"Apply closet brightness: {value}")
        for ip in CLOSETS_IPS:
            url = f'{ip}/json/state'
            response = requests.post(url, json={'on': value > 2, 'bri': str(value)})
            response.close()
            # break


    def set_enable(self, enabled: bool) -> None:
        if enabled == self.is_enabled:
            return
        self.is_enabled = enabled
        if enabled:
            self.handle_detected_move()
            self.set_light(True)
        else:
            self.set_light(False)

        self.history.append(HistoryEvent(self.is_light_on, datetime.datetime.utcnow(), HistoryEventType.SWITCH))
        mode = self.get_current_mode()
        if mode == ColorMode.CRAZY:
            print("PANIC!!!!")

    def set_light(self, on: bool) -> None:
        self.is_light_on = on
        if on:
            self._apply_color(self.color)
            if self.room.type == ColorType.WRGB_BLEXBOX_WITH_CLOSET:
                self._set_closet_color(self.room.closet_brightness/255.0)
        else:
            self._apply_color(Color(0, 0, 0, 0))
            if self.room.type == ColorType.WRGB_BLEXBOX_WITH_CLOSET:
                self._set_closet_color(0)

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

    def trim_history(self):
        if len(self.history) == 0:
            return
        max_seconds_diff = 3
        prev = self.history[0]
        new_history = []
        for event in self.history:
            if (event.date - prev.date).total_seconds() > max_seconds_diff:
                new_history = []
            new_history.append(event)
            prev = event
        if (datetime.datetime.utcnow() - prev.date).total_seconds() > max_seconds_diff:
            new_history = []
        self.history = new_history

    def get_current_mode(self) -> ColorMode:
        self.trim_history()
        offs = [a for a in self.history if a.type == HistoryEventType.SWITCH and not a.is_light_on]
        if len(offs) == 0:
            return ColorMode.BRIGHTNESS
        elif len(offs) == 1:
            return ColorMode.HUE
        # elif len(offs) == 2:
        #     return ColorMode.SATURATION
        elif len(offs) == 2:
            return ColorMode.WHITE
        elif len(offs) == 3:
            return ColorMode.CLOSET
        elif len(offs) >= 4:
            return ColorMode.CRAZY  # crazy + clear history

    def change_adc(self, adc_value: int) -> None:
        print("Adc value is {}".format(adc_value))
        if abs(self.prev_adc_value - adc_value) < self.ADC_THRESSHOLD:
            return
        self.prev_adc_value = adc_value

        value = (adc_value - self.min_adc) / (self.max_adc - self.min_adc)
        value = min(max(value, 0), 1)

        if not self.is_enabled:
            return None

        mode = self.get_current_mode()

        self.color.s = 1
        if mode == ColorMode.BRIGHTNESS:
            self.color.v = value
            self._apply_color(self.color)
        if mode == ColorMode.HUE:
            self.color.h = value
            self._apply_color(self.color)
        # if mode == ColorMode.SATURATION:
        #     self.color.s = value
        #     self._apply_color(self.color)
        if mode == ColorMode.WHITE:
            self.color.w = value
            self._apply_color(self.color)
        if mode == ColorMode.CLOSET:
            self.color.v = value
            # self._apply_color(self.color)
            self._set_closet_color(value)
        if mode == ColorMode.CRAZY:
            print("Crazy adc")
            asyncio.create_task(self.crazy_panic())

        self.history.append(HistoryEvent(self.is_light_on, datetime.datetime.utcnow(), HistoryEventType.ADC, value))

    async def crazy_panic(self) -> None:
        for i in range(50):
            # self._apply_color(Color(0,0,1,1), 0)
            # time.sleep(0.03)
            self._apply_color(Color(0,0,0,0), 0)
            time.sleep(0.05)
            # await asyncio.sleep(0.03)
            # self._apply_color(Color(random.random(),1,1,0.1), 0)
            self._apply_color(Color(0,1,1,0.0), 0)
            time.sleep(0.05)
            self._apply_color(Color(0, 0, 0, 0), 0)
            time.sleep(0.05)
            self._apply_color(Color(0.666, 1, 1, 0.0), 0)
            time.sleep(0.05)

            # await asyncio.sleep(0.03)


