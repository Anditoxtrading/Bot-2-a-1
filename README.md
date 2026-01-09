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
- 🛡️ **Protección Progresiva** — Stop Loss dinámico para asegurar beneficios  
- 📊 **Monitoreo en Tiempo Real** — Actualización constante de precios  
- 📱 **Notificaciones por Telegram** — Alertas inmediatas de cada evento  
- 🎯 **Gestión de Riesgo Automática** — Cálculo preciso del tamaño de posición  
- ⏳ **Sistema de Cooldown** — Evita operar repetidamente el mismo activo  
- 💻 **Interfaz Gráfica (GUI)** — Monitor visual desarrollado con **Tkinter**

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
