const int RELAY_FAN  = 7;  // IN1
const int RELAY_PUMP = 8;  // IN2

void setup() {
  pinMode(RELAY_FAN, OUTPUT);
  pinMode(RELAY_PUMP, OUTPUT);
  // Active-LOW relays: HIGH = OFF, LOW = ON
  digitalWrite(RELAY_FAN, HIGH);
  digitalWrite(RELAY_PUMP, HIGH);
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();

    if (c == 'f') { digitalWrite(RELAY_FAN, LOW);  }  // fan ON
    if (c == 'F') { digitalWrite(RELAY_FAN, HIGH); }  // fan OFF

    if (c == 'p') { digitalWrite(RELAY_PUMP, LOW);  } // pump ON
    if (c == 'P') { digitalWrite(RELAY_PUMP, HIGH); } // pump OFF

    if (c == 'a') { // all OFF
      digitalWrite(RELAY_FAN, HIGH);
      digitalWrite(RELAY_PUMP, HIGH);
    }

    if (c == 's') { // status back to Python
      Serial.print("FAN:");
      Serial.print(digitalRead(RELAY_FAN) == LOW ? "ON" : "OFF");
      Serial.print(",PUMP:");
      Serial.println(digitalRead(RELAY_PUMP) == LOW ? "ON" : "OFF");
    }
  }
}
