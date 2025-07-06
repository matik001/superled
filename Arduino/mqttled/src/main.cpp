#include <mqtt_8266.h>

// #define DEBUG

#ifdef DEBUG
#define PRINT(...) Serial.printf(__VA_ARGS__)
#define PRINTLN(...) Serial.println(__VA_ARGS__)
#else
#define PRINT(...)
#define PRINTLN(...)
#endif

String HOUSE_NAME = "rycerska";
String ROOM_NAME = "living_room";

const int ADC_PIN = A0;
const int SWITCH_PIN = 5;

const int ADC_TOLERANCE = 7;

char topic[50];

void setup()
{
#ifdef DEBUG
  Serial.begin(9600);
#endif
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  ("custom/update/" + HOUSE_NAME + "/" + ROOM_NAME).toCharArray(topic, 50);
}

void sendADC(int adc_val)
{
  PRINT("Sending adc %d \n", adc_val);
  auto msg = "{\"adc\": " + String(adc_val) + "}";
  PRINTLN(msg.c_str());
  bool successful = mqttClient.publish(topic, msg.c_str());
  PRINTLN(successful ? "Sent OK" : "Sent error");
  PRINT("MQTT Connection failed, state: %d\n", mqttClient.state());
}

void sendSwitch(int switch_state)
{
  PRINT("Sending switch %d \n", switch_state);
  auto msg = "{\"state\": \"" + String(switch_state ? "ON" : "OFF") + "\"}";
  PRINTLN(msg.c_str());

  bool successful = mqttClient.publish(topic, msg.c_str());
  PRINTLN(successful ? "Sent OK" : "Sent error");
  PRINT("MQTT Connection failed, state: %d\n", mqttClient.state());
}

int prev_switch = -1;
int prev_adc = -1;
void loop()
{
  if (ensure_connection())
  {
    unsigned long loop_time = millis();
    // Yielding for 100ms
    while (millis() - loop_time < 30)
    {
      yield();
    }
    // yield();
    // yield();
    // yield();
    // yield();
    // yield();
    // yield();
    // yield();
    // yield();
    // yield();
    // yield();

    int adc_val = analogRead(ADC_PIN);
    int switch_val = digitalRead(SWITCH_PIN);

    if (abs(adc_val - prev_adc) > ADC_TOLERANCE)
    {
      prev_adc = adc_val;
      int newVal = adc_val;
      // Serial.println("Change adc");
      sendADC(newVal);
    }
    if (switch_val != prev_switch)
    {
      prev_switch = switch_val;
      // Serial.println("Change switch");
      sendSwitch(switch_val);
    }
  }
  else
  {
    delay(1000);
  }
}