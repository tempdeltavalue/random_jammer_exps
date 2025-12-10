#include <SPI.h>       // Для зв'язку nRF24L01 по SPI
#include <nRF24L01.h>    // Бібліотека nRF24L01
#include <RF24.h>        // Бібліотека nRF24L01

// --- НАЛАШТУВАННЯ NRF24L01 ДЛЯ NodeMCU / Wemos D1 Mini ---
// CE до D4 (GPIO2)
// CSN до D8 (GPIO15)
// SCK до D5 (GPIO14)
// MOSI до D7 (GPIO13)
// MISO до D6 (GPIO12)
RF24 radio(D4, D8); // Ініціалізація nRF24L01: CE_PIN, CSN_PIN

const byte address[6] = "00001"; // Та сама адреса, що й на передавачі (Arduino Nano)

// Змінна для зберігання отриманих даних синусоїди
int16_t receivedSineData;

// Для відстеження втрати сигналу
unsigned long lastReceivedTime = 0;
const long signalTimeout = 500; // Час в мс, після якого вважаємо сигнал втраченим

void setup() {
  Serial.begin(115200); // Швидкість Serial Monitor для налагодження
  delay(100);
  Serial.println("NodeMCU/Wemos - nRF24L01 Sine Wave Receiver");

  // --- ІНІЦІАЛІЗАЦІЯ NRF24L01 ---
  if (!radio.begin()) {
    Serial.println("ПОМИЛКА: nRF24L01 не знайдено або неправильне підключення!");
    while (1); // Зупинити виконання, якщо модуль не знайдено
  }
  Serial.println("nRF24L01 ініціалізовано.");

  // Відкриття каналу для читання (Pipe 0)
  radio.openReadingPipe(0, address); 
  
  // ==========================================================
  // --- !!! ВАЖЛИВО: ЦІ ПАРАМЕТРИ ПОВИННІ ЗБІГАТИСЯ З ПЕРЕДАВАЧЕМ !!! ---
  radio.setPALevel(RF24_PA_MAX);       // <--- ЗМІНЕНО НА MAX (як на передавачі)
  radio.setDataRate(RF24_1MBPS);       // <--- ЗМІНЕНО НА 1MBPS (як на передавачі)
  radio.setChannel(76);                // Та самий фіксований канал
  radio.setAutoAck(true);              // <--- ДОДАНО: УВІМКНЕНО Auto-ACK (як на передавачі)
  radio.enableDynamicPayloads();       // <--- ДОДАНО: УВІМКНЕНО динамічні пакети (як на передавачі)
  // ==========================================================

  radio.startListening();            // Перемикання модуля в режим приймача

  // Для відображення налаштувань
  Serial.print("Канал: ");
  Serial.println(radio.getChannel());
  Serial.print("Швидкість передачі: ");
  switch (radio.getDataRate()) {
    case RF24_250KBPS: Serial.println("250 KBPS"); break;
    case RF24_1MBPS:   Serial.println("1 MBPS");   break;
    case RF24_2MBPS:   Serial.println("2 MBPS");   break;
  }
  Serial.print("Потужність PA (приймача): ");
  switch (radio.getPALevel()) {
    case RF24_PA_MIN:  Serial.println("MIN");  break;
    case RF24_PA_LOW:  Serial.println("LOW");  break;
    case RF24_PA_HIGH: Serial.println("HIGH"); break;
    case RF24_PA_MAX:  Serial.println("MAX");  break;
  }
  Serial.println("Очікування даних синусоїди...");
}

void loop() {
  // Перевірка наявності даних від nRF24L01
  if (radio.available()) {
    // Якщо є дані, читаємо їх
    radio.read(&receivedSineData, sizeof(receivedSineData));
    lastReceivedTime = millis(); // Оновлюємо час останнього отримання даних

    // Виводимо отримане значення
    Serial.println(receivedSineData);
  } else {
    // Якщо дані не надходять протягом певного часу, виводимо повідомлення
    static bool printedTimeoutMessage = false; // Статична змінна, щоб зберігати стан

    if (millis() - lastReceivedTime > signalTimeout) {
      if (!printedTimeoutMessage) {
        Serial.println("------ Втрата сигналу або сильні перешкоди! ------");
        printedTimeoutMessage = true; // Позначаємо, що повідомлення вже надруковано
      }
    } else {
      printedTimeoutMessage = false; // Скидаємо прапорець, якщо дані знову надходять
    }
  }
  
  // Додаємо затримку, щоб дати ESP час обробити внутрішні завдання та Serial вивід.
  delay(20); 
}