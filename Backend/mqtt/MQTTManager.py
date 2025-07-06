import asyncio
import os
from collections import defaultdict
from random import randint
from typing import Callable, Any, Coroutine

from paho.mqtt import client as mqtt_client


class MQTTManager:
    def __init__(self):
        self.event_loop = None
        self.client:mqtt_client
        self.host = os.getenv('MQTT_HOST')
        self.login = os.getenv('MQTT_LOGIN')
        self.password = os.getenv('MQTT_PASSWORD')
        self.port = 1883
        self.client_id = f'ledbackend-{randint(0, 1000)}'

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print("Failed to connect, return code %d\n", rc)

        client = mqtt_client.Client(client_id=self.client_id)

        client.username_pw_set(self.login, self.password)
        client.on_connect = on_connect
        client.connect(self.host, self.port)
        self.client = client

    def subscribe_coroutine(self, topic: str, handler: Callable[[Any, str],  Coroutine[Any, Any, None]]):
        def on_message(client, userdata, msg):
            payload = msg.payload.decode()
            print(f"Received `{payload}` from `{msg.topic}` topic")
            try:
                if self.event_loop and not self.event_loop.is_closed():
                    asyncio.run_coroutine_threadsafe(handler(payload, msg.topic), self.event_loop)
                else:
                    print("Event loop is not available or closed")
            except Exception as e:
                print(f"Error running coroutine: {e}")

        self.client.subscribe(topic)
        self.client.message_callback_add(topic, on_message)

    def subscribe(self, topic: str, handler: Callable[[Any, str], None]):
        def on_message(client, userdata, msg):
            payload = msg.payload.decode()
            print(f"Received `{payload}` from `{msg.topic}` topic")
            handler(payload, msg.topic)

        self.client.subscribe(topic)
        self.client.message_callback_add(topic, on_message)
        # self.client.on_message = on_message

    def run(self):
        try:
            # Użyj get_running_loop() zamiast get_event_loop()
            self.event_loop = asyncio.get_running_loop()
            print(f"Using running event loop: {self.event_loop}")
        except RuntimeError:
            print("No running event loop found, trying to get current loop")
            try:
                self.event_loop = asyncio.get_event_loop()
                print(f"Using current event loop: {self.event_loop}")
            except RuntimeError as e:
                print(f"Could not get event loop: {e}")
                return
        
        self.client.loop_start()
        print("MQTT client loop started")
