// =================================================================
//  ARDUINO: RECEPTOR TOTAL (ACEPTA TODOS LOS CANALES EXCEPTO BATERÍA)
// =================================================================
#include <EEPROM.h>

const int pinA = 2; 
const int pinB = 3; 
const int pinC = 4; 
const int pinD = 5; 

const int pinSwitchIzquierdo = 7; 
const int pinSwitchDerecho   = 6; 

const int ADDR_CALIBRADO = 0; 
const int ADDR_LARGO_H   = 1; 
const int ADDR_LARGO_L   = 2; 

long largoTotalPasos = 4000; 
long mitadPasos = 2000;

int pasoActual = 0; 
long contadorPasos = 0;
bool direccionActual = true; 

bool notaActiva = false;
byte notaMidiActual = 0;
unsigned long delayPasoUs = 0;
unsigned long ultimoPasoUs = 0;

void realizarCalibracionFisica() {
  long pasosHoming = 0;
  while (digitalRead(pinSwitchIzquierdo) == HIGH) {
    darUnPaso(false);
    delay(4); 
    pasosHoming++;
  }
  apagarMotor();
  delay(300); 
  
  long pasosContados = 0;
  while (digitalRead(pinSwitchDerecho) == HIGH) {
    darUnPaso(true);
    delay(4);
    pasosContados++;
  }
  largoTotalPasos = pasosContados;
  mitadPasos = largoTotalPasos / 2;
  apagarMotor();
  delay(300); 

  for (long i = 0; i < mitadPasos; i++) {
    darUnPaso(false); 
    delay(4);
  }
  
  contadorPasos = mitadPasos; 
  direccionActual = true; 
  apagarMotor();

  EEPROM.write(ADDR_CALIBRADO, 1);
  EEPROM.write(ADDR_LARGO_H, (largoTotalPasos >> 8) & 0xFF);
  EEPROM.write(ADDR_LARGO_L, largoTotalPasos & 0xFF);
}

void setup() {
  Serial.begin(115200);
  
  pinMode(pinA, OUTPUT);
  pinMode(pinB, OUTPUT);
  pinMode(pinC, OUTPUT);
  pinMode(pinD, OUTPUT);
  
  pinMode(pinSwitchIzquierdo, INPUT_PULLUP);
  pinMode(pinSwitchDerecho, INPUT_PULLUP);

  byte yaCalibrado = EEPROM.read(ADDR_CALIBRADO);
  bool forzarRecalibracion = (digitalRead(pinSwitchIzquierdo) == LOW || digitalRead(pinSwitchDerecho) == LOW);

  if (yaCalibrado == 1 && !forzarRecalibracion) {
    byte alto = EEPROM.read(ADDR_LARGO_H);
    byte bajo = EEPROM.read(ADDR_LARGO_L);
    largoTotalPasos = (alto << 8) | bajo;
    mitadPasos = largoTotalPasos / 2;
    contadorPasos = mitadPasos; 
    direccionActual = true;
  } else {
    realizarCalibracionFisica();
  }
}

void loop() {
  if (Serial.available() >= 3) {
    byte comando = Serial.read();
    byte nota = Serial.read();
    byte velocidad = Serial.read();

    byte tipoMensaje = comando & 0xF0; 
    byte canalDestino = comando & 0x0F; 

    // Ignoramos el Canal 9 (baterías/percusión en estándar MIDI)
    if (canalDestino != 9) {
      if (tipoMensaje == 0x90 && velocidad > 0) {
        notaActiva = true;
        notaMidiActual = nota;
        
        float frecuenciaHz = 440.0 * pow(2.0, (nota - 69.0) / 12.0);
        delayPasoUs = 1000000.0 / (4.0 * frecuenciaHz); 
        ultimoPasoUs = micros();
      } 
      else if (tipoMensaje == 0x80 || (tipoMensaje == 0x90 && velocidad == 0)) {
        if (nota == notaMidiActual) {
          notaActiva = false;
          apagarMotor();
        }
      }
    }
  }

  if (notaActiva) {
    unsigned long tiempoActualUs = micros();
    if (tiempoActualUs - ultimoPasoUs >= delayPasoUs) {
      ultimoPasoUs = tiempoActualUs;

      if (direccionActual && digitalRead(pinSwitchDerecho) == LOW) {
        direccionActual = false;
        contadorPasos = largoTotalPasos;
      } 
      else if (!direccionActual && digitalRead(pinSwitchIzquierdo) == LOW) {
        direccionActual = true;
        contadorPasos = 0;
      }

      if (direccionActual) {
        contadorPasos++;
        if (contadorPasos >= largoTotalPasos) direccionActual = false;
      } else {
        contadorPasos--;
        if (contadorPasos <= 0) direccionActual = true;
      }

      darUnPaso(direccionActual);
    }
  }
}

void darUnPaso(bool adelante) {
  if (adelante) pasoActual++; else pasoActual--;
  if (pasoActual > 3) pasoActual = 0;
  if (pasoActual < 0) pasoActual = 3;
  actualizarPinesHighPower();
}

void actualizarPinesHighPower() {
  switch (pasoActual) {
    case 0: digitalWrite(pinA, HIGH); digitalWrite(pinB, HIGH); digitalWrite(pinC, LOW);  digitalWrite(pinD, LOW);  break; 
    case 1: digitalWrite(pinA, LOW);  digitalWrite(pinB, HIGH); digitalWrite(pinC, HIGH); digitalWrite(pinD, LOW);  break; 
    case 2: digitalWrite(pinA, LOW);  digitalWrite(pinB, LOW);  digitalWrite(pinC, HIGH); digitalWrite(pinD, HIGH); break; 
    case 3: digitalWrite(pinA, HIGH); digitalWrite(pinB, LOW);  digitalWrite(pinC, LOW);  digitalWrite(pinD, HIGH); break; 
  }
}

void apagarMotor() {
  digitalWrite(pinA, LOW);
  digitalWrite(pinB, LOW);
  digitalWrite(pinC, LOW);
  digitalWrite(pinD, LOW);
}