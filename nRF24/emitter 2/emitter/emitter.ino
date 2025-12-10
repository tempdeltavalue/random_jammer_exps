#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>
#include <math.h>

// nRF24L01 pin configuration for Arduino Nano
// CE to D9
// CSN to D10
// SCK to D13
// MOSI to D11
// MISO to D12
RF24 radio(9, 10); // CE, CSN pins

const byte address[6] = "00001"; // Unique address for communication (must be the same on receiver)

const int LED_PIN = 13;       // Built-in LED pin on Arduino Nano (D13)

// --- Parameters for MULTIPLE Sinusoidal Signals per Channel ---
const int NUM_CHANNELS = 5; // CRITICAL CHANGE: Reduced from 20 to 5

// Each channel will now have THREE independently sweeping sine waves.
float baseFrequencies1[NUM_CHANNELS];
float baseFrequencies2[NUM_CHANNELS];
float baseFrequencies3[NUM_CHANNELS];

const int maxAmplitude1 = 7000;
const int maxAmplitude2 = 5000;
const int maxAmplitude3 = 4000;
const int noiseAmplitude = 1000; // Adjusted for 5 channels, can be increased if needed

float phase1[NUM_CHANNELS] = {0.0};
float phase2[NUM_CHANNELS] = {0.0};
float phase3[NUM_CHANNELS] = {0.0};

// --- Channel Hopping Configuration ---
// Adjusted channel list to 5 channels
const byte channelList[NUM_CHANNELS] = {
  76, 77, 78, 79, 80 // Reverting to original 5 channels
};
int currentChannelIndex = 0;

const long sendInterval = 10; // Send a packet and hop channels every 10 ms (100 times/sec)

unsigned long previousMillis = 0;

// --- Frequency Sweeping Parameters ---
unsigned long lastFreqChangeTime = 0;
const long freqChangeInterval = 250; // Faster: Change frequencies every 0.25 seconds
const float freqSweepRange = 4.0; // Frequencies will sweep +/- 4.0 Hz from their base

// --- Amplitude Modulation Parameters ---
unsigned long lastAmpChangeTime = 0;
const long ampChangeInterval = 750; // Faster: Change amplitude modulation every 0.75 seconds
const float ampModDepth = 0.9;
float currentAmpModFactor1[NUM_CHANNELS];
float currentAmpModFactor2[NUM_CHANNELS];
float currentAmpModFactor3[NUM_CHANNELS];

// --- Random Jump Parameters ---
unsigned long lastJumpTime = 0;
const long jumpInterval = 1000; // More Frequent: Attempt a random frequency jump every 1 second
const float jumpMinFreq = 0.1;
const float jumpMaxFreq = 9.9;


void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(LED_PIN, OUTPUT);

  randomSeed(analogRead(A0));

  for (int i = 0; i < NUM_CHANNELS; i++) {
    // Spread initial frequencies across the full range (0.1 to 9.9 Hz)
    baseFrequencies1[i] = random(10, 990) / 100.0;
    baseFrequencies2[i] = random(10, 990) / 100.0;
    baseFrequencies3[i] = random(10, 990) / 100.0;

    currentAmpModFactor1[i] = 1.0;
    currentAmpModFactor2[i] = 1.0;
    currentAmpModFactor3[i] = 1.0;
  }

  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }

  Serial.println("Arduino Nano - Multi-Channel MAX DIVERSITY Signal Emitter (5 Channels)");

  if (!radio.begin()) {
    Serial.println("ERROR: nRF24L01 not found or incorrect connection!");
    while (1) {
      digitalWrite(LED_PIN, HIGH);
      delay(50);
      digitalWrite(LED_PIN, LOW);
      delay(50);
    }
  }
  Serial.println("nRF24L01 initialized.");

  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);

  radio.openWritingPipe(address);
  radio.setPALevel(RF24_PA_MAX);
  radio.setDataRate(RF24_1MBPS);
  radio.setAutoAck(true);
  radio.enableDynamicPayloads();
  radio.setRetries(15, 15);
  radio.stopListening();

  Serial.print("Data Rate: ");
  switch (radio.getDataRate()) {
    case RF24_250KBPS: Serial.println("250 KBPS"); break;
    case RF24_1MBPS:   Serial.println("1 MBPS");   break;
    case RF24_2MBPS:   Serial.println("2 MBPS");   break;
  }
  Serial.print("PA Level: ");
  switch (radio.getPALevel()) {
    case RF24_PA_MIN:  Serial.println("MIN");  break;
    case RF24_PA_LOW:  Serial.println("LOW");  break;
    case RF24_PA_HIGH: Serial.println("HIGH"); break;
    case RF24_PA_MAX:  Serial.println("MAX");  break;
  }
  Serial.println("Starting multi-channel highly diverse signal transmission...");
  Serial.print("Number of Frequencies/Channels: ");
  Serial.println(NUM_CHANNELS);
}

void loop() {
  unsigned long currentMillis = millis();
  float timeStep = sendInterval / 1000.0;

  // --- Frequency Sweeping Logic ---
  if (currentMillis - lastFreqChangeTime >= freqChangeInterval) {
    lastFreqChangeTime = currentMillis;
    for (int i = 0; i < NUM_CHANNELS; i++) {
      float randomOffset1 = (random(-100, 100) / 100.0) * freqSweepRange;
      baseFrequencies1[i] = baseFrequencies1[i] + randomOffset1;
      if (baseFrequencies1[i] < 0.1) baseFrequencies1[i] = 0.1;
      if (baseFrequencies1[i] > 9.9) baseFrequencies1[i] = 9.9;

      float randomOffset2 = (random(-100, 100) / 100.0) * freqSweepRange;
      baseFrequencies2[i] = baseFrequencies2[i] + randomOffset2;
      if (baseFrequencies2[i] < 0.1) baseFrequencies2[i] = 0.1;
      if (baseFrequencies2[i] > 9.9) baseFrequencies2[i] = 9.9;

      float randomOffset3 = (random(-100, 100) / 100.0) * freqSweepRange;
      baseFrequencies3[i] = baseFrequencies3[i] + randomOffset3;
      if (baseFrequencies3[i] < 0.1) baseFrequencies3[i] = 0.1;
      if (baseFrequencies3[i] > 9.9) baseFrequencies3[i] = 9.9;
    }
  }

  // --- Random Jump Logic ---
  if (currentMillis - lastJumpTime >= jumpInterval) {
    lastJumpTime = currentMillis;
    for (int i = 0; i < NUM_CHANNELS; i++) {
      if (random(0, 100) < 70) {
        baseFrequencies1[i] = random(jumpMinFreq * 100, jumpMaxFreq * 100) / 100.0;
        baseFrequencies2[i] = random(jumpMinFreq * 100, jumpMaxFreq * 100) / 100.0;
        baseFrequencies3[i] = random(jumpMinFreq * 100, jumpMaxFreq * 100) / 100.0;
      }
    }
  }

  // --- Amplitude Modulation Logic ---
  if (currentMillis - lastAmpChangeTime >= ampChangeInterval) {
    lastAmpChangeTime = currentMillis;
    for (int i = 0; i < NUM_CHANNELS; i++) {
      currentAmpModFactor1[i] = 1.0 - ampModDepth + (random(0, 100) / 100.0) * ampModDepth;
      currentAmpModFactor2[i] = 1.0 - ampModDepth + (random(0, 100) / 100.0) * ampModDepth;
      currentAmpModFactor3[i] = 1.0 - ampModDepth + (random(0, 100) / 100.0) * ampModDepth;
    }
  }

  // Send data and hop channels at a controlled interval
  if (currentMillis - previousMillis >= sendInterval) {
    previousMillis = currentMillis;

    byte targetChannel = channelList[currentChannelIndex];
    radio.setChannel(targetChannel);

    float currentFreq1 = baseFrequencies1[currentChannelIndex];
    float currentFreq2 = baseFrequencies2[currentChannelIndex];
    float currentFreq3 = baseFrequencies3[currentChannelIndex];
    float currentAmp1 = maxAmplitude1 * currentAmpModFactor1[currentChannelIndex];
    float currentAmp2 = maxAmplitude2 * currentAmpModFactor2[currentChannelIndex];
    float currentAmp3 = maxAmplitude3 * currentAmpModFactor3[currentChannelIndex];

    phase1[currentChannelIndex] += 2 * PI * currentFreq1 * timeStep;
    phase2[currentChannelIndex] += 2 * PI * currentFreq2 * timeStep;
    phase3[currentChannelIndex] += 2 * PI * currentFreq3 * timeStep;

    if (phase1[currentChannelIndex] >= 2 * PI) phase1[currentChannelIndex] -= 2 * PI;
    if (phase2[currentChannelIndex] >= 2 * PI) phase2[currentChannelIndex] -= 2 * PI;
    if (phase3[currentChannelIndex] >= 2 * PI) phase3[currentChannelIndex] -= 2 * PI;

    int16_t sineValue1 = currentAmp1 * sin(phase1[currentChannelIndex]);
    int16_t sineValue2 = currentAmp2 * sin(phase2[currentChannelIndex]);
    int16_t sineValue3 = currentAmp3 * sin(phase3[currentChannelIndex]);

    int16_t combinedSineValue = sineValue1 + sineValue2 + sineValue3 + random(-noiseAmplitude, noiseAmplitude);

    if (combinedSineValue > 32767) combinedSineValue = 32767;
    if (combinedSineValue < -32768) combinedSineValue = -32768;

    struct Payload {
      byte channel;
      int16_t sineValue;
    };
    Payload dataToSend;
    dataToSend.channel = targetChannel;
    dataToSend.sineValue = combinedSineValue;

    bool success = radio.write(&dataToSend, sizeof(dataToSend));

    if (success) {
      digitalWrite(LED_PIN, HIGH);
      delay(1);
      digitalWrite(LED_PIN, LOW);
    } else {
      digitalWrite(LED_PIN, LOW);
    }

    currentChannelIndex = (currentChannelIndex + 1) % NUM_CHANNELS;
  }
}