import datetime
from enum import Enum
from typing import Dict

from fastapi import FastAPI
import requests
import asyncio

from led_room_manager import LedRoomManager, Room, Color
from sunrise_api import SunriseSunsetAPI

app = FastAPI()

rooms:Dict[str, LedRoomManager] = {
    'living_room': LedRoomManager(Room.LIVING_ROOM, SunriseSunsetAPI(), Color(0,0,0,255), 15*60)
}

async def turn_off_lights_loop():
    while True:
        await asyncio.sleep(1)
        for room in rooms:
            rooms[room].switch_off_lights_if_needed()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(turn_off_lights_loop())

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/house/{house_name}/room/{room_name}/detected")
async def detected_move(house_name: str, room_name: str):
    room = rooms[room_name]
    room.handle_detected_move()
    return {"OK": "OK"}


@app.get("/house/{house_name}/room/{room_name}/enable")
async def detected_move(house_name: str, room_name: str):
    room = rooms[room_name]
    room.change_detection_mode(True)
    return {"OK": "OK"}


@app.get("/house/{house_name}/room/{room_name}/disable")
async def detected_move(house_name: str, room_name: str):
    room = rooms[room_name]
    room.change_detection_mode(False)
    return {"OK": "OK"}
