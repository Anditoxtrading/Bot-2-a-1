"""
🚀 BOT MONITOR BINANCE - ENVÍA SEÑALES AL BOT 2 A 1
Monitorea precios en Binance Futures y envía alertas al bot 2 a 1
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import threading
import time
from datetime import datetime
from binance.client import Client
import requests
from decimal import Decimal
import json

# ===== CONFIGURACIÓN =====
BOT_2A1_URL = "http://localhost:5000"
DATABASE_FILE = "monitor_binance.db"

# Colores
COLOR_BG = "#1e1e1e"
COLOR_FG = "#ffffff"
COLOR_ACCENT = "#4CAF50"
COLOR_LONG = "#00ff00"
COLOR_SHORT = "#ff5555"
COLOR_PANEL = "#2d2d2d"
COLOR_ENTRY = "#3d3d3d"
COLOR_BUTTON = "#4CAF50"
COLOR_BUTTON_HOVER = "#66BB6A"

class MonitorBinanceBot:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 BOT MONITOR BINANCE → BOT 2 A 1")
        self.root.geometry("1200x700")
        self.root.configure(bg=COLOR_BG)

        # Variables de control
        self.monitoring = False
        self.binance_client = None
        self.monitored_coins = {}  # {symbol: {"long_entry": price, "long_sl": price, "short_entry": price, "short_sl": price, "current_price": price}}
        self.triggered_signals = set()  # Para evitar enviar la misma señal múltiples veces

        # Base de datos
        self.init_database()

        # Interfaz gráfica
        self.create_gui()

        # Cargar monedas guardadas
        self.load_coins_from_db()

        # Verificar conexión con Bot 2 a 1
        self.check_bot_2a1_connection()

    def init_database(self):
        """Inicializa la base de datos SQLite"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitored_coins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                long_entry REAL,
                long_sl REAL,
                short_entry REAL,
                short_sl REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def create_gui(self):
        """Crea la interfaz gráfica"""

        # ===== TÍTULO =====
        title_frame = tk.Frame(self.root, bg=COLOR_BG)
        title_frame.pack(pady=10)

        tk.Label(
            title_frame,
            text="🚀 BOT MONITOR BINANCE",
            font=("Arial", 18, "bold"),
            bg=COLOR_BG,
            fg=COLOR_ACCENT
        ).pack()

        tk.Label(
            title_frame,
            text="Envía señales automáticas al Bot 2 a 1",
            font=("Arial", 10),
            bg=COLOR_BG,
            fg=COLOR_FG
        ).pack()

        # ===== STATUS BAR =====
        status_frame = tk.Frame(self.root, bg=COLOR_PANEL, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = tk.Label(
            status_frame,
            text="⚪ Detenido",
            font=("Arial", 10, "bold"),
            bg=COLOR_PANEL,
            fg="#ffaa00"
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.bot_2a1_status = tk.Label(
            status_frame,
            text="🔴 Bot 2 a 1: Desconectado",
            font=("Arial", 9),
            bg=COLOR_PANEL,
            fg="#ff5555"
        )
        self.bot_2a1_status.pack(side=tk.RIGHT, padx=10, pady=5)

        # ===== PANEL DE ENTRADA =====
        input_frame = tk.LabelFrame(
            self.root,
            text="➕ Agregar/Editar Moneda",
            bg=COLOR_PANEL,
            fg=COLOR_FG,
            font=("Arial", 11, "bold"),
            relief=tk.RIDGE,
            bd=2
        )
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        # Fila 1: Moneda
        row1 = tk.Frame(input_frame, bg=COLOR_PANEL)
        row1.pack(pady=5, padx=10, fill=tk.X)

        tk.Label(row1, text="Moneda:", bg=COLOR_PANEL, fg=COLOR_FG, width=15, anchor='w').pack(side=tk.LEFT)
        self.symbol_entry = tk.Entry(row1, bg=COLOR_ENTRY, fg=COLOR_FG, insertbackground=COLOR_FG, width=20)
        self.symbol_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(row1, text="(Ejemplo: BTCUSDT)", bg=COLOR_PANEL, fg="#888888", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)

        # Fila 2: LONG Entry y SL
        row2 = tk.Frame(input_frame, bg=COLOR_PANEL)
        row2.pack(pady=5, padx=10, fill=tk.X)

        tk.Label(row2, text="🟢 LONG Entry:", bg=COLOR_PANEL, fg=COLOR_LONG, width=15, anchor='w').pack(side=tk.LEFT)
        self.long_entry = tk.Entry(row2, bg=COLOR_ENTRY, fg=COLOR_FG, insertbackground=COLOR_FG, width=15)
        self.long_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="SL:", bg=COLOR_PANEL, fg=COLOR_LONG, width=8, anchor='w').pack(side=tk.LEFT, padx=(20,0))
        self.long_sl = tk.Entry(row2, bg=COLOR_ENTRY, fg=COLOR_FG, insertbackground=COLOR_FG, width=15)
        self.long_sl.pack(side=tk.LEFT, padx=5)

        # Fila 3: SHORT Entry y SL
        row3 = tk.Frame(input_frame, bg=COLOR_PANEL)
        row3.pack(pady=5, padx=10, fill=tk.X)

        tk.Label(row3, text="🔴 SHORT Entry:", bg=COLOR_PANEL, fg=COLOR_SHORT, width=15, anchor='w').pack(side=tk.LEFT)
        self.short_entry = tk.Entry(row3, bg=COLOR_ENTRY, fg=COLOR_FG, insertbackground=COLOR_FG, width=15)
        self.short_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(row3, text="SL:", bg=COLOR_PANEL, fg=COLOR_SHORT, width=8, anchor='w').pack(side=tk.LEFT, padx=(20,0))
        self.short_sl = tk.Entry(row3, bg=COLOR_ENTRY, fg=COLOR_FG, insertbackground=COLOR_FG, width=15)
        self.short_sl.pack(side=tk.LEFT, padx=5)

        # Fila 4: Botones
        row4 = tk.Frame(input_frame, bg=COLOR_PANEL)
        row4.pack(pady=10, padx=10)

        self.add_button = tk.Button(
            row4,
            text="➕ Agregar Moneda",
            command=self.add_coin,
            bg=COLOR_BUTTON,
            fg=COLOR_FG,
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            bd=2,
            padx=15,
            cursor="hand2"
        )
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.update_button = tk.Button(
            row4,
            text="✏️ Actualizar",
            command=self.update_coin,
            bg="#2196F3",
            fg=COLOR_FG,
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            bd=2,
            padx=15,
            cursor="hand2"
        )
        self.update_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = tk.Button(
            row4,
            text="🗑️ Limpiar",
            command=self.clear_inputs,
            bg="#FF9800",
            fg=COLOR_FG,
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            bd=2,
            padx=15,
            cursor="hand2"
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # ===== TABLA DE MONEDAS =====
        table_frame = tk.LabelFrame(
            self.root,
            text="📊 Monedas Monitoreadas",
            bg=COLOR_PANEL,
            fg=COLOR_FG,
            font=("Arial", 11, "bold"),
            relief=tk.RIDGE,
            bd=2
        )
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=("symbol", "long_distance", "short_distance", "long_entry", "long_sl", "short_entry", "short_sl"),
            show="headings",
            yscrollcommand=scrollbar.set,
            height=10
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.tree.yview)

        # Configurar columnas
        self.tree.heading("symbol", text="Moneda")
        self.tree.heading("long_distance", text="🟢 Dist. Long")
        self.tree.heading("short_distance", text="🔴 Dist. Short")
        self.tree.heading("long_entry", text="🟢 Long Entry")
        self.tree.heading("long_sl", text="🟢 Long SL")
        self.tree.heading("short_entry", text="🔴 Short Entry")
        self.tree.heading("short_sl", text="🔴 Short SL")

        self.tree.column("symbol", width=100, anchor="center")
        self.tree.column("long_distance", width=110, anchor="center")
        self.tree.column("short_distance", width=110, anchor="center")
        self.tree.column("long_entry", width=110, anchor="center")
        self.tree.column("long_sl", width=110, anchor="center")
        self.tree.column("short_entry", width=110, anchor="center")
        self.tree.column("short_sl", width=110, anchor="center")

        # Estilo de Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLOR_ENTRY, foreground=COLOR_FG, fieldbackground=COLOR_ENTRY, rowheight=25)
        style.configure("Treeview.Heading", background=COLOR_BUTTON, foreground=COLOR_FG, font=("Arial", 9, "bold"))
        style.map("Treeview", background=[("selected", COLOR_BUTTON)])

        # Eventos
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_tree_right_click)

        # ===== LOG =====
        log_frame = tk.LabelFrame(
            self.root,
            text="📝 Log de Actividad",
            bg=COLOR_PANEL,
            fg=COLOR_FG,
            font=("Arial", 11, "bold"),
            relief=tk.RIDGE,
            bd=2
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            bg=COLOR_ENTRY,
            fg=COLOR_FG,
            font=("Consolas", 9),
            height=8,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ===== BOTÓN INICIAR/DETENER =====
        control_frame = tk.Frame(self.root, bg=COLOR_BG)
        control_frame.pack(pady=10)

        self.start_button = tk.Button(
            control_frame,
            text="▶️ INICIAR MONITOREO",
            command=self.toggle_monitoring,
            bg=COLOR_BUTTON,
            fg=COLOR_FG,
            font=("Arial", 12, "bold"),
            relief=tk.RAISED,
            bd=3,
            padx=30,
            pady=10,
            cursor="hand2"
        )
        self.start_button.pack()

        # Log inicial
        self.log("✅ Bot Monitor Binance iniciado")
        self.log("📊 Listo para agregar monedas y comenzar el monitoreo")

    def log(self, message):
        """Escribe en el log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def check_bot_2a1_connection(self):
        """Verifica la conexión con el Bot 2 a 1"""
        try:
            response = requests.get(f"{BOT_2A1_URL}/status", timeout=3)
            if response.status_code == 200:
                data = response.json()
                self.bot_2a1_status.config(
                    text=f"🟢 Bot 2 a 1: Conectado ({data['posiciones_abiertas']}/{data['max_posiciones']} posiciones)",
                    fg=COLOR_LONG
                )
                self.log("✅ Bot 2 a 1 detectado y disponible")
                return True
            else:
                self.bot_2a1_status.config(text="🔴 Bot 2 a 1: Error", fg=COLOR_SHORT)
                self.log("⚠️ Bot 2 a 1 no responde correctamente")
                return False
        except Exception as e:
            self.bot_2a1_status.config(text="🔴 Bot 2 a 1: Desconectado", fg=COLOR_SHORT)
            self.log(f"⚠️ No se pudo conectar con Bot 2 a 1: {e}")
            return False

    def add_coin(self):
        """Agrega una moneda a la lista de monitoreo"""
        symbol = self.symbol_entry.get().strip().upper()

        if not symbol:
            messagebox.showerror("Error", "Debes ingresar una moneda")
            return

        try:
            long_entry = float(self.long_entry.get()) if self.long_entry.get() else None
            long_sl = float(self.long_sl.get()) if self.long_sl.get() else None
            short_entry = float(self.short_entry.get()) if self.short_entry.get() else None
            short_sl = float(self.short_sl.get()) if self.short_sl.get() else None

            # Validar que al menos un lado esté configurado
            if not (long_entry and long_sl) and not (short_entry and short_sl):
                messagebox.showerror("Error", "Debes configurar al menos un lado (LONG o SHORT)")
                return

            # Guardar en base de datos
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO monitored_coins (symbol, long_entry, long_sl, short_entry, short_sl)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, long_entry, long_sl, short_entry, short_sl))
            conn.commit()
            conn.close()

            # Actualizar tabla
            self.load_coins_from_db()
            self.clear_inputs()

            self.log(f"✅ {symbol} agregado correctamente")
            messagebox.showinfo("Éxito", f"{symbol} agregado correctamente")

        except ValueError:
            messagebox.showerror("Error", "Los precios deben ser números válidos")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"{symbol} ya está en la lista")

    def update_coin(self):
        """Actualiza una moneda existente"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Selecciona una moneda de la tabla")
            return

        symbol = self.symbol_entry.get().strip().upper()
        if not symbol:
            messagebox.showerror("Error", "Debes ingresar una moneda")
            return

        try:
            long_entry = float(self.long_entry.get()) if self.long_entry.get() else None
            long_sl = float(self.long_sl.get()) if self.long_sl.get() else None
            short_entry = float(self.short_entry.get()) if self.short_entry.get() else None
            short_sl = float(self.short_sl.get()) if self.short_sl.get() else None

            # Actualizar en base de datos
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE monitored_coins
                SET long_entry=?, long_sl=?, short_entry=?, short_sl=?, updated_at=CURRENT_TIMESTAMP
                WHERE symbol=?
            """, (long_entry, long_sl, short_entry, short_sl, symbol))
            conn.commit()
            conn.close()

            # Actualizar tabla
            self.load_coins_from_db()
            self.clear_inputs()

            self.log(f"✏️ {symbol} actualizado correctamente")
            messagebox.showinfo("Éxito", f"{symbol} actualizado correctamente")

        except ValueError:
            messagebox.showerror("Error", "Los precios deben ser números válidos")

    def clear_inputs(self):
        """Limpia los campos de entrada"""
        self.symbol_entry.delete(0, tk.END)
        self.long_entry.delete(0, tk.END)
        self.long_sl.delete(0, tk.END)
        self.short_entry.delete(0, tk.END)
        self.short_sl.delete(0, tk.END)

    def on_tree_double_click(self, event):
        """Carga los datos de la moneda seleccionada en los campos de entrada"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']

            self.symbol_entry.delete(0, tk.END)
            self.symbol_entry.insert(0, values[0])

            self.long_entry.delete(0, tk.END)
            if values[3] and values[3] != "---":
                self.long_entry.insert(0, values[3])

            self.long_sl.delete(0, tk.END)
            if values[4] and values[4] != "---":
                self.long_sl.insert(0, values[4])

            self.short_entry.delete(0, tk.END)
            if values[5] and values[5] != "---":
                self.short_entry.insert(0, values[5])

            self.short_sl.delete(0, tk.END)
            if values[6] and values[6] != "---":
                self.short_sl.insert(0, values[6])

    def on_tree_right_click(self, event):
        """Muestra menú contextual para eliminar"""
        selected = self.tree.selection()
        if selected:
            menu = tk.Menu(self.root, tearoff=0, bg=COLOR_PANEL, fg=COLOR_FG)
            menu.add_command(label="🗑️ Eliminar", command=lambda: self.delete_coin(selected[0]))
            menu.post(event.x_root, event.y_root)

    def delete_coin(self, item):
        """Elimina una moneda"""
        values = self.tree.item(item)['values']
        symbol = values[0]

        if messagebox.askyesno("Confirmar", f"¿Eliminar {symbol}?"):
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM monitored_coins WHERE symbol=?", (symbol,))
            conn.commit()
            conn.close()

            self.load_coins_from_db()
            self.log(f"🗑️ {symbol} eliminado")

    def load_coins_from_db(self):
        """Carga las monedas desde la base de datos"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Cargar desde DB
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, long_entry, long_sl, short_entry, short_sl FROM monitored_coins")
        rows = cursor.fetchall()
        conn.close()

        # Actualizar diccionario de monedas monitoreadas
        self.monitored_coins = {}
        for row in rows:
            symbol, long_entry, long_sl, short_entry, short_sl = row
            self.monitored_coins[symbol] = {
                "long_entry": long_entry,
                "long_sl": long_sl,
                "short_entry": short_entry,
                "short_sl": short_sl,
                "current_price": None
            }

            # Agregar a la tabla
            self.tree.insert("", tk.END, values=(
                symbol,
                "---",  # Distancia Long
                "---",  # Distancia Short
                long_entry if long_entry else "---",
                long_sl if long_sl else "---",
                short_entry if short_entry else "---",
                short_sl if short_sl else "---"
            ))

    def toggle_monitoring(self):
        """Inicia o detiene el monitoreo"""
        if not self.monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        """Inicia el monitoreo"""
        if not self.monitored_coins:
            messagebox.showwarning("Advertencia", "No hay monedas para monitorear")
            return

        # Verificar conexión con Bot 2 a 1
        if not self.check_bot_2a1_connection():
            if not messagebox.askyesno("Advertencia", "No se detectó el Bot 2 a 1. ¿Continuar de todos modos?"):
                return

        self.monitoring = True
        self.start_button.config(text="⏸️ DETENER MONITOREO", bg="#ff5555")
        self.status_label.config(text="🟢 Monitoreando", fg=COLOR_LONG)

        self.log("🚀 Iniciando monitoreo...")

        # Iniciar hilo de monitoreo
        monitor_thread = threading.Thread(target=self.monitor_prices, daemon=True)
        monitor_thread.start()

    def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.monitoring = False
        self.start_button.config(text="▶️ INICIAR MONITOREO", bg=COLOR_BUTTON)
        self.status_label.config(text="⚪ Detenido", fg="#ffaa00")
        self.log("⏸️ Monitoreo detenido")

    def monitor_prices(self):
        """Monitorea los precios de las monedas usando la API REST de Binance"""
        try:
            # Crear cliente de Binance (sin API keys, solo para datos públicos)
            self.binance_client = Client()

            self.log(f"📊 Monitoreando {len(self.monitored_coins)} monedas...")

            while self.monitoring:
                for symbol in list(self.monitored_coins.keys()):
                    try:
                        # Obtener precio actual
                        ticker = self.binance_client.futures_symbol_ticker(symbol=symbol)
                        current_price = float(ticker['price'])

                        # Actualizar precio actual
                        self.monitored_coins[symbol]["current_price"] = current_price

                        # Actualizar tabla
                        self.update_table_price(symbol, current_price)

                        # Verificar si se alcanzó algún nivel
                        self.check_price_levels(symbol, current_price)

                    except Exception as e:
                        self.log(f"❌ Error al obtener precio de {symbol}: {e}")

                time.sleep(0.5)  # Actualizar cada 0.5 segundos (2 veces por segundo)

        except Exception as e:
            self.log(f"❌ Error en el monitoreo: {e}")
            self.monitoring = False
            self.start_button.config(text="▶️ INICIAR MONITOREO", bg=COLOR_BUTTON)
            self.status_label.config(text="⚪ Detenido", fg="#ffaa00")

    def update_table_price(self, symbol, current_price):
        """Actualiza las distancias en la tabla"""
        coin = self.monitored_coins.get(symbol)
        if not coin:
            return

        # Calcular distancia LONG (misma fórmula que el Oráculo)
        long_distance_text = "---"
        if coin["long_entry"]:
            long_entry = coin["long_entry"]
            distance_pct = abs((long_entry - current_price) / current_price * 100)
            # Determinar si está por encima o por debajo
            if current_price > long_entry:
                long_distance_text = f"+{distance_pct:.2f}%"  # Precio por encima del entry
            else:
                long_distance_text = f"-{distance_pct:.2f}%"  # Precio por debajo del entry (activado)

        # Calcular distancia SHORT (misma fórmula que el Oráculo)
        short_distance_text = "---"
        if coin["short_entry"]:
            short_entry = coin["short_entry"]
            distance_pct = abs((short_entry - current_price) / current_price * 100)
            # Determinar si está por encima o por debajo
            if current_price < short_entry:
                short_distance_text = f"-{distance_pct:.2f}%"  # Precio por debajo del entry
            else:
                short_distance_text = f"+{distance_pct:.2f}%"  # Precio por encima del entry (activado)

        # Actualizar tabla
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values[0] == symbol:
                self.tree.item(item, values=(
                    values[0],
                    long_distance_text,   # Distancia Long
                    short_distance_text,  # Distancia Short
                    values[3],            # Long Entry
                    values[4],            # Long SL
                    values[5],            # Short Entry
                    values[6]             # Short SL
                ))
                break

    def check_price_levels(self, symbol, current_price):
        """Verifica si el precio alcanzó algún nivel de entrada"""
        coin = self.monitored_coins[symbol]

        # Verificar LONG Entry
        if coin["long_entry"] and coin["long_sl"]:
            signal_key = f"{symbol}_LONG"
            if signal_key not in self.triggered_signals and current_price <= coin["long_entry"]:
                self.log(f"🟢 {symbol}: Precio {current_price:.8f} alcanzó LONG Entry {coin['long_entry']}")
                self.send_signal_to_bot_2a1(symbol, "long", coin["long_entry"], coin["long_sl"])
                self.triggered_signals.add(signal_key)
                # Marcar en rojo y eliminar después de 3 segundos
                self.mark_and_remove_coin(symbol)
                return  # Salir para no verificar SHORT

        # Verificar SHORT Entry
        if coin["short_entry"] and coin["short_sl"]:
            signal_key = f"{symbol}_SHORT"
            if signal_key not in self.triggered_signals and current_price >= coin["short_entry"]:
                self.log(f"🔴 {symbol}: Precio {current_price:.8f} alcanzó SHORT Entry {coin['short_entry']}")
                self.send_signal_to_bot_2a1(symbol, "short", coin["short_entry"], coin["short_sl"])
                self.triggered_signals.add(signal_key)
                # Marcar en rojo y eliminar después de 3 segundos
                self.mark_and_remove_coin(symbol)
                return  # Salir

    def mark_and_remove_coin(self, symbol):
        """Marca la moneda en rojo y la elimina después de 3 segundos"""
        # Marcar en rojo en la tabla
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values[0] == symbol:
                self.tree.item(item, tags=('triggered',))
                self.tree.tag_configure('triggered', background='#ff5555', foreground='#ffffff')
                break

        self.log(f"🔴 {symbol} marcado - Se eliminará en 3 segundos...")

        # Programar eliminación después de 3 segundos
        threading.Timer(3.0, lambda: self.remove_coin_from_monitoring(symbol)).start()

    def remove_coin_from_monitoring(self, symbol):
        """Elimina la moneda del monitoreo y de la base de datos"""
        try:
            # Eliminar de la base de datos
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM monitored_coins WHERE symbol=?", (symbol,))
            conn.commit()
            conn.close()

            # Eliminar del diccionario
            if symbol in self.monitored_coins:
                del self.monitored_coins[symbol]

            # Eliminar de la tabla
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                if values[0] == symbol:
                    self.tree.delete(item)
                    break

            self.log(f"🗑️ {symbol} eliminado del monitoreo")

        except Exception as e:
            self.log(f"❌ Error al eliminar {symbol}: {e}")

    def send_signal_to_bot_2a1(self, symbol, side, entry_price, sl_price):
        """Envía la señal al Bot 2 a 1"""
        try:
            # Calcular distancia del SL en porcentaje
            if side == "long":
                distancia_sl = ((entry_price - sl_price) / entry_price) * 100
            else:  # short
                distancia_sl = ((sl_price - entry_price) / entry_price) * 100

            # Preparar datos
            url = f"{BOT_2A1_URL}/signal"
            data = {
                "symbol": symbol,
                "side": side,
                "distancia_sl": round(distancia_sl, 2)
            }

            self.log(f"📡 Enviando señal al Bot 2 a 1: {symbol} {side.upper()} (SL: {distancia_sl:.2f}%)")

            # Enviar señal
            response = requests.post(url, json=data, timeout=10)
            resultado = response.json()

            if response.status_code == 200:
                if resultado['status'] == 'success':
                    self.log(f"✅ Señal enviada exitosamente: {resultado['message']}")
                    # Removido messagebox para no bloquear el monitoreo
                elif resultado['status'] == 'ignored':
                    self.log(f"⚠️ Señal ignorada: {resultado['message']}")
                elif resultado['status'] == 'rejected':
                    self.log(f"⚠️ Señal rechazada: {resultado['message']}")
            else:
                self.log(f"❌ Error al enviar señal: {resultado['message']}")

        except Exception as e:
            self.log(f"❌ Error al enviar señal al Bot 2 a 1: {e}")
            # Removido messagebox para no bloquear el monitoreo


# ===== MAIN =====
if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorBinanceBot(root)
    root.mainloop()
