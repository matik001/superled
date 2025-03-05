from dotenv import load_dotenv

from db.models.room import ColorType
from mqtt.ActionHandlers import ActionHandlers
from mqtt.LedMQTT import LedMQTT

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
        color = Color.from_str_blebox(room.desired_color)
        managers_dict[house.name][room.name] = LedRoomManager(room.url, sunrise_api, color, room.detection_time, room.max_adc, room.min_adc, room)

action_handlers = ActionHandlers(managers_dict)
mqtt = LedMQTT(action_handlers)

app = FastAPI()

async def turn_off_lights_loop():
    while True:
        await asyncio.sleep(1)
        for house in managers_dict.values():
            for room in house.values():
                if room.room.use_motion_detector:
                    room.switch_off_lights_if_needed()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(turn_off_lights_loop())
    mqtt.start()


@app.get("/house/{house_name}/room/{room_name}/detected")
async def detected_move(house_name: str, room_name: str):
    room = managers_dict[house_name][room_name]
    room.handle_detected_move()
    return {"OK": "OK"}


@app.get("/house/{house_name}/room/{room_name}/switch/{switch_state}")
async def switch_change(house_name: str, room_name: str, switch_state: int, db: Session = Depends(get_db)):
    return action_handlers.switch_change(house_name, room_name, switch_state)



@app.get("/house/{house_name}/room/{room_name}/adc/{adc_value}")
async def adc_change(house_name: str, room_name: str, adc_value: int, db: Session = Depends(get_db)):
    return action_handlers.adc_change(house_name, room_name, adc_value)


