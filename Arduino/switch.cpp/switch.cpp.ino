#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

const char* ssid = "piesikot";
const char* password = "kotipies";

String URL = "http://192.168.100.17:6767";
String HOUSE_NAME = "rycerska";
String ROOM_NAME = "living_room";

String ADC_URL = URL+"/house/" + HOUSE_NAME + "/room/" + ROOM_NAME + "/adc/";
String SWITCH_URL = URL+"/house/" + HOUSE_NAME + "/room/" + ROOM_NAME + "/switch/";

const int ADC_PIN = A0;
const int SWITCH_PIN = 5;
const int LED_PIN = 2;


const int ADC_TOLERANCE = 5;

void connect_wifi(){
  digitalWrite(LED_PIN, 0);
  WiFi.begin(ssid, password);
  Serial.println("Connecting");
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());
  digitalWrite(LED_PIN, 1);
}
void setup() {
  Serial.begin(115200); 
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
}

inline void sendGet(String url){
  WiFiClient client;
  HTTPClient http;
  http.begin(client, url.c_str());
  int httpResponseCode = http.GET();
  http.end();
}
void sendADC(int adc_val){
  sendGet(ADC_URL+String(adc_val));
}


void sendSwitch(int switch_state){
  sendGet(SWITCH_URL+String(switch_state));
}

int prev_switch = -1;
int prev_adc = -1;
void loop() {
  if(WiFi.status() == WL_CONNECTED){

    int adc_val = analogRead(ADC_PIN);
    int switch_val = digitalRead(SWITCH_PIN);

    if(abs(adc_val - prev_adc) > ADC_TOLERANCE){
      prev_adc = adc_val;
      Serial.println("Change adc");
      sendADC(adc_val);
    }
    if(switch_val != prev_switch){
      prev_switch = switch_val;
      Serial.println("Change switch");
      sendSwitch(switch_val);
    }
  }
  else {
    Serial.println("WiFi Disconnected");
    connect_wifi();
  }
}