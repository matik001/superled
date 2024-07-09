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

def lights_on(state:bool):
    connect_network()
    url = 'http://192.168.100.10'
    if state:
        response = urequests.get(f'{url}/s/000000ff00/colorFadeMs/300')
    else:
        response = urequests.get(f'{url}/s/0000000000/colorFadeMs/300')
    response.close()

    # print('response2: ' + json.dumps(response))

led = Pin(2, Pin.OUT)
sen = Pin(5, Pin.IN)
# connect_network()
while True:
    try:
        # gc.collect()
        # val = int(sen.value())
        # lights_on(True)
        sleep(3)  # 10 minut
        print("boom")
    except Exception as e:
        print(e)
        import machine
        machine.reset()
