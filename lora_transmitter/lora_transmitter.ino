#include <SPI.h>
#include <RadioLib.h>

// --- Pin Definitions for Ai-Thinker Ra-01/Ra-02 with ESP8266 (NodeMCU) ---
#define NSS_PIN  15    // ESP8266 D8 (GPIO15) - NSS pin for the LoRa module
#define RST_PIN  5     // ESP8266 D1 (GPIO5) - Reset pin for the LoRa module
#define DIO0_PIN 4     // ESP8266 D2 (GPIO4) - DIO0 pin for the LoRa module (interrupt)

// Create an SX1278 object with the defined pins
SX1278 radio = new Module(NSS_PIN, DIO0_PIN, RST_PIN);

// --- Global Variables ---
// Array of messages to send (UPDATED and SWAPPED)
const char* messages[] = {
  "Love is all you need", // Message 1 (19 characters)
  "Hello humans"          // Message 2 (12 characters)
};
// Calculate the number of messages in the array
const int NUM_MESSAGES = sizeof(messages) / sizeof(messages[0]);
int currentMessageIndex = 0; // Index of the current message to send, starting from the first
unsigned long lastSendTime = 0; // Stores the time of the last transmission of the current message
unsigned long messagePhaseStartTime = 0; // Stores the start time of the current phase (sending message or pausing)

// Define operational states
enum State {
  SENDING_MESSAGE, // State when we are sending the current message repeatedly
  PAUSING          // State when we are pausing before switching messages
};
State currentState = SENDING_MESSAGE; // Initial state - sending message

const long REPEAT_INTERVAL_MS = 50; // Interval between repeated transmissions of ONE message
const long MESSAGE_SEND_DURATION_MS = 1000; // Duration of sending ONE message before transitioning to the pause state
const long PAUSE_DURATION_MS = 500; // Duration of the pause before switching to the next message

// --- FSK Parameters (MUST EXACTLY MATCH THE PYTHON RECEIVER) ---
// --- UPDATED to match Python script ---
const float FSK_BIT_RATE_KBPS = 48.0005;   // FSK Bit Rate in kbps
const float FSK_FREQ_DEV_KHZ = 50.0;       // FSK Frequency Deviation in kHz
const float FSK_RX_BW_KHZ = 200.0;         // FSK Receiver Bandwidth in kHz (a suitable value for the new parameters)

void setup() {
  Serial.begin(115200); // Initialize serial port for debug output
  while (!Serial); // Wait until the serial port is ready (especially useful for boards with USB-Serial)

  Serial.println(F("--- ESP8266 with Ai-Thinker Ra-01 (FSK Sender - Streaming Messages) ---")); // Updated program title
  Serial.print(F("Current time (ms): ")); Serial.println(millis()); // Print current time since startup

  // Initialize Ra-01 module in FSK mode
  Serial.println(F("\nInitializing Ai-Thinker Ra-01 module in FSK mode..."));

  // Call the beginFSK function to configure the SX1278 module
  // Parameters: frequency, bit rate, frequency deviation, receiver bandwidth, output power, preamble, CRC
  int state = radio.beginFSK(
    433.0,                  // Frequency (MHz) - must match receiver frequency
    FSK_BIT_RATE_KBPS,      // Bit rate (kbps) - MUST MATCH
    FSK_FREQ_DEV_KHZ,       // Frequency deviation (kHz) - MUST MATCH
    FSK_RX_BW_KHZ,          // Receiver bandwidth (kHz)
    17,                     // Output power (dBm) - a good value for transmission
    16,                     // Preamble length - number of preamble bits
    false                   // Disable CRC (checksum)
  );

  // Check initialization status
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println(F("SX1278 LoRa module initialized in FSK mode successfully!"));
  } else {
    Serial.print(F("FATAL ERROR: Failed to initialize SX1278 in FSK mode, code: "));
    Serial.println(state);
    while(true); // Stick here if initialization failed to prevent further errors
  }

  Serial.println(F("LoRa module ready for continuous FSK transmission."));
  Serial.print(F("FSK Bit Rate: ")); Serial.print(FSK_BIT_RATE_KBPS); Serial.println(F(" kbps"));
  Serial.print(F("FSK Freq Dev: ")); Serial.print(FSK_FREQ_DEV_KHZ); Serial.println(F(" kHz"));
  Serial.print(F("FSK Rx BW: ")); Serial.print(FSK_RX_BW_KHZ); Serial.println(F(" kHz"));

  // Initialize the start time of the current phase
  messagePhaseStartTime = millis();
  lastSendTime = millis(); // Also initialize lastSendTime for the first transmission
}

void loop() {
  unsigned long currentTime = millis();

  switch (currentState) {
    case SENDING_MESSAGE:
      // Check time to transition to the pause phase
      if (currentTime - messagePhaseStartTime >= MESSAGE_SEND_DURATION_MS) {
        currentState = PAUSING; // Change state to "pausing"
        messagePhaseStartTime = currentTime; // Start time tracking for the pause
        Serial.println(F("\n--- Starting pause (0.5 sec) ---"));
      } else {
        // Repeatedly send the current message if it's not time to pause
        if (currentTime - lastSendTime >= REPEAT_INTERVAL_MS) {
          lastSendTime = currentTime; // Update time of last transmission

          const char* messageToSend = messages[currentMessageIndex]; // Get the current message from the array

          Serial.print(F("Sending packet: \""));
          Serial.print(messageToSend);
          Serial.print(F("\" (Length: "));
          Serial.print(strlen(messageToSend));
          Serial.println(F(" bytes)"));

          // Send the message
          int state = radio.transmit((uint8_t*)messageToSend, strlen(messageToSend));

          // Check transmission status
          if (state == RADIOLIB_ERR_NONE) {
            Serial.println(F("Packet sent successfully!"));
          } else if (state == RADIOLIB_ERR_TX_TIMEOUT) {
            Serial.println(F("WARNING: Packet transmission timed out!"));
          } else {
            Serial.print(F("ERROR: Failed to send packet, code: "));
            Serial.println(state);
          }
        }
      }
      break;

    case PAUSING:
      // Check time to end the pause and switch to the next message
      if (currentTime - messagePhaseStartTime >= PAUSE_DURATION_MS) {
        currentState = SENDING_MESSAGE; // Change state back to "sending message"
        messagePhaseStartTime = currentTime; // Start time tracking for the new message
        lastSendTime = currentTime; // Reset lastSendTime for the new message

        // Move to the next message in the array
        currentMessageIndex = (currentMessageIndex + 1) % NUM_MESSAGES;

        Serial.print(F("\n--- Pause ended. Switching to message: \""));
        Serial.print(messages[currentMessageIndex]);
        Serial.println(F("\" ---"));
      }
      // During pause, we don't send anything, just wait
      break;
  }

  // yield() allows ESP8266 to perform background tasks (e.g., Wi-Fi)
  // This is important for stable operation, especially if you add other functions
  yield();
}