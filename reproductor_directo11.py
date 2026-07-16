import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import mido
import serial
import serial.tools.list_ports
from collections import Counter
import ctypes
import os

class MegaOrquestaPachatron:
    def __init__(self, root):
        self.root = root
        self.root.title("PACHATRON - Mega Orquesta Completa con Playlist y Escáner")
        self.root.geometry("720x980")
        
        self.conexion_leonardo = None
        self.conexion_uno = None 
        self.conexion_escaner = None  
        self.reproduciendo = False
        self.hilo_musica = None
        self.tiempos_tap = [] 

        # --- SISTEMA DE PLAYLIST ---
        self.playlist = []           # Lista con las rutas completas de los archivos MIDI
        self.indice_actual = 0       # Índice del MIDI que se está reproduciendo
        self.forzar_siguiente = False # Bandera para saltar de canción manualmente

        # Inicializar el sintetizador MIDI de hardware de Windows
        self.hmidi = ctypes.c_void_p()
        ctypes.windll.winmm.midiOutOpen(ctypes.byref(self.hmidi), 0, 0, 0, 0)

        # --- DICCIONARIO DE MAPEO DE PINES Y NOMBRES PARA EL ARDUINO UNO ---
        self.MAPA_BATERIA = {
            35: (2, "🥁 Bombo Acústico"),
            36: (2, "🥁 Bombo Estándar"),
            38: (3, "💥 Caja / Snare"),
            40: (4, "⚡ Caja Eléctrica"),
            42: (5, "💿 Hi-Hat Cerrado"),
            46: (6, "📀 Hi-Hat Abierto"),
            41: (7, "🔊 Tom de Piso"),
            43: (8, "🔉 Tom Bajo"),
            45: (9, "🍁 Tom Medio"),
            48: (10, "📢 Tom Alto"),
            49: (11, "✨ Platillo Crash"),
            51: (12, "🎵 Platillo Ride")
        }

        # --- SELECCION DE PUERTOS ---
        tk.Label(root, text="1. Puerto del Arduino Leonardo (Disqueteras):", font=("Arial", 9, "bold")).pack(pady=2)
        self.combo_leo = tk.StringVar()
        self.dropdown_leo = ttk.Combobox(root, textvariable=self.combo_leo, state="readonly", width=30)
        self.dropdown_leo.pack(pady=2)
        
        tk.Label(root, text="2. Puerto del Arduino UNO (Batería 12CH):", font=("Arial", 9, "bold")).pack(pady=2)
        self.combo_uno = tk.StringVar()
        self.dropdown_uno = ttk.Combobox(root, textvariable=self.combo_uno, state="readonly", width=30)
        self.dropdown_uno.pack(pady=2)

        tk.Label(root, text="3. Puerto del Arduino Escáner (Motor Paso a Paso):", font=("Arial", 9, "bold"), fg="darkblue").pack(pady=2)
        self.combo_escaner = tk.StringVar()
        self.dropdown_escaner = ttk.Combobox(root, textvariable=self.combo_escaner, state="readonly", width=30)
        self.dropdown_escaner.pack(pady=2)
        
        self.actualizar_puertos()
        tk.Button(root, text="Actualizar Lista de Puertos", command=self.actualizar_puertos).pack(pady=4)

        # --- TESTEO ---
        frame_test = tk.Frame(root)
        frame_test.pack(pady=4)
        tk.Button(frame_test, text="PROBAR DISQUETERAS", bg="orange", fg="black", font=("Arial", 8, "bold"), command=self.testear_disqueteras).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_test, text="PROBAR BOMBO", bg="cyan", fg="black", font=("Arial", 8, "bold"), command=self.testear_bombo).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_test, text="PROBAR ESCÁNER", bg="lime", fg="black", font=("Arial", 8, "bold"), command=self.testear_escaner).pack(side=tk.LEFT, padx=5)

        # --- NUEVO: INTERFAZ DE PLAYLIST (REEMPLAZA AL BOTÓN SIMPLE) ---
        tk.Label(root, text="4. Lista de Reproducción (Playlist):", font=("Arial", 10, "bold")).pack(pady=4)
        
        frame_playlist = tk.Frame(root)
        frame_playlist.pack(pady=2, fill=tk.BOTH, expand=False, padx=40)
        
        # Caja de lista con barra de desplazamiento
        self.listbox_playlist = tk.Listbox(frame_playlist, height=6, bg="#1e1e1e", fg="white", selectbackground="green", font=("Arial", 9))
        self.listbox_playlist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox_playlist.bind("<Double-Button-1>", self.doble_clic_playlist) # Doble clic para reproducir una concreta
        
        scrollbar = tk.Scrollbar(frame_playlist, orient="vertical", command=self.listbox_playlist.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_playlist.config(yscrollcommand=scrollbar.set)

        # Botones de gestión de Playlist
        frame_botones_playlist = tk.Frame(root)
        frame_botones_playlist.pack(pady=4)
        tk.Button(frame_botones_playlist, text="Agregar MIDIs...", bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), command=self.buscar_midi).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones_playlist, text="Limpiar Lista", bg="#f44336", fg="white", font=("Arial", 9, "bold"), command=self.limpiar_lista_midis).pack(side=tk.LEFT, padx=5)

        # --- VOLUMEN MIDI ---
        tk.Label(root, text="5. Volumen de la Música de Fondo (Parlantes):", font=("Arial", 10, "bold"), fg="navy").pack(pady=4)
        self.slider_volumen = tk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, length=400, command=self.ajustar_volumen)
        self.slider_volumen.set(40)  
        self.slider_volumen.pack(pady=2)

        # --- TRANSPOSICIÓN DE OCTAVAS PARA DISQUETERAS ---
        tk.Label(root, text="6. Afinación / Rango de Frecuencia (Disqueteras):", font=("Arial", 10, "bold"), fg="darkgreen").pack(pady=4)
        self.slider_octava = tk.Scale(root, from_=-24, to=24, orient=tk.HORIZONTAL, length=400, tickinterval=12)
        self.slider_octava.set(12)  
        self.slider_octava.pack(pady=2)

        # --- CALIBRADOR ---
        tk.Label(root, text="7. Calibrador de Oído Magnético para la Batería:", font=("Arial", 10, "bold"), fg="purple").pack(pady=4)
        self.btn_tap = tk.Button(root, text="¡PRESIONA ESPACIO al ritmo de la música si la batería va desfasada!", 
                                 bg="purple", fg="white", font=("Arial", 9, "bold"), command=self.registrar_tap)
        self.btn_tap.pack(pady=4, fill=tk.X, padx=40)
        root.bind("<space>", lambda event: self.registrar_tap())

        self.slider_desfase = tk.Scale(root, from_=0, to=800, orient=tk.HORIZONTAL, length=400)
        self.slider_desfase.set(0) 
        self.slider_desfase.pack(pady=2)
        self.lbl_ms = tk.Label(root, text="Retardo actual de batería: 0 ms", font=("Arial", 9, "bold"), fg="blue")
        self.lbl_ms.pack()

        # --- CONTROLES DE REPRODUCCIÓN ---
        tk.Label(root, text="8. Controles del Concierto:", font=("Arial", 10, "bold")).pack(pady=4)
        
        frame_controles = tk.Frame(root)
        frame_controles.pack(pady=4)
        
        self.btn_play = tk.Button(frame_controles, text="▶ PLAY Concierto", bg="green", fg="white", font=("Arial", 11, "bold"), command=self.iniciar_reproduccion, state=tk.DISABLED)
        self.btn_play.pack(side=tk.LEFT, padx=5)
        
        self.btn_next = tk.Button(frame_controles, text="⏭ Siguiente", bg="blue", fg="white", font=("Arial", 11, "bold"), command=self.saltar_cancion, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(frame_controles, text="⏹ STOP Todo", bg="red", fg="white", font=("Arial", 11, "bold"), command=self.detener_reproduccion, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # --- MONITOR ---
        tk.Label(root, text="9. Monitor Detallado en Vivo (Canal 10 + Disqueteras + Escáner):", font=("Arial", 10, "bold")).pack(pady=4)
        self.monitor = scrolledtext.ScrolledText(root, width=75, height=10, bg="black", fg="lime", font=("Courier New", 9))
        self.monitor.pack(pady=5)
        
        self.ajustar_volumen(40)

    def actualizar_puertos(self):
        puertos = [p.device for p in serial.tools.list_ports.comports()]
        if puertos:
            self.dropdown_leo['values'] = puertos
            self.dropdown_uno['values'] = puertos
            self.dropdown_escaner['values'] = puertos
            
            self.combo_leo.set(puertos[0])
            self.combo_uno.set(puertos[0] if len(puertos) == 1 else puertos[1])
            self.combo_escaner.set(puertos[-1])  
        else:
            self.combo_leo.set("No se encontraron COM")
            self.combo_uno.set("No se encontraron COM")
            self.combo_escaner.set("No se encontraron COM")

    def log(self, texto):
        def escribir():
            self.monitor.insert(tk.END, texto + "\n")
            self.monitor.see(tk.END)
        self.root.after(0, escribir)

    def buscar_midi(self):
        # filetypes modificado para permitir selección múltiple (multiple=True)
        archivos = filedialog.askopenfilenames(filetypes=[("Archivos MIDI", "*.mid;*.midi")])
        if archivos:
            for ruta in archivos:
                if ruta not in self.playlist:
                    self.playlist.append(ruta)
                    nombre_archivo = os.path.basename(ruta)
                    self.listbox_playlist.insert(tk.END, f"🎵 {nombre_archivo}")
            
            self.btn_play.config(state=tk.NORMAL)
            self.log(f"Se agregaron {len(archivos)} canciones a la playlist.")

    def limpiar_lista_midis(self):
        self.detener_reproduccion()
        self.playlist.clear()
        self.listbox_playlist.delete(0, tk.END)
        self.btn_play.config(state=tk.DISABLED)
        self.btn_next.config(state=tk.DISABLED)
        self.log("🧹 Playlist vaciada.")

    def doble_clic_playlist(self, event):
        # Permite reproducir una canción específica haciendo doble clic sobre ella en la interfaz
        seleccion = self.listbox_playlist.curselection()
        if seleccion:
            indice = seleccion[0]
            if self.reproduciendo:
                self.indice_actual = indice
                self.forzar_siguiente = True # Hace que el bucle actual termine y salte a esta
            else:
                self.indice_actual = indice
                self.iniciar_reproduccion()

    def ajustar_volumen(self, valor):
        try:
            porcentaje = int(valor)
            vol_canal = int((porcentaje / 100.0) * 0xFFFF)
            vol_final = vol_canal | (vol_canal << 16)
            ctypes.windll.winmm.midiOutSetVolume(self.hmidi, vol_final)
        except: pass

    def testear_disqueteras(self):
        puerto = self.combo_leo.get()
        if "No" in puerto or not puerto: return
        threading.Thread(target=self.bucle_testeo_leo, args=(puerto,), daemon=True).start()

    def bucle_testeo_leo(self, puerto):
        try:
            test_ser = serial.Serial(puerto, 115200, timeout=2, rtscts=True, dsrdtr=True)
            time.sleep(1.5)
            for d in range(6):
                test_ser.write(bytes([0x90 + d, 60, 100])) 
                test_ser.flush()
                time.sleep(0.2)
                test_ser.write(bytes([0x80 + d, 60, 0]))
                test_ser.flush()
            test_ser.close()
        except Exception as e: messagebox.showerror("Error", f"Fallo: {e}")

    def testear_bombo(self):
        puerto = self.combo_uno.get()
        if "No" in puerto or not puerto: return
        try:
            bombo_ser = serial.Serial(puerto, 115200, timeout=2)
            time.sleep(2.0) 
            bombo_ser.write(bytes([2])) 
            bombo_ser.flush()
            bombo_ser.close()
        except Exception as e: messagebox.showerror("Error", f"Fallo: {e}")

    def testear_escaner(self):
        puerto = self.combo_escaner.get()
        if "No" in puerto or not puerto: return
        try:
            esc_ser = serial.Serial()
            esc_ser.port = puerto
            esc_ser.baudrate = 115200
            esc_ser.dsrdtr = False
            esc_ser.rtscts = False
            esc_ser.open()
            esc_ser.dtr = False
            esc_ser.rts = False
            
            time.sleep(1.0)
            esc_ser.write(bytes([0x90, 60, 100]))  
            esc_ser.flush()
            time.sleep(0.5)
            esc_ser.write(bytes([0x80, 60, 0]))    
            esc_ser.flush()
            esc_ser.close()
        except Exception as e: messagebox.showerror("Error", f"Fallo en escáner: {e}")

    def registrar_tap(self):
        if not self.reproduciendo: return
        ahora = time.time()
        self.tiempos_tap.append(ahora)
        if len(self.tiempos_tap) >= 2:
            ultimos_taps = self.tiempos_tap[-4:]
            diferencias = [ultimos_taps[i] - ultimos_taps[i-1] for i in range(1, len(ultimos_taps))]
            promedio_segundos = sum(diferencias) / len(diferencias)
            ms_calculados = int((promedio_segundos % 0.600) * 1000)
            if 50 <= ms_calculados <= 750:
                self.slider_desfase.set(ms_calculados)

    def tocar_nota_parlante(self, comando, canal, nota, velocidad):
        msg = comando | canal | (nota << 8) | (velocidad << 16)
        ctypes.windll.winmm.midiOutShortMsg(self.hmidi, msg)

    def analizar_bateria_midi(self, ruta):
        try:
            mid = mido.MidiFile(ruta)
            notas_bateria = []
            for msg in mid:
                if msg.type == 'note_on' and msg.velocity > 0 and msg.channel == 9:
                    notas_bateria.append(msg.note)
            
            self.log("\n" + "="*50)
            self.log(f"   ANALIZANDO PERCUSIÓN: {os.path.basename(ruta)}")
            self.log("="*50)
            if not notas_bateria:
                self.log("⚠️ ¡Ojo! Este archivo MIDI no tiene percusión en el Canal 10.")
            else:
                conteo = Counter(notas_bateria)
                for nota, veces in conteo.most_common():
                    detalle = "Instrumento desconocido"
                    if nota in self.MAPA_BATERIA:
                        detalle = self.MAPA_BATERIA[nota][1]
                    self.log(f" 🎵 Nota MIDI {nota} -> ({detalle}): se repite {veces} veces.")
            self.log("="*50 + "\n")
        except Exception as e:
            self.log(f"No se pudo analizar la batería: {e}")

    def iniciar_reproduccion(self):
        if not self.playlist:
            messagebox.showwarning("Sin música", "Primero agrega canciones usando el botón 'Agregar MIDIs...'")
            return
            
        self.tiempos_tap = []
        p_leo = self.combo_leo.get()
        p_uno = self.combo_uno.get()
        p_esc = self.combo_escaner.get()
        self.ajustar_volumen(self.slider_volumen.get())

        try:
            # 1. Conexión Disqueteras
            self.conexion_leonardo = serial.Serial(p_leo, 115200, timeout=2, rtscts=True, dsrdtr=True)
            self.conexion_leonardo.dtr = True
            self.conexion_leonardo.rts = True
            
            # 2. Conexión Batería
            self.conexion_uno = serial.Serial(p_uno, 115200, timeout=2)
            
            # 3. Conexión Escáner
            self.conexion_escaner = serial.Serial()
            self.conexion_escaner.port = p_esc
            self.conexion_escaner.baudrate = 115200
            self.conexion_escaner.timeout = 1
            self.conexion_escaner.dsrdtr = False
            self.conexion_escaner.rtscts = False
            self.conexion_escaner.open()
            self.conexion_escaner.dtr = False
            self.conexion_escaner.rts = False

            time.sleep(2.0) 
        except Exception as e:
            messagebox.showerror("Error", f"Error abriendo puertos seriales: {e}")
            self.limpiar_orquesta()
            return

        self.reproduciendo = True
        self.btn_play.config(state=tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        
        # Arrancamos el hilo principal que controla la cola de reproducción
        self.hilo_musica = threading.Thread(target=self.bucle_playlist, daemon=True)
        self.hilo_musica.start()

    def bucle_playlist(self):
        """Bucle superior que controla la transición entre canciones de la lista"""
        while self.reproduciendo and self.indice_actual < len(self.playlist):
            self.forzar_siguiente = False
            ruta_cancion = self.playlist[self.indice_actual]
            nombre_corto = os.path.basename(ruta_cancion)
            
            # Actualizar selección visual en el listbox
            self.root.after(0, self.actualizar_seleccion_playlist, self.indice_actual)
            
            self.log(f"\n▶ INICIANDO CONCIERTO: {nombre_corto} [{self.indice_actual + 1}/{len(self.playlist)}]")
            self.analizar_bateria_midi(ruta_cancion)
            
            # Ejecuta la canción actual
            self.reproducir_midi_individual(ruta_cancion)
            
            # Si no ha sido detenido del todo y terminamos (o nos saltamos), avanzamos
            if self.reproduciendo:
                self.indice_actual += 1
                
        # Si llegamos al final de la playlist, reiniciamos el índice y paramos
        self.indice_actual = 0
        self.detener_reproduccion()

    def actualizar_seleccion_playlist(self, indice):
        self.listbox_playlist.selection_clear(0, tk.END)
        self.listbox_playlist.selection_set(indice)
        self.listbox_playlist.see(indice)

    def saltar_cancion(self):
        """Pasa a la siguiente canción interrumpiendo el flujo actual"""
        if self.reproduciendo:
            self.forzar_siguiente = True

    def reproducir_midi_individual(self, ruta):
        try:
            mid = mido.MidiFile(ruta)
            mapeo_canales = {}
            siguiente_disquetera = 0
            
            notas_activas_disquetera = {i: None for i in range(6)}
            notas_activas_escaner = {} 

            for msg in mid.play():
                # Condición de salida si se pulsa STOP o si se pulsa SIGUIENTE
                if not self.reproduciendo or self.forzar_siguiente:
                    break
                
                if msg.type in ['note_on', 'note_off']:
                    cmd_tipo = 0x90 if msg.type == 'note_on' else 0x80
                    
                    # 1. PARLANTES
                    self.tocar_nota_parlante(cmd_tipo, msg.channel, msg.note, msg.velocity)
                    
                    # 2. BATERÍA
                    if msg.channel == 9: 
                        if msg.type == 'note_on' and msg.velocity > 0:
                            nota = msg.note
                            if nota in self.MAPA_BATERIA:
                                pin_destino, nombre_instrumento = self.MAPA_BATERIA[nota]
                                retardo = self.slider_desfase.get() / 1000.0
                                
                                threading.Thread(
                                    target=self.enviar_bateria_retrasada, 
                                    args=(pin_destino, nombre_instrumento, retardo), 
                                    daemon=True
                                ).start()
                            else:
                                self.log(f"⚠️ [DESCONOCIDO] Nota de percusión {nota} sin pin asignado.")
                        continue 
                    
                    # 3. ESCÁNER SOLISTA
                    if msg.type == 'note_on' and msg.velocity > 0:
                        notas_activas_escaner[msg.note] = msg.channel
                        nota_mas_aguda = max(notas_activas_escaner.keys())
                        
                        if msg.note == nota_mas_aguda:
                            if self.conexion_escaner and self.conexion_escaner.is_open:
                                self.conexion_escaner.write(bytes([0x90, msg.note, msg.velocity]))
                                self.conexion_escaner.flush()
                    
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        if msg.note in notas_activas_escaner:
                            del notas_activas_escaner[msg.note]
                            
                            if self.conexion_escaner and self.conexion_escaner.is_open:
                                if notas_activas_escaner:
                                    siguiente_aguda = max(notas_activas_escaner.keys())
                                    self.conexion_escaner.write(bytes([0x90, siguiente_aguda, 127]))
                                else:
                                    self.conexion_escaner.write(bytes([0x80, msg.note, 0]))
                                self.conexion_escaner.flush()

                    # 4. DISQUETERAS
                    if msg.channel not in mapeo_canales:
                        if siguiente_disquetera < 6:
                            mapeo_canales[msg.channel] = siguiente_disquetera
                            siguiente_disquetera += 1
                        else:
                            mapeo_canales[msg.channel] = 5
                    
                    disquetera_destino = mapeo_canales[msg.channel]
                    es_nota_on = (msg.type == 'note_on' and msg.velocity > 0)
                    
                    nota_modificada = msg.note + self.slider_octava.get()
                    nota_modificada = max(24, min(96, nota_modificada))

                    if es_nota_on:
                        if notas_activas_disquetera[disquetera_destino] is not None:
                            nota_vieja = notas_activas_disquetera[disquetera_destino]
                            if self.conexion_leonardo and self.conexion_leonardo.is_open:
                                self.conexion_leonardo.write(bytes([0x80 + disquetera_destino, nota_vieja, 0]))
                        
                        notas_activas_disquetera[disquetera_destino] = nota_modificada
                        comando_final = 0x90 + disquetera_destino
                        if self.conexion_leonardo and self.conexion_leonardo.is_open:
                            self.conexion_leonardo.write(bytes([comando_final, nota_modificada, msg.velocity]))
                            self.conexion_leonardo.flush()
                    else:
                        if notas_activas_disquetera[disquetera_destino] == nota_modificada:
                            notas_activas_disquetera[disquetera_destino] = None
                            comando_final = 0x80 + disquetera_destino
                            if self.conexion_leonardo and self.conexion_leonardo.is_open:
                                self.conexion_leonardo.write(bytes([comando_final, nota_modificada, 0]))
                                self.conexion_leonardo.flush()

        except Exception as e: self.log(f"Error reproduciendo canción: {e}")

    def enviar_bateria_retrasada(self, pin, nombre, retardo):
        if retardo > 0: 
            time.sleep(retardo)
        if self.reproduciendo and self.conexion_uno and self.conexion_uno.is_open:
            self.log(f"⚡ [BATERÍA] {nombre} -> Saliendo por PIN {pin}")
            self.conexion_uno.write(bytes([pin]))
            self.conexion_uno.flush()

    def detener_reproduccion(self): 
        self.reproduciendo = False
        self.forzar_siguiente = True

    def limpiar_orquesta(self):
        if self.hmidi: ctypes.windll.winmm.midiOutReset(self.hmidi)
        
        # Apagar disqueteras
        if self.conexion_leonardo and self.conexion_leonardo.is_open:
            for d in range(6):
                try: self.conexion_leonardo.write(bytes([0x80 + d, 0, 0]))
                except: pass
            self.conexion_leonardo.close()
            
        # Apagar batería
        if self.conexion_uno and self.conexion_uno.is_open: 
            self.conexion_uno.close()
            
        # Apagar escáner
        if self.conexion_escaner and self.conexion_escaner.is_open:
            try:
                self.conexion_escaner.write(bytes([0x80, 0, 0]))
                self.conexion_escaner.flush()
            except: pass
            self.conexion_escaner.close()
            
        self.root.after(0, self.restaurar_botones)

    def restaurar_botones(self):
        self.btn_play.config(state=tk.NORMAL)
        self.btn_next.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = MegaOrquestaPachatron(root)
    root.mainloop()