import gc

from machine import Pin, ADC
from time import sleep
import urequests
# import json
import network


wlan = network.WLAN(network.STA_IF)


def connect_network():
    if wlan.isconnected():
        return
    wlan.active(True)
    wlan.connect("Piesikot", "kotipies")
    while not wlan.isconnected():
        print('Connecting to network...')
        sleep(1)
    print("Network connected")

def notify_detected():
    connect_network()
    url = 'http://192.168.100.17:6767'
    response = urequests.get(f'{url}/house/rycerska/room/living_room/detected')
    response.close()

    # print('response2: ' + json.dumps(response))

led = Pin(2, Pin.OUT)
sen = Pin(5, Pin.IN)
prev = 0
connect_network()
while True:
    try:
        gc.collect()
        val = int(sen.value())
        if val:
            notify_detected()
        # if val != prev:
        #     if val:
        #         print('ruch')
        #         lights_on(True)
        #         sleep(10*60) # 10 minut
        #     else:
        #         print("brak ruchu")
        #         lights_on(False)
        # prev = val
    except Exception as e:
        print(e)
        import machine
        machine.reset()
