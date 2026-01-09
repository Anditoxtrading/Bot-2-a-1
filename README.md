# 🚀 Sistema de Trading Automatizado 2:1

Sistema de **trading automatizado** que monitorea precios en **Binance Futures** y ejecuta operaciones en **Bybit Futures**, aplicando un **ratio de ganancia 2:1**, con **gestión de riesgo automática** y **protección progresiva**.

---

## 📌 Tabla de Contenidos

- [📋 Descripción](#-descripción)
- [🤖 Arquitectura del Sistema](#-arquitectura-del-sistema)
- [✨ Características](#-características)
- [🔧 Requisitos Previos](#-requisitos-previos)
- [📥 Instalación](#-instalación)
- [🔑 Configuración de Credenciales](#-configuración-de-credenciales)
- [📲 Notificaciones por Telegram](#-notificaciones-por-telegram)
- [⚠️ Advertencia de Riesgo](#️-advertencia-de-riesgo)

---

## 📋 Descripción

Este proyecto implementa un sistema de trading algorítmico compuesto por **dos bots independientes** que trabajan de forma coordinada para detectar oportunidades y ejecutar operaciones con control de riesgo.

---

## 🤖 Arquitectura del Sistema

El sistema está compuesto por los siguientes módulos:

### 🔹 Bot 2:1 (Bybit)

- Ejecuta operaciones en **Bybit Futures**
- Aplica **ratio riesgo/beneficio 1:2**
- Manejo automático de:
  - Stop Loss
  - Take Profit
  - Protección progresiva de ganancias

### 🔹 Bot Monitor Oráculo (Binance)

- Monitorea precios en **Binance Futures**
- Analiza movimientos en tiempo real
- Envía señales automáticas al Bot 2:1

---

## ✨ Características

- ✅ **Ratio 2:1** — Gana el doble de lo que arriesgas por operación  
- 🛡️ **Protección Progresiva** — Stop Loss dinámico que protege ganancias  
- 📊 **Monitoreo en Tiempo Real** — Actualización constante de precios  
- 📱 **Notificaciones por Telegram** — Alertas instantáneas  
- 🎯 **Gestión de Riesgo Automática** — Cálculo automático de posiciones  
- ⏳ **Sistema de Cooldown** — Evita operar la misma moneda repetidamente  
- 💻 **Interfaz Gráfica (GUI)** — Monitor visual con **Tkinter**

---

## 🔧 Requisitos Previos

- 🐍 **Python 3.8 o superior**
- 💼 Cuenta en **Bybit** con API Keys habilitadas
- 📈 Cuenta en **Binance** (no requiere API Keys)
- 🤖 Bot de **Telegram** configurado
- 🖥️ Sistema operativo:
  - Windows
  - Linux
  - macOS

---

## 📥 Instalación

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/bot-trading-2a1.git
cd bot-trading-2a1
También puedes descargar el proyecto en formato ZIP y descomprimirlo.

2️⃣ Instalar Python
Descárgalo desde:
https://www.python.org/downloads/

3️⃣ Instalar dependencias
bash
Copiar código
pip install pybit pytelegrambotapi flask python-binance requests
🔑 Configuración de Credenciales
Edita el archivo config.py:

python
Copiar código
# API Keys de Bybit
api_key = "TU_API_KEY_DE_BYBIT"
api_secret = "TU_API_SECRET_DE_BYBIT"

# Telegram
token_telegram = "TU_TOKEN_DE_TELEGRAM"
chat_id = "TU_CHAT_ID_DE_TELEGRAM"
🔐 Cómo obtener las credenciales
🟡 Bybit API Keys
Inicia sesión en https://www.bybit.com

Ve a API → API Management

Crea una nueva API Key

Habilita los permisos:

✅ Read-Write (Trading)

✅ Contract Trading

Guarda tu API Key y Secret Key

⚠️ Recomendado: activa IP Whitelisting

🔵 Telegram Bot
Busca @BotFather en Telegram

Ejecuta:

bash
Copiar código
/newbot
Sigue las instrucciones

Guarda el token generado

Obtener tu chat_id
Busca @userinfobot

Inicia una conversación

Copia tu chat_id

📲 Notificaciones por Telegram
El sistema enviará alertas sobre:

📈 Apertura de operaciones

🎯 Take Profit alcanzado

🛑 Stop Loss activado

🔄 Protección progresiva activada

⚠️ Errores o eventos críticos

⚠️ Advertencia de Riesgo
Este software es solo para fines educativos.
El trading con futuros implica alto riesgo financiero y puede resultar en la pérdida total del capital.
Usa este sistema bajo tu propia responsabilidad.
