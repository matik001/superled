from dotenv import load_dotenv
load_dotenv()
from sqlalchemy.orm import Session

from db.db_init import get_db, Base, engine
from db.models.house import House


import datetime
from enum import Enum
from typing import Dict

from fastapi import FastAPI, Depends
import requests
import asyncio
from led_room_manager import LedRoomManager, Color
from sunrise_api import SunriseSunsetAPI

Base.metadata.create_all(bind=engine)

sunrise_api = SunriseSunsetAPI()

db = next(get_db())
houses = db.query(House).all()
managers_dict: Dict[str, Dict[str, LedRoomManager]] = {}
for house in houses:
    managers_dict[house.name] = {}
    for room in house.rooms:
        color = Color.from_str(room.desired_color)
        managers_dict[house.name][room.name] = LedRoomManager(room.url, sunrise_api, color, room.detection_time)

app = FastAPI()

async def turn_off_lights_loop():
    while True:
        await asyncio.sleep(1)
        for house in managers_dict.values():
            for room in house.values():
                room.switch_off_lights_if_needed()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(turn_off_lights_loop())


@app.get("/house/{house_name}/room/{room_name}/detected")
async def detected_move(house_name: str, room_name: str):
    room = managers_dict[house_name][room_name]
    room.handle_detected_move()
    return {"OK": "OK"}


@app.get("/house/{house_name}/room/{room_name}/switch/{switch_state}")
async def switch_change(house_name: str, room_name: str, switch_state: str, db: Session = Depends(get_db)):
    is_switched = switch_state == '1'
    room = managers_dict[house_name][room_name]
    room.change_detection_mode(is_switched)
    return {"OK": "OK"}

