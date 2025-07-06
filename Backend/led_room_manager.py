import datetime
import time
import asyncio
from enum import Enum
from multiprocessing.dummy import Pool
from typing import List, Optional

import requests
import aiohttp

from db.models.room import Room, ColorType
from sunrise_api import SunriseSunsetAPI
import colorsys

CLOSETS_IPS = ['http://192.168.100.43', 'http://192.168.100.54', 'http://192.168.100.57']


class Color:
    # w przypadku CCT (v - janosc, h - stopien bialo-zolty)
    def __init__(self, h: float, s: float, v: float, w: float) -> None:
        self.h = h
        self.s = s
        self.v = v
        self.w = w

    @staticmethod
    def from_str_blebox(text: str):
        r = int(text[0:2], 16)
        g = int(text[2:4], 16)
        b = int(text[4:6], 16)
        w = int(text[6:8], 16)
        ret = Color(r, g, b, w)
        ret.from_rgb(r, g, b, w)
        return ret

    def from_rgb(self, r: int, g: int, b: int, w: int):
        (h, s, v) = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        self.h = h
        self.s = s
        self.v = v
        self.w = w / 255

    #
    def to_rgbw(self):
        (r, g, b) = colorsys.hsv_to_rgb(self.h, self.s, self.v)
        r = int(255 * r)
        g = int(255 * g)
        b = int(255 * b)
        w = int(255 * self.w * self.v)
        return r, g, b, w

    def to_cct(self):
        cw = int(min(1.0, self.h * 2) * self.v * 255)
        cc = int(min(1.0, abs(2.0 - 2 * self.h)) * self.v * 255)
        return f'{cc:02x}{cw:02x}{cc:02x}{cw:02x}'

    def __str__(self):
        (r, g, b, w) = self.to_rgbw()
        return f'{r:02x}{g:02x}{b:02x}{w:02x}00'


# 0000000000  - none
# ff00000000  - red
# 00ff000000  - green
# 0000ff0000  - blue
# 000000ff00  - white

class HistoryEventType(Enum):
    SWITCH = 1
    ADC = 2


class HistoryEvent:
    is_light_on: bool
    date: datetime.datetime
    type: HistoryEventType
    adc_val: float

    def __init__(self, is_light_on: bool, date: datetime.datetime, type: HistoryEventType,
                 adc_val: float = 0.0) -> None:
        super().__init__()
        self.is_light_on = is_light_on
        self.date = date
        self.type = type
        self.adc_val = adc_val


class ColorMode(Enum):
    BRIGHTNESS = 1
    HUE = 2  # w przypadku CCT bialo zolty mix
    SATURATION = 3
    WHITE = 4
    CLOSET = 5
    CRAZY = 6


class LedRoomManager:
    def __init__(self, url: str, sunrise_api: SunriseSunsetAPI, color: Color, duration_seconds: int, max_adc: int,
                 min_adc: int, room: Room):
        self.urls = url.split(',')
        self.last_move = datetime.datetime.utcnow()
        self.sunrise_api = sunrise_api
        self.color = color
        self.is_light_on = False
        self.is_enabled = True
        self.duration_seconds = duration_seconds
        self.max_adc = max_adc
        self.min_adc = min_adc
        self.history: List[HistoryEvent] = []
        self.prev_adc_value = 0
        self.ADC_THRESSHOLD = 20
        self.room = room
        # Zapisujemy wartość closet_brightness jako atrybut, żeby nie odwoływać się do kolumny SQLAlchemy
        self.closet_brightness = int(room.closet_brightness or 0)
        
        # Nowy system trybów
        self.current_mode_index = 0  # 0=brightness, 1=hue, 2=white, 3=closet, 4=panic
        self.last_adc_change = datetime.datetime.utcnow()
        self.mode_order = [ColorMode.BRIGHTNESS, ColorMode.HUE, ColorMode.WHITE, ColorMode.CLOSET, ColorMode.CRAZY]

    async def _apply_color(self, color: Color, fade_ms=300) -> None:
        color_str = str(color)
        if ColorType(self.room.type) == ColorType.CCT_BLEBOX:
            color_str = color.to_cct()
        
        # Przygotowanie wszystkich URL-i
        urls = []
        for url in self.urls:
            url = f'{url}/s/{color_str}'
            if fade_ms > 0:
                url += f'/colorFadeMs/{fade_ms}'
            urls.append(url)
        
        # Asynchroniczne wysyłanie requestów równolegle
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                task = asyncio.create_task(self._send_request(session, url))
                tasks.append(task)
            
            # Czekamy na wszystkie requesty równolegle
            await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"Apply color: {color.h} {color.s} {color.v} {color.w} {color_str}")
    
    async def _send_request(self, session: aiohttp.ClientSession, url: str) -> None:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                pass  # Nie potrzebujemy odpowiedzi
        except Exception as e:
            print(f"Error sending request to {url}: {e}")

    async def _set_closet_color(self, brightness: float) -> None:
        value = int(brightness * 255)
        print(f"Apply closet brightness: {value}")
        
        # Asynchroniczne wysyłanie requestów do wszystkich szaf równolegle
        async with aiohttp.ClientSession() as session:
            tasks = []
            for ip in CLOSETS_IPS:
                url = f'{ip}/json/state'
                payload = {'on': value > 2, 'bri': str(value)}
                task = asyncio.create_task(self._send_post_request(session, url, payload))
                tasks.append(task)
            
            # Czekamy na wszystkie requesty równolegle
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_post_request(self, session: aiohttp.ClientSession, url: str, payload: dict) -> None:
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as response:
                pass  # Nie potrzebujemy odpowiedzi
        except Exception as e:
            print(f"Error sending POST request to {url}: {e}")

    async def set_enable(self, enabled: bool) -> None:
        if enabled == self.is_enabled:
            print(f"DEBUG: Brak zmiany - enabled == is_enabled ({enabled})")
            return
        
        old_enabled = self.is_enabled
        self.is_enabled = enabled
        
        print(f"DEBUG: Zmiana z {old_enabled} na {enabled}")
        
        if enabled:
            # Włączamy - przełączamy na kolejny tryb
            if not self.is_light_on:
                # Przejdź na kolejny tryb PRZY WŁĄCZENIU
                old_mode_index = self.current_mode_index
                self.current_mode_index = (self.current_mode_index + 1) % len(self.mode_order)
                current_mode = self.mode_order[self.current_mode_index]
                
                # Resetuj czas ostatniego ADC - nowy tryb zaczyna "od nowa"
                self.last_adc_change = datetime.datetime.utcnow()
                
                print(f"Nowy tryb ADC po włączeniu: {self.mode_order[old_mode_index].name} → {current_mode.name} (index: {old_mode_index} → {self.current_mode_index})")
                
                if current_mode == ColorMode.CRAZY:
                    print("PANIC!!!!")
                    # Po panic mode wróć na początek
                    self.current_mode_index = 0
                
                await self.set_light(True)
        else:
            # Wyłączamy
            await self.set_light(False)

    async def set_light(self, on: bool) -> None:
        self.is_light_on = on
        if on:
            await self._apply_color(self.color)
            if ColorType(self.room.type) == ColorType.WRGB_BLEXBOX_WITH_CLOSET:
                await self._set_closet_color(float(self.closet_brightness) / 255.0)
        else:
            await self._apply_color(Color(0, 0, 0, 0))
            if ColorType(self.room.type) == ColorType.WRGB_BLEXBOX_WITH_CLOSET:
                await self._set_closet_color(0)

    async def handle_detected_move(self) -> None:
        if not self.is_enabled:
            return None
        if self.sunrise_api.is_daylight_now():
            return None
        
        # Sprawdź reset trybu przed obsługą ruchu
        self.check_mode_reset()
        
        self.last_move = datetime.datetime.utcnow()
        if self.is_light_on:
            return None
        await self.set_light(True)

    def should_switch_off_light(self) -> bool:
        if not self.is_enabled:
            return False
        if not self.is_light_on:
            return False
        if not bool(self.room.use_motion_detector):
            return False
        switch_off_time = self.last_move + datetime.timedelta(seconds=self.duration_seconds)
        if self.sunrise_api.is_daylight_now() and switch_off_time < datetime.datetime.utcnow():
            print("Switch off")
            print(str(switch_off_time))
            print(str(datetime.datetime.utcnow()))
            return True
        return False

    async def switch_off_lights_if_needed(self) -> None:
        # Usunąłem check_mode_reset() stąd - może resetował tryb zbyt często
        if self.should_switch_off_light():
            await self.set_light(False)

    def check_mode_reset(self):
        """Sprawdza czy nie należy wrócić do trybu BRIGHTNESS po 2 sekundach nieaktywności ADC"""
        reset_seconds = 2  # 2 sekundy na powrót do BRIGHTNESS
        
        # Jeśli minęło więcej niż reset_seconds od ostatniego ruchu ADC
        time_since_last_adc = (datetime.datetime.utcnow() - self.last_adc_change).total_seconds()
        
        if time_since_last_adc > reset_seconds:
            if self.current_mode_index != 0:  # Jeśli nie jesteśmy już w BRIGHTNESS
                old_mode = self.mode_order[self.current_mode_index]
                print(f"Powrót do trybu BRIGHTNESS po {reset_seconds} sekundach nieaktywności ADC (był {old_mode.name})")
                self.current_mode_index = 0

    def get_current_mode(self) -> ColorMode:
        """Zwraca aktualny tryb na podstawie current_mode_index"""
        self.check_mode_reset()
        return self.mode_order[self.current_mode_index]

    def trim_history(self):
        """Usuwamy starą funkcję trim_history - nie jest już potrzebna"""
        pass

    async def change_adc(self, adc_value: float, override_mode: Optional[ColorMode] = None, ignore_threshold: bool = False) -> None:
        print("Adc value is {}".format(adc_value))
        if not ignore_threshold:
            if abs(self.prev_adc_value - adc_value) < self.ADC_THRESSHOLD:
                return
            self.prev_adc_value = adc_value

            value = (adc_value - self.min_adc) / (self.max_adc - self.min_adc)
            value = min(max(value, 0), 1)
        else:
            value = adc_value

        if not self.is_enabled:
            return None

        # Pobierz aktualny tryb PRZED aktualizacją czasu (żeby reset mógł zadziałać)
        print(f"DEBUG: Przed get_current_mode() - current_mode_index: {self.current_mode_index}, last_adc_change: {(datetime.datetime.utcnow() - self.last_adc_change).total_seconds():.1f}s temu")
        mode = self.get_current_mode()
        if override_mode is not None:
            mode = override_mode
            
        print(f"DEBUG: Po get_current_mode() - używany tryb ADC: {mode.name} (index: {self.current_mode_index})")
        
        # Aktualizuj czas ostatniego ruchu ADC DOPIERO po sprawdzeniu trybu
        self.last_adc_change = datetime.datetime.utcnow()

        self.color.s = 1
        if mode == ColorMode.BRIGHTNESS:
            self.color.v = value
            await self._apply_color(self.color)
        elif mode == ColorMode.HUE:
            self.color.h = value
            await self._apply_color(self.color)
        elif mode == ColorMode.WHITE:
            self.color.w = value
            await self._apply_color(self.color)
        elif mode == ColorMode.CLOSET:
            self.color.v = value
            # await self._apply_color(self.color)
            await self._set_closet_color(value)
        elif mode == ColorMode.CRAZY:
            print("Crazy adc")
            await self.crazy_panic()

        # Zachowaj historię dla kompatybilności (można usunąć w przyszłości)
        self.history.append(HistoryEvent(self.is_light_on, datetime.datetime.utcnow(), HistoryEventType.ADC, value))

    async def crazy_panic(self) -> None:
        for i in range(50):
            # await self._apply_color(Color(0,0,1,1), 0)
            # await asyncio.sleep(0.03)
            await self._apply_color(Color(0, 0, 0, 0), 0)
            await asyncio.sleep(0.05)
            # await asyncio.sleep(0.03)
            # await self._apply_color(Color(random.random(),1,1,0.1), 0)
            await self._apply_color(Color(0, 1, 1, 0.0), 0)
            await asyncio.sleep(0.05)
            await self._apply_color(Color(0, 0, 0, 0), 0)
            await asyncio.sleep(0.05)
            await self._apply_color(Color(0.666, 1, 1, 0.0), 0)
            await asyncio.sleep(0.05)

            # await asyncio.sleep(0.03)
