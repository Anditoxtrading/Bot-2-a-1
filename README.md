# 🚀 Sistema de Trading Automatizado 2:1

Sistema de **trading automatizado** que monitorea precios en **Binance Futures** y ejecuta operaciones en **Bybit Futures**, utilizando un **ratio riesgo/beneficio 1:2**, con **gestión de riesgo automática** y **protección progresiva**.

---

## 📋 Descripción

Sistema compuesto por **dos bots independientes** que trabajan en conjunto para detectar oportunidades y ejecutar operaciones de forma automatizada y controlada.

---

## 🤖 Arquitectura del Sistema

### 🔹 Bot 2:1 (Bybit)
- Ejecuta operaciones en **Bybit Futures**
- Ratio **1:2 (riesgo / ganancia)**
- Stop Loss y Take Profit automáticos
- Protección progresiva de ganancias

### 🔹 Bot Monitor Oráculo (Binance)
- Monitorea precios en **Binance Futures**
- Analiza movimientos en tiempo real
- Envía señales al Bot 2:1

---

## ✨ Características

- ✅ Ratio **2:1**
- 🛡️ Stop Loss dinámico
- 📊 Monitoreo en tiempo real
- 📱 Alertas por **Telegram**
- 🎯 Gestión de riesgo automática
- ⏳ Cooldown por activo
- 💻 Interfaz gráfica con **Tkinter**

---

## 🔧 Requisitos

- Python **3.4+**
- Cuenta en **Bybit** (API habilitada)
- Cuenta en **Binance**
- Bot de **Telegram**
- Windows / Linux / macOS

---

## 📥 Instalación

### 1️⃣ Clonar repositorio

```bash
git clone https://github.com/tu-usuario/bot-trading-2a1.git
cd bot-trading-2a1
```

2️⃣ Instalar dependencias
```bash
pip install pybit pytelegrambotapi flask python-binance requests
```
🔑 Configuración

Edita el archivo config.py:
```bash
api_key = "TU_API_KEY_DE_BYBIT"
api_secret = "TU_API_SECRET_DE_BYBIT"

token_telegram = "TU_TOKEN_DE_TELEGRAM"
chat_id = "TU_CHAT_ID
```

⚠️ Advertencia

Este software es solo educativo.
El trading con futuros implica alto riesgo financiero.
Úsalo bajo tu propia responsabilidad.
