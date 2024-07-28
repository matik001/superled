import time

from machine import Pin, ADC

led = Pin(2, Pin.OUT)

while True:
    led.value(not led.value())
    time.sleep_ms(1000)