from dotenv import load_dotenv

from db.models.room import ColorType, Room
from mqtt.ActionHandlers import ActionHandlers
from mqtt.LedMQTT import LedMQTT

load_dotenv()
from sqlalchemy.orm import Session

from db.db_init import get_db, Base, engine
from db.models.house import House

import datetime
from enum import Enum
from typing import Dict
import os

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
    house_name = str(house.name)
    managers_dict[house_name] = {}
    for room in house.rooms:
        room_name = str(room.name)
        color = Color.from_str_blebox(str(room.desired_color))
        managers_dict[house_name][room_name] = LedRoomManager(str(room.url), sunrise_api, color, int(room.detection_time), int(room.max_adc), int(room.min_adc), room)

action_handlers = ActionHandlers(managers_dict)
mqtt = LedMQTT(action_handlers)

app = FastAPI()

async def turn_off_lights_loop():
    while True:
        await asyncio.sleep(1)
        for house in managers_dict.values():
            for room in house.values():
                await room.switch_off_lights_if_needed()

async def save_current_colors_to_db():
    """Zapisuje aktualny kolor każdego pokoju do bazy danych"""
    try:
        # Pobierz nową sesję bazy danych
        db_session = next(get_db())
        
        print("Zapisuję aktualny kolor pokoi do bazy danych...")
        
        for house_name, house_rooms in managers_dict.items():
            for room_name, room_manager in house_rooms.items():
                # Pobierz aktualny kolor z managera
                current_color_hex = str(room_manager.color)
                
                # Znajdź pokój w bazie danych
                db_room = db_session.query(Room).filter(
                    Room.name == room_name
                ).first()
                
                if db_room:
                    # Zapisz aktualny kolor do bazy
                    old_color = db_room.desired_color
                    # Używamy setattr aby uniknąć problemów z SQLAlchemy columns
                    setattr(db_room, 'desired_color', current_color_hex)
                    setattr(db_room, 'closet_brightness', room_manager.closet_brightness)
                    db_session.commit()
                    
                    print(f"Zapisano kolor pokoju {house_name}/{room_name}: {old_color} -> {current_color_hex}")
                    print(f"Zapisano jasność szafki {house_name}/{room_name}: {room_manager.closet_brightness}")
                else:
                    print(f"Nie znaleziono pokoju {house_name}/{room_name} w bazie danych")
        
        db_session.close()
        print("Zapisywanie kolorów zakończone pomyślnie")
        
    except Exception as e:
        print(f"Błąd podczas zapisywania kolorów do bazy: {e}")
        try:
            db_session.close()
        except:
            pass

async def save_colors_to_db_loop():
    """Pętla zapisująca kolory co godzinę"""
    while True:
        await asyncio.sleep(3600)  # 3600 sekund = 1 godzina
        await save_current_colors_to_db()

@app.on_event("startup")
async def startup_event():
    print("Starting application...")
    print(f"MQTT Host: {os.getenv('MQTT_HOST')}")
    print(f"MQTT Login: {os.getenv('MQTT_LOGIN')}")
    print(f"Event loop: {asyncio.get_running_loop()}")
    
    # Uruchom MQTT w kontekście async
    mqtt.start()
    asyncio.create_task(turn_off_lights_loop())
    asyncio.create_task(save_colors_to_db_loop())
    # Zapisz kolory przy starcie programu
    await save_current_colors_to_db()


@app.get("/house/{house_name}/room/{room_name}/detected")
async def detected_move(house_name: str, room_name: str):
    room = managers_dict[house_name][room_name]
    await room.handle_detected_move()
    return {"OK": "OK"}

#
# @app.get("/house/{house_name}/room/{room_name}/switch/{switch_state}")
# def switch_change(house_name: str, room_name: str, switch_state: int, db: Session = Depends(get_db)):
#     return action_handlers.switch_change(house_name, room_name, switch_state)
#
#
#
# @app.get("/house/{house_name}/room/{room_name}/adc/{adc_value}")
# def adc_change(house_name: str, room_name: str, adc_value: int, db: Session = Depends(get_db)):
#     return action_handlers.adc_change(house_name, room_name, adc_value)


