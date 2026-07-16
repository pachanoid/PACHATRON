// Arreglo con los 12 pines de salida (Cambiamos el conflictivo 13 por el A0)
const int pinesActuadores[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, A0};
const int cantidadPines = 12;

// Arreglos dinámicos para el tiempo de apagado de cada pin
unsigned long tiemposGolpe[cantidadPines];
bool pinesActivados[cantidadPines];

const int duracionGolpeMs = 15; // Tiempo que el relé se queda pegado

void setup() {
  Serial.begin(115200);
  
  // Inicializamos los 12 pines como salidas en estado LOW
  for (int i = 0; i < cantidadPines; i++) {
    pinMode(pinesActuadores[i], OUTPUT);
    digitalWrite(pinesActuadores[i], LOW);
    tiemposGolpe[i] = 0;
    pinesActivados[i] = false;
  }
}

void loop() {
  // Si llega la orden desde Python
  if (Serial.available() > 0) {
    int byteRecibido = Serial.read();
    int indice = -1;

    // OPCIÓN A: Si Python manda bytes puros (0 a 11 correspondientes al índice)
    if (byteRecibido >= 0 && byteRecibido < cantidadPines) {
      indice = byteRecibido;
    }
    // OPCIÓN B: Si Python manda los números como caracteres ASCII (ej: '0', '1', '2'...)
    // Nota: Para dos dígitos ('10', '11') desde Python tendrías que mandar letras (ej: 'A', 'B') 
    // pero si mandas el byte crudo (Opción A), entra directo acá abajo:
    else if (byteRecibido >= '2' && byteRecibido <= '9') {
      // Si mandas caracteres del '2' al '9', calculas el índice
      indice = byteRecibido - '2'; 
    }

    // Si encontramos un índice válido, disparamos
    if (indice >= 0 && indice < cantidadPines) {
      digitalWrite(pinesActuadores[indice], HIGH); // ¡Zas! Dispara usando el arreglo
      tiemposGolpe[indice] = millis();             // Guarda el milisegundo exacto
      pinesActivados[indice] = true;
    }
  }

  // Apagado automático independiente para cada uno de los 12 pines
  for (int i = 0; i < cantidadPines; i++) {
    if (pinesActivados[i] && (millis() - tiemposGolpe[i] >= duracionGolpeMs)) {
      digitalWrite(pinesActuadores[i], LOW);
      pinesActivados[i] = false;
    }
  }
}