/*
 * Nai Miris C1 - ESP32-S3 production-style data acquisition & HTTPS v2
 * Tested pin assignment from user's WORKING diagnostics:
 * GPIO1 analog moisture 1 | GPIO2 moisture 2 | GPIO4 DS18B20
 * GPIO5 DHT22 | GPIO8 BH1750 SDA | GPIO9 BH1750 SCL | ADO -> GND (0x23).
 * All sensors powered by correct 3.3 V and common GND.
 * DS18B20 DATA -> 3.3V through 4.7k resistor. DHT22 3-pin module
 * usually already has a DATA pullup. BH1750 breakout often has pullups.
 *
 * Requires Arduino IDE ESP32 core, OneWire, DallasTemperature, DHT sensor
 * library, Adafruit Unified Sensor, BH1750 (Christopher Laws), HTTPClient,
 * ArduinoJson 7.x. Board: ESP32S3 Dev Module, USB CDC On Boot Enabled.
 * This uses HTTPS with public CA verification.
 * No watering actuator: C3 receives manual irrigation logs separately.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <NetworkClientSecure.h>
#include <LittleFS.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>
#include <BH1750.h>
#include <time.h>
#include <math.h>
#include <esp_task_wdt.h>
#include <esp_system.h>
#include "secrets.h"
#ifndef WIFI_BACKUP_SSID
#define WIFI_BACKUP_SSID ""
#endif
#ifndef WIFI_BACKUP_PASSWORD
#define WIFI_BACKUP_PASSWORD ""
#endif

constexpr int SOIL1_GPIO = 1, SOIL2_GPIO = 2, DS_GPIO = 4, DHT_GPIO = 5;
constexpr int SDA_GPIO = 8, SCL_GPIO = 9;
constexpr unsigned long SAMPLE_PERIOD_MS = 5UL * 60UL * 1000UL; // Testing: one sample every 5 minutes
constexpr unsigned long WIFI_CONNECT_GRACE_MS = 30000UL;
constexpr unsigned long WIFI_CLOCK_GRACE_MS = 120000UL;
constexpr unsigned long SENSOR_WARMUP_MS = 2500UL;

constexpr uint32_t WATCHDOG_TIMEOUT_MS = 60000UL;
constexpr size_t MAX_PENDING = 288; // Up to one day in persistent flash at five-minute sampling

OneWire oneWire(DS_GPIO);
DallasTemperature soilThermometer(&oneWire);
DHT dht(DHT_GPIO, DHT22);
BH1750 bh1750;
bool bhReady = false;
uint8_t bhAddress = 0;
unsigned long lastSample = 0, lastReconnect = 0, lastWiFiAttempt = 0;
bool watchdogReady = false, storageReady = false;
uint32_t sequenceNo = 0, nextQueueId = 1;
String bootId;
struct SavedNetwork { const char *ssid; const char *password; };
const SavedNetwork savedNetworks[] = {
  {WIFI_SSID, WIFI_PASSWORD},
  {WIFI_BACKUP_SSID, WIFI_BACKUP_PASSWORD}
};
uint8_t activeNetwork = 0, failedUploads = 0;
bool networkWasConnected = false;

void startSavedNetwork(uint8_t slot) {
  activeNetwork=slot;
  lastWiFiAttempt=millis();
  failedUploads=0;
  networkWasConnected=false;
  WiFi.disconnect(false);
  WiFi.begin(savedNetworks[slot].ssid,savedNetworks[slot].password);
  // Never print passwords or device keys to Serial Monitor.
  Serial.printf("Trying saved Wi-Fi network %u\n",unsigned(slot+1));
}

void tryNextNetwork() {
  uint8_t next=(strlen(WIFI_BACKUP_SSID)>0)?uint8_t(1-activeNetwork):0;
  startSavedNetwork(next);
}

bool initQueue() {
  Preferences settings;
  if (!settings.begin("nai_https",false)) return false;
  bool initialized=settings.getBool("fs_ready",false);
  bool mounted=LittleFS.begin(false);
  // Format only on this app's first use of the dedicated flash filesystem.
  // A later mount failure must not silently erase queued measurements.
  if (!mounted && !initialized && LittleFS.format()) mounted=LittleFS.begin(false);
  if (!mounted) { settings.end(); Serial.println("ERROR: flash queue unavailable; not formatting existing queue"); return false; }
  settings.putBool("fs_ready",true); settings.end();
  if (!LittleFS.exists("/queue") && !LittleFS.mkdir("/queue")) return false;
  File dir=LittleFS.open("/queue");
  for(File f=dir.openNextFile();f;f=dir.openNextFile()) {
    String name=f.name();
    if(name.endsWith(".json")) { uint32_t id=strtoul(name.c_str(),nullptr,10); if(id>=nextQueueId) nextQueueId=id+1; }
    f.close();
  }
  return true;
}

String oldestQueueFile(size_t &count) {
  count=0; String oldest;
  File dir=LittleFS.open("/queue");
  for(File f=dir.openNextFile();f;f=dir.openNextFile()) {
    String name=f.name();
    if(name.endsWith(".json")) { count++; if(!oldest.length()||name<oldest) oldest=name; }
    f.close();
  }
  return oldest.length()?String("/queue/")+oldest:String();
}

bool i2cFound(uint8_t a) {
  Wire.beginTransmission(a);
  return Wire.endTransmission() == 0;
}

String timeISO8601UTC() {
  time_t rawTime = time(nullptr);
  if (rawTime < 1700000000) return String();  // not yet NTP-synchronized
  struct tm utc;
  gmtime_r(&rawTime, &utc);
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return String(buf);
}

void addNullableNumber(JsonDocument &doc, const char *key, float value, float minV, float maxV) {
  if (isfinite(value) && value >= minV && value <= maxV) doc[key] = round(value * 100.0f) / 100.0f;
  else doc[key] = nullptr;
}

int readAverageADC(int gpio) {
  long sum = 0;
  for (int i = 0; i < 16; ++i) { sum += analogRead(gpio); delay(4); }
  return int(sum / 16);
}

String acquireJson() {
  // DHT22 sensor should not be polled faster than once every ~2 s.
  soilThermometer.requestTemperatures();
  const float soilC = soilThermometer.getTempCByIndex(0);
  const float airC = dht.readTemperature();
  const float rh = dht.readHumidity();
  if (!bhReady) {
    if (i2cFound(0x23)) bhAddress = 0x23;
    else if (i2cFound(0x5C)) bhAddress = 0x5C;
    if (bhAddress) bhReady = bh1750.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, bhAddress, &Wire);
  }
  float lux = NAN;
  if (bhReady) {
    lux = bh1750.readLightLevel();
    if (!isfinite(lux) || lux < 0) bhReady = false;
  }
  int adc1 = readAverageADC(SOIL1_GPIO);
  int adc2 = readAverageADC(SOIL2_GPIO);

  JsonDocument doc;
  doc["schema_version"] = "1.0.0";
  doc["node_id"] = NODE_ID;
  doc["zone_id"] = ZONE_ID;
  doc["boot_id"] = bootId;
  doc["firmware_version"] = "2.1.0-https-wifi-fallback";
  doc["wifi_network_slot"] = unsigned(activeNetwork+1);
  doc["watchdog_enabled"] = watchdogReady;
  doc["reset_reason"] = int(esp_reset_reason());
  doc["sequence_number"] = ++sequenceNo;
  const String stamp = timeISO8601UTC();
  if (stamp.length()) doc["timestamp"] = stamp;
  else doc["timestamp"] = nullptr;
  doc["uptime_ms"] = millis();
  doc["soil_moisture_1_adc"] = adc1;
  doc["soil_moisture_2_adc"] = adc2;
  doc["soil_moisture_1_mv"] = analogReadMilliVolts(SOIL1_GPIO); // diagnostic estimate
  doc["soil_moisture_2_mv"] = analogReadMilliVolts(SOIL2_GPIO); // diagnostic estimate
  addNullableNumber(doc, "soil_temperature_c", soilC, -55, 125);
  if (soilC == -127 || soilC == 85) doc["soil_temperature_c"] = nullptr;
  addNullableNumber(doc, "air_temperature_c", airC, -40, 80);
  addNullableNumber(doc, "relative_humidity_pct", rh, 0, 100);
  addNullableNumber(doc, "light_lux", lux, 0, 120000);
  doc["rain_detected"] = nullptr; // No rain sensor installed on this circuit
  doc["wifi_rssi_dbm"] = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
  doc["data_origin"] = "real";
  String payload;
  serializeJson(doc, payload);
  return payload;
}

void queueReading(const String &payload) {
  if(!storageReady) { Serial.println("ERROR: reading could not be queued; check flash storage"); return; }
  size_t count; oldestQueueFile(count);
  if(count>=MAX_PENDING) { Serial.println("ERROR: offline queue full; new reading dropped, older readings preserved"); return; }
  char path[40]; snprintf(path,sizeof(path),"/queue/%010lu.json",(unsigned long)nextQueueId++);
  const String temp=String(path)+".tmp";
  File file=LittleFS.open(temp,FILE_WRITE);
  if(!file) { Serial.println("ERROR: cannot create queue file"); return; }
  size_t written=file.print(payload); file.flush(); file.close();
  if(written!=payload.length()||!LittleFS.rename(temp,path)) Serial.println("ERROR: queue write incomplete; reading not confirmed saved");
}

void sendOldest() {
  if(!storageReady||WiFi.status()!=WL_CONNECTED||time(nullptr)<1700000000) return;
  size_t count; String path=oldestQueueFile(count); if(!path.length()) return;
  File file=LittleFS.open(path,FILE_READ); if(!file) return;
  String payload=file.readString(); file.close();
  JsonDocument packet;
  if(deserializeJson(packet,payload)!=DeserializationError::Ok) { Serial.println("ERROR: corrupt queue entry; retained for diagnosis"); return; }
  // Recover a pre-NTP sample's acquisition time only within its original boot.
  if(packet["timestamp"].isNull() && String(packet["boot_id"].as<const char*>())==bootId) {
    time_t captured=time(nullptr)-(uint32_t(millis()-packet["uptime_ms"].as<uint32_t>())/1000);
    struct tm utc; gmtime_r(&captured,&utc); char stamp[25]; strftime(stamp,sizeof(stamp),"%Y-%m-%dT%H:%M:%SZ",&utc);
    packet["timestamp"]=stamp; payload=String(); serializeJson(packet,payload);
  }
  NetworkClientSecure client; client.useBuiltinCACertBundle();
  client.setHandshakeTimeout(10); client.setConnectionTimeout(5000);
  HTTPClient http;
  http.setConnectTimeout(5000); http.setTimeout(10000);
  http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
  if(!http.begin(client,UPLOAD_URL)) return;
  http.addHeader("Content-Type","application/json");
  http.addHeader("Authorization",String("Bearer ")+DEVICE_TOKEN);
  int status=http.POST(payload); String response=http.getString(); http.end();
  // Positive HTTP codes prove the host was reachable. Authentication/server
  // errors should retain the reading, not cause needless Wi-Fi switching.
  if(status>0) failedUploads=0;
  else if(++failedUploads>=3) {
    Serial.println("Three network upload failures; trying another saved Wi-Fi");
    tryNextNetwork();
  }
  JsonDocument ack;
  String expected=String(packet["node_id"].as<const char*>())+"_"+packet["boot_id"].as<const char*>()+"_"+String(packet["sequence_number"].as<uint32_t>());
  if(status==200 && deserializeJson(ack,response)==DeserializationError::Ok && ack["ok"]==true && String(ack["record_id"].as<const char*>())==expected) {
    if(LittleFS.remove(path)) Serial.printf("SAVED BY CLOUD: %s | remaining=%u\n",expected.c_str(),unsigned(count-1));
  } else Serial.printf("Upload not confirmed: HTTP %d | queued reading retained\n",status);
}

void reconnectNetwork() {
  if(WiFi.status()==WL_CONNECTED) {
    if(!networkWasConnected) {
      networkWasConnected=true;
      Serial.printf("Connected to saved Wi-Fi network %u\n",unsigned(activeNetwork+1));
    }
    // TLS cannot upload until the clock is synchronized. A Wi-Fi connection
    // without working NTP may have no usable internet access.
    if(time(nullptr)<1700000000 && millis()-lastWiFiAttempt>=WIFI_CLOCK_GRACE_MS) {
      Serial.println("Clock synchronization unavailable; trying another saved Wi-Fi");
      tryNextNetwork();
    }
    return;
  }
  if(networkWasConnected || millis()-lastWiFiAttempt>=WIFI_CONNECT_GRACE_MS) tryNextNetwork();
}

void setup() {
  Serial.begin(115200);
#if ARDUINO_USB_CDC_ON_BOOT
  // Logging must never hold up HTTPS when no Serial Monitor is attached.
  Serial.setTxTimeoutMs(0);
#endif
  esp_task_wdt_config_t watchdogConfig = {};
  watchdogConfig.timeout_ms = WATCHDOG_TIMEOUT_MS;
  watchdogConfig.idle_core_mask = 0;
  watchdogConfig.trigger_panic = true;
  esp_err_t watchdogResult = esp_task_wdt_reconfigure(&watchdogConfig);
  if (watchdogResult == ESP_ERR_INVALID_STATE) {
    watchdogResult = esp_task_wdt_init(&watchdogConfig);
  }
  if (watchdogResult == ESP_OK) {
    watchdogReady = esp_task_wdt_add(nullptr) == ESP_OK;
  }
  delay(1000);
  Serial.println("=== Nai Miris C1 / ESP32-S3 Wi-Fi HTTPS ===");
  Serial.println("Sensor GPIO: moisture=1/2, DS=4, DHT=5, BH SDA=8 SCL=9");
  bootId = String((uint32_t)(ESP.getEfuseMac() & 0xFFFFFFFF), HEX) + "-" + String(esp_random(), HEX);
  storageReady=initQueue();
  analogReadResolution(12);
  analogSetPinAttenuation(SOIL1_GPIO, ADC_11db);
  analogSetPinAttenuation(SOIL2_GPIO, ADC_11db);
  pinMode(SOIL1_GPIO, INPUT);
  pinMode(SOIL2_GPIO, INPUT);
  soilThermometer.begin();
  dht.begin();
  Wire.begin(SDA_GPIO, SCL_GPIO);
  Wire.setTimeOut(50);
  Wire.setClock(100000);
  delay(100);
  if (i2cFound(0x23)) bhAddress = 0x23;
  else if (i2cFound(0x5C)) bhAddress = 0x5C;
  if (bhAddress) bhReady = bh1750.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, bhAddress, &Wire);
  Serial.printf("DS18B20 found=%d | BH1750=%s\n", soilThermometer.getDeviceCount(), bhReady ? "OK" : "MISSING");
  WiFi.mode(WIFI_STA);
  // Our manager explicitly alternates credentials; avoid a competing driver
  // retry repeatedly reconnecting to the failed network.
  WiFi.setAutoReconnect(false);
  startSavedNetwork(0);
  // Initial NTP sync happens asynchronously once Wi-Fi connects.
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  delay(SENSOR_WARMUP_MS);
  // First sample now to verify installation, afterwards every 5 minutes.
  lastSample = millis() - SAMPLE_PERIOD_MS;
}

void loop() {
  if(watchdogReady) esp_task_wdt_reset();
  unsigned long now=millis();
  reconnectNetwork();
  if(now-lastSample>=SAMPLE_PERIOD_MS) {
    lastSample=now; queueReading(acquireJson());
  }
  if(now-lastReconnect>=15000UL) {
    lastReconnect=now; sendOldest();
  }
  delay(20);
}
