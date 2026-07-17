#include <LiquidCrystal.h>

// Configuración de pines clásica del LCD Keypad Shield
LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

int ultimo_boton = -1;

void setup() {
  Serial.begin(9600);
  
  // Mantiene el bucle rápido para evitar retrasos
  Serial.setTimeout(10); 

  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("PACHATRON READY");
  lcd.setCursor(0, 1);
  lcd.print("Esperando PC...");
}

void loop() {
  // 1. LEER BOTONES DEL SHIELD 
  int x = analogRead(0);
  int boton_presionado = -1; 

  // Márgenes ampliados (Tus valores base: right=0, up=132, down=307, left=480, select=722)
  if (x < 60) {
    boton_presionado = 0; // RIGHT (Detecta de 0 a 59)
  } else if (x < 240) {    // ¡MÁS TOLERANCIA PARA EL UP! (Antes 180, ahora lee hasta 239 por si falla el contacto)
    boton_presionado = 1; // UP 
  } else if (x < 410) {    // Más tolerancia para el DOWN (Antes 360, ahora hasta 409)
    boton_presionado = 2; // DOWN 
  } else if (x < 630) {    // ¡MÁS TOLERANCIA PARA EL LEFT! (Antes 550, ahora lee hasta 629 para asegurar tu 480)
    boton_presionado = 3; // LEFT 
  } else if (x < 880) {
    boton_presionado = 4; // SELECT
  }

  // Detectar el momento exacto de la presión
  if (boton_presionado != ultimo_boton) {
    if (boton_presionado == 1) {        // UP
      Serial.println("P");              // P = Play Concierto
    } 
    else if (boton_presionado == 2) {   // DOWN
      Serial.println("S");              // S = Stop
    } 
    else if (boton_presionado == 0) {   // RIGHT
      Serial.println("N");              // N = Avanzar canción
    }
    else if (boton_presionado == 3) {   // LEFT
      Serial.println("B");              // B = Retroceder canción
    }
    
    delay(50); // Anti-rebote
  }
  ultimo_boton = boton_presionado;

  // 2. RECIBIR TEXTO DESDE PYTHON
  if (Serial.available() > 0) {
    String linea = Serial.readStringUntil('\n');
    linea.trim();

    if (linea.length() > 0) {
      if (linea == "--- PACHASTOP ---") {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("CONCIERTO STOP");
        lcd.setCursor(0, 1);
        lcd.print("PACHATRON READY");
      } else {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("REPRODUCIENDO:");
        lcd.setCursor(0, 1);
        lcd.print(linea); 
      }
    }
  }
}