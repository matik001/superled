// #define DEBUG

#include <ESP8266WiFi.h>
#include <PubSubClient.h>

#ifdef DEBUG
#define PRINT(...) Serial.printf(__VA_ARGS__)
#define PRINTLN(...) Serial.println(__VA_ARGS__)
#else
#define PRINT(...)
#define PRINTLN(...)
#endif

const char *ssid = "Piesikot";
const char *password = "kotipies";

const char *mqtt_broker = "192.168.100.17";
const char *mqtt_username = "matik";
const char *mqtt_password = "qweqwe123";
const int mqtt_port = 1883;

const int LED_PIN = 15;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

void connect_wifi()
{
    digitalWrite(LED_PIN, 1);
    WiFi.begin(ssid, password);
    // Serial.println("Connecting");
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }
    // Serial.println("");
    // Serial.print("Connected to WiFi network with IP Address: ");
    // Serial.println(WiFi.localIP());
    digitalWrite(LED_PIN, 0);
}

String client_id = "";

bool ensure_connection()
{
    if (client_id.length() == 0)
    {
        client_id = "esp32-mqttClient-";
        client_id += String(WiFi.macAddress());
    }

    PRINTLN("CHECKING WIFI");
    if (WiFi.status() != WL_CONNECTED)
    {
        connect_wifi();
        if (WiFi.status() != WL_CONNECTED)
            return false;
    }
    PRINTLN("WIFI CONNECTED");

    if (!mqttClient.connected())
    {
        // Serial.printf("The mqttClient %s connects to the public MQTT broker\n", client_id.c_str());
        PRINTLN("CONNECTING MQTT");

        mqttClient.setServer(mqtt_broker, mqtt_port);
        mqttClient.setBufferSize(512);
        if (!mqttClient.connect(client_id.c_str(), mqtt_username, mqtt_password))
        {
            // Serial.print("failed with state ");
            // Serial.print(mqttClient.state());
            // delay(2000);
            return false;
        }
    }

    PRINTLN("MQTT CONNECTED");
    PRINTLN("");

    // mqttClient.setCallback(callback);
    // mqttClient.subscribe
    if (!mqttClient.loop())
        return false;
    return true;
}