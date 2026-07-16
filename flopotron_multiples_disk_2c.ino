// ==================================================================================
//   FIRMWARE PACHATRON V9 - RE-SINCRO TOTAL (MÁXIMA NITIDEZ Y RITMO PERFECTO)
// ==================================================================================

#include <Arduino.h>

#define MAX_DRIVES 6

// Memorias de posición y estados alineados
unsigned int MIN_POSITION[16] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
unsigned int MAX_POSITION[16] = {158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158};
unsigned int currentPosition[16] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
int currentState[24] = {LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW,LOW};

unsigned int currentPeriod[16] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
unsigned int currentTick[16] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};

// --- MATRIZ DE TU CABLEADO REAL (Canales 0 al 5 de Python) ---
const byte pStep[] = {2, 4, 6, 8, 12, 10}; // Pines de pulso/paso
const byte pDir[]  = {3, 5, 7, 9, 13, 11}; // Pines de dirección

// Tabla de frecuencias oficial de Moppy 2 calibrada para el reloj de hardware
const unsigned int noteDoubleTicks[] = {
  0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
  1528,1442,1362,1285,1213,1145,1081,1020,963,909,858,810,
  764,721,681,643,607,573,540,510,481,454,429,405,
  382,361,340,321,303,286,270,255,241,227,214,203,
  191,180,170,161,152,143,135,128,120,114,107,101,
  96,90,85,80,76,72,68,64,60,57,54,51,
  48,45,43,40,38,36,34,32,30,28,27,25
};

void resetAll();
void togglePin(byte driveNum, byte pin, byte direction_pin);

void setup() {
  Serial.begin(115200);

  // Inicializar pines de salida del 2 al 13
  for (int i = 2; i <= 13; i++) {
    pinMode(i, OUTPUT);
    digitalWrite(i, LOW);
  }

  // Calibración inicial automática
  resetAll();
  delay(500);

  // CONFIGURACIÓN DEL TIMER 1 POR HARDWARE (Pulsos puros sin delay)
  cli();
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1  = 0;
  OCR1A  = 79; // Resolución clásica de Moppy para máxima afinación
  TCCR1B |= (1 << WGM12); 
  TCCR1B |= (1 << CS11);  // Prescaler de 8
  TIMSK1 |= (1 << OCIE1A);
  sei();
}

// INTERRUPCIÓN MAESTRA: Corre en nanosegundos de forma paralela al código
ISR(TIMER1_COMPA_vect) {
  for (int d = 0; d < MAX_DRIVES; d++) {
    if (currentPeriod[d] > 0) {
      currentTick[d]++;
      if (currentTick[d] >= currentPeriod[d]) {
        togglePin(d, pStep[d], pDir[d]); 
        currentTick[d] = 0;
      }
    }
  }
}

void togglePin(byte driveNum, byte pin, byte direction_pin) {
  int dirIndex = driveNum + 8;

  // Lógica de rebote largo por carril (158 medios pasos)
  if (currentPosition[driveNum] >= MAX_POSITION[driveNum]) {
    currentState[dirIndex] = HIGH;
    digitalWrite(direction_pin, HIGH);
  } 
  else if (currentPosition[driveNum] <= MIN_POSITION[driveNum]) {
    currentState[dirIndex] = LOW;
    digitalWrite(direction_pin, LOW);
  }

  // Actualizar la posición del cabezal
  if (currentState[dirIndex] == HIGH) {
    currentPosition[driveNum]--;
  } else {
    currentPosition[driveNum]++;
  }

  // --- SOLUCIÓN DE ORDEN Y NITIDEZ ---
  // Alternamos el estado de manera síncrona en cada ciclo. 
  // Al no usar delayMicroseconds(), el Timer no se deforma, eliminando el desorden rítmico.
  digitalWrite(pin, currentState[driveNum]);
  currentState[driveNum] = !currentState[driveNum];
}

void loop() {
  // Lector Serial de alta velocidad limpio
  if (Serial.available() >= 3) {
    byte comando = Serial.read();
    byte nota = Serial.read();
    byte velocidad = Serial.read();
    
    int tipoComando = comando & 0xF0;
    int canal = comando & 0x0F; 

    if (canal >= 0 && canal < MAX_DRIVES) {
      if (tipoComando == 0x90 && velocidad > 0) { // Note On
        if (nota >= 24 && nota <= 85) {
          currentPeriod[canal] = noteDoubleTicks[nota];
        }
      } 
      else if (tipoComando == 0x80 || (tipoComando == 0x90 && velocidad == 0)) { // Note Off
        currentPeriod[canal] = 0;
      }
    }
  }
}

void resetAll() {
  for (byte d = 0; d < MAX_DRIVES; d++) {
    currentPeriod[d] = 0;
    digitalWrite(pDir[d], HIGH); 
  }

  // Calibración a fondo mecánico
  for (unsigned int s = 0; s < 158; s++) {
    for (byte d = 0; d < MAX_DRIVES; d++) {
      digitalWrite(pStep[d], HIGH);
      digitalWrite(pStep[d], LOW);
    }
    delayMicroseconds(1200);
  }

  for (byte d = 0; d < MAX_DRIVES; d++) {
    currentPosition[d] = 0;
    currentState[d] = LOW;
    digitalWrite(pDir[d], LOW);
    currentState[d + 8] = LOW;
  }
}