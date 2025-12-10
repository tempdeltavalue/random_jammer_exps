#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>
#include <math.h> // Для функції sin()

// nRF24L01 pin configuration for Arduino Nano
// CE to D9
// CSN to D10
// SCK to D13
// MOSI to D11
// MISO to D12
RF24 radio(9, 10); // CE, CSN pins

const byte address[6] = "00001"; // Унікальна адреса для зв'язку (має бути така ж на приймачі)

const int LED_PIN = 13;       // Вбудований LED пін на Arduino Nano (D13)

// Параметри синусоїдального сигналу
const float amplitude = 5000.0; // Максимальна амплітуда для int16_t (щоб уникнути переповнення)
const float frequency = 1.0;    // Частота синусоїди в Гц (один цикл за секунду)
const int   sampleRate = 500;   // Кількість відліків синусоїди за секунду (висока роздільна здатність)

unsigned long previousMillis = 0;
// Тепер додамо інтервал для більш контрольованої відправки
const long sendInterval = 20; // Надсилати кожні 20 мс (50 відправок/сек) - це повільніше, ніж раніше

void setup() {
  Serial.begin(115200); // Швидкість Serial Monitor для налагодження
  delay(100);

  // Конфігурація LED піна як OUTPUT
  pinMode(LED_PIN, OUTPUT);

  // Індикація початку ініціалізації: 3 коротких блимання
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }

  Serial.println("Arduino Nano - Sine Wave Emitter (Reliable Mode)");

  // Ініціалізація nRF24L01
  if (!radio.begin()) {
    Serial.println("ERROR: nRF24L01 not found or incorrect connection!");
    // Якщо ініціалізація не вдається, LED буде швидко блимати
    while (1) {
      digitalWrite(LED_PIN, HIGH);
      delay(50);
      digitalWrite(LED_PIN, LOW);
      delay(50);
    }
  }
  Serial.println("nRF24L01 ініціалізовано.");

  // Індикація успішної ініціалізації: 1 довге блимання
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);

  radio.openWritingPipe(address);   // Відкриваємо канал для запису
  
  // --- НАЛАШТУВАННЯ ДЛЯ НАДІЙНОГО ЗВ'ЯЗКУ ---
  radio.setPALevel(RF24_PA_MAX);    // Максимальна потужність передавача (для найкращого діапазону)
  radio.setDataRate(RF24_1MBPS);    // Середня швидкість передачі даних (більш стабільна)
  radio.setChannel(76);             // Фіксований канал (має збігатися з приймачем)
  radio.setAutoAck(true);           // УВІМКНУТИ Auto-ACK (передавач чекатиме підтвердження)
  radio.enableDynamicPayloads();    // Дозволити динамічні пакети (може допомогти)
  radio.setRetries(15, 15);         // Максимальна кількість повторних спроб (15 разів, з 1500 мкс затримкою)

  radio.stopListening();            // Перемикаємося в режим передавача

  Serial.print("Канал: ");
  Serial.println(radio.getChannel());
  Serial.print("Швидкість передачі: ");
  switch (radio.getDataRate()) {
    case RF24_250KBPS: Serial.println("250 KBPS"); break;
    case RF24_1MBPS:   Serial.println("1 MBPS");   break;
    case RF24_2MBPS:   Serial.println("2 MBPS");   break;
  }
  Serial.print("Потужність PA: ");
  switch (radio.getPALevel()) {
    case RF24_PA_MIN:  Serial.println("MIN");  break;
    case RF24_PA_LOW:  Serial.println("LOW");  break;
    case RF24_PA_HIGH: Serial.println("HIGH"); break;
    case RF24_PA_MAX:  Serial.println("MAX");  break;
  }
  Serial.println("Відправка синусоїди...");
}

void loop() {
  unsigned long currentMillis = millis();

  // Відправляємо дані з контрольованим інтервалом
  if (currentMillis - previousMillis >= sendInterval) {
    previousMillis = currentMillis;

    // Обчислення поточної точки синусоїди
    float rawSineValue = sin(2 * PI * frequency * (currentMillis / 1000.0));
    int16_t sineData = (int16_t)(rawSineValue * amplitude);

    // Відправка даних та перевірка успіху (оскільки Auto-ACK увімкнено)
    bool success = radio.write(&sineData, sizeof(sineData));

    if (success) {
      Serial.print("Відправлено: ");
      Serial.print(sineData);
      Serial.println(" -- Успішно.");
      digitalWrite(LED_PIN, HIGH); // Увімкнути LED на короткий час
      delay(1);                    // Дуже коротке блимання
      digitalWrite(LED_PIN, LOW);
    } else {
      Serial.print("Не вдалося відправити дані: ");
      Serial.print(sineData);
      Serial.println(" -- НЕ УСПІШНО (Не отримано ACK)."); // Це важливе повідомлення для налагодження!
      digitalWrite(LED_PIN, LOW); // Залишити LED вимкненим, щоб показати помилку
    }
  }
}