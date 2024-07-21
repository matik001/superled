import gc
import math

from machine import Pin, ADC
from time import sleep
import urequests
# import json
import network


wlan = network.WLAN(network.STA_IF)

class NotifierAPI:
    def __init__(self, url: str, house_name: str, room_name: str, ssid: str, password: str):
        self.url = url
        self.house_name = house_name
        self.room_name = room_name
        self.ssid = ssid
        self.password = password

    def connect_network(self):
        if wlan.isconnected():
            return
        wlan.active(True)
        wlan.connect(self.ssid, self.password)
        while not wlan.isconnected():
            print('Connecting to network...')
            sleep(1)
        print("Network connected")

    def notify_detected(self):
        self.connect_network()
        response = urequests.get(f'{self.url}/house/{self.house_name}/room/{self.room_name}/detected')
        response.close()

    def notify_switch(self, mode: int): # mode is 0 or 1
        self.connect_network()
        response = urequests.get(f'{self.url}/house/{self.house_name}/room/{self.room_name}/switch/'+str(mode))
        response.close()

    def notify_adc(self, value: int):
        self.connect_network()
        response = urequests.get(f'{self.url}/house/{self.house_name}/room/{self.room_name}/adc/'+str(value))
        response.close()


notifier = NotifierAPI('http://192.168.0.87:6767', 'hetmanska', 'living_room', 'LAPA', 'staryduren123')
notifier.connect_network()

led = Pin(2, Pin.OUT)
switch = Pin(5, Pin.IN, Pin.PULL_UP)
adc = ADC(0)

val_switch_prev = -1
val_adc_prev = -1
adc_tolerance = 200
while True:
    try:
        gc.collect()
        val_adc = adc.read_u16()
        val_switch = int(switch.value())
        if val_switch != val_switch_prev:
            print("Changed switch: " + str(val_switch))
            val_switch_prev = val_switch
            notifier.notify_switch(val_switch)
        if math.fabs(val_adc_prev - val_adc) > adc_tolerance:
            print("Changed adc: " + str(val_adc))
            val_adc_prev = val_adc
            notifier.notify_adc(val_adc)

    except Exception as e:
        print(e)
        import machine
        machine.reset()
