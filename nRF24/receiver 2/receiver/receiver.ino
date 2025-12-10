#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>
#include <arduinoFFT.h>
#include <ArduinoJson.h>

// --- WiFi Configuration ---
const char* ssid = "Slavik";
const char* password = "20111977";

// --- Flask App URL (Local IP) ---
const char* flaskAppUrl = "http://192.168.1.17:5000/receive_fft";

// --- nRF24L01 Pin Configuration for NodeMCU 12E (ESP8266) ---
#define NRF_CE_PIN  D4
#define NRF_CSN_PIN D8
RF24 radio(NRF_CE_PIN, NRF_CSN_PIN);

// --- Emitter's Channel List (MUST EXACTLY MATCH EMITTER'S CONFIGURATION!) ---
const byte channelList[] = {
  76, 77, 78, 79, 80 // 5 channels
};
const int numChannels = sizeof(channelList) / sizeof(channelList[0]);
int currentChannelIndex = 0;

// --- FFT Parameters ---
#define SAMPLES 32 // CRITICAL CHANGE: Reduced from 64 to 32
// SAMPLING_FREQ_PER_CHANNEL: 1 sample every 50ms for each channel -> 20 Hz.
#define SAMPLING_FREQ_PER_CHANNEL 20.0

double vReal[SAMPLES];
double vImag[SAMPLES];

ArduinoFFT FFT = ArduinoFFT(vReal, vImag, SAMPLES, SAMPLING_FREQ_PER_CHANNEL);

int16_t channelDataBuffers[numChannels][SAMPLES];
int channelDataCounts[numChannels] = {0};

struct Payload {
  byte channel;
  int16_t sineValue;
};

const byte nrf_address[6] = "00001";

unsigned long lastFftSendTime = 0;
const long fftSendInterval = 50; // Check and send every 50ms (frontend fetches every 20ms)

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("--- ESP8266 NodeMCU - nRF24L01 FFT Receiver ---");

  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Target Flask URL: ");
  Serial.println(flaskAppUrl);

  if (!radio.begin()) {
    Serial.println("ERROR: nRF24L01 not found or incorrect connection!");
    while (1) { delay(100); }
  }
  Serial.println("nRF24L01 initialized.");

  radio.openReadingPipe(1, nrf_address);
  radio.setPALevel(RF24_PA_MAX);
  radio.setDataRate(RF24_1MBPS);
  radio.setAutoAck(true);
  radio.enableDynamicPayloads();
  radio.setRetries(15, 15);

  radio.setChannel(channelList[currentChannelIndex]);
  radio.startListening();

  Serial.print("Initial Listening Channel: ");
  Serial.println(radio.getChannel());
  Serial.print("Listening for data on ");
  Serial.print(numChannels);
  Serial.println(" channels...");
}

void loop() {
  static unsigned long lastHopTime = 0;
  const long hopInterval = 10; // Emitter's sendInterval in milliseconds

  if (millis() - lastHopTime >= hopInterval) {
    lastHopTime = millis();
    currentChannelIndex = (currentChannelIndex + 1) % numChannels;
    radio.setChannel(channelList[currentChannelIndex]);
  }

  if (radio.available()) {
    Payload receivedData;
    radio.read(&receivedData, sizeof(receivedData));

    byte receivedChannel = receivedData.channel;
    int16_t sineValue = receivedData.sineValue;

    int channelIdx = -1;
    for (int i = 0; i < numChannels; i++) {
      if (channelList[i] == receivedChannel) {
        channelIdx = i;
        break;
      }
    }

    if (channelIdx != -1) {
      if (channelDataCounts[channelIdx] < SAMPLES) {
        channelDataBuffers[channelIdx][channelDataCounts[channelIdx]] = sineValue;
        channelDataCounts[channelIdx]++;
      }
    } else {
      Serial.println("Unknown Channel!");
    }
  }

  unsigned long currentMillis = millis();
  if (currentMillis - lastFftSendTime >= fftSendInterval) {
    lastFftSendTime = currentMillis;

    for (int i = 0; i < numChannels; i++) {
      if (channelDataCounts[i] == SAMPLES) { // Only process and send if buffer is full
        for (int j = 0; j < SAMPLES; j++) {
          vReal[j] = (double)channelDataBuffers[i][j];
          vImag[j] = 0.0;
        }

        FFT.dcRemoval(vReal, SAMPLES);
        FFT.windowing(vReal, SAMPLES, FFT_WIN_TYP_HAMMING, FFT_FORWARD);
        FFT.compute(vReal, vImag, SAMPLES, FFT_FORWARD);
        FFT.complexToMagnitude(vReal, vImag, SAMPLES);

        double peakFrequency = FFT.majorPeak(vReal, SAMPLES, SAMPLING_FREQ_PER_CHANNEL);

        StaticJsonDocument<4096> doc;
        doc["channel"] = channelList[i];
        doc["sampling_freq"] = SAMPLING_FREQ_PER_CHANNEL;
        doc["peak_frequency"] = peakFrequency;

        JsonArray fft_magnitudes = doc.createNestedArray("magnitudes");
        for (int j = 0; j < SAMPLES / 2; j++) { // SAMPLES/2 will now be 16 bins
          fft_magnitudes.add(vReal[j]);
        }

        String jsonPayload;
        serializeJson(doc, jsonPayload);

        WiFiClient client;
        HTTPClient http;
        http.begin(client, flaskAppUrl);
        http.addHeader("Content-Type", "application/json");

        int httpResponseCode = http.POST(jsonPayload);

        if (httpResponseCode <= 0) {
          Serial.print("  HTTP Error for Ch ");
          Serial.print(channelList[i]);
          Serial.print(": ");
          Serial.println(http.errorToString(httpResponseCode).c_str());
        }
        http.end();

        channelDataCounts[i] = 0; // Reset buffer count for this channel
      }
    }
  }
}