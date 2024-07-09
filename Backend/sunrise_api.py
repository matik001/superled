import datetime

import requests


class SunriseSunsetAPI:
    def __init__(self):
        self.date:datetime.date = None
        self.sunrise_utc:datetime.time = None
        self.sunset_utc:datetime.time = None
        pass

    def is_daylight_now(self):
        if not self.is_up_to_date():
            self.update_time()
        nowtime = datetime.datetime.utcnow().time()
        return self.sunrise_utc < nowtime < self.sunset_utc

    def update_time(self):
        data = requests.get("https://api.sunrisesunset.io/json?lat=51.1309&lng=17.10175")
        json = data.json()['results']

        sunrise = datetime.datetime.strptime(json['sunrise'], "%I:%M:%S %p")
        sunset = datetime.datetime.strptime(json['sunset'], "%I:%M:%S %p")
        self.date = datetime.datetime.fromisoformat(json['date']).date()
        utc_offset = int(json['utc_offset'])
        self.sunrise_utc = (sunrise - datetime.timedelta(minutes=utc_offset)).time()
        self.sunset_utc = (sunset - datetime.timedelta(minutes=utc_offset)).time()

    def is_up_to_date(self):
        return datetime.datetime.today().date() == self.date

# test = SunriseSunsetAPI()
# print(test.is_up_to_date())
# test.update_time()
# print(test.is_up_to_date())
# print(test.date)
# print(test.sunrise_utc)
# print(test.sunset_utc)
# print(test.sunset_utc.utcoffset())
