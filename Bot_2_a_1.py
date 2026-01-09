import config
import time
from pybit.unified_trading import HTTP
from decimal import Decimal, ROUND_DOWN, ROUND_FLOOR
import threading
import telebot
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

# ===== CONFIGURACIÓN =====
session = HTTP(
    testnet=False,
    api_key=config.api_key,
    api_secret=config.api_secret,
    recv_window=20000  # Aumentado a 20000ms para manejar diferencias de timestamp
)

# PARAMETROS PARA OPERAR
monto_base_usdt = Decimal(100)  # Monto base en USDT
margen_proteccion_progresiva = Decimal(2.0)  # Margen de 2% para protección progresiva
Numero_de_posiciones = 1  # Solo 1 posición simultánea
margen_extra_sl = Decimal(0.5)  # Margen extra de 0.5% para alejar el SL

# Diccionarios de control
posiciones_con_stop = {}  # {symbol: True/False} - Si ya se activó protección 1:1
tracking_posiciones = {}  # {symbol: {"precio_maximo": Decimal, "precio_entrada": Decimal, "side": str, "distancia_sl": Decimal}}
monedas_operadas = {}  # {symbol: timestamp_operacion}
cooldown_minutos = 60

# Telegram
bot_token = config.token_telegram
bot = telebot.TeleBot(bot_token)
chat_id = config.chat_id

# Flask API
app = Flask(__name__)

# ===== FUNCIONES DE TELEGRAM =====
def enviar_mensaje_telegram(chat_id, mensaje):
    try:
        bot.send_message(chat_id, mensaje, parse_mode='HTML')
    except Exception as e:
        print(f"No se pudo enviar el mensaje a Telegram: {e}")

# ===== FUNCIONES DE BYBIT =====
def verificar_symbol_en_bybit(symbol):
    """Verifica si el symbol existe en Bybit futuros"""
    try:
        response = session.get_instruments_info(category="linear", symbol=symbol)
        if response['retCode'] == 0 and len(response['result']['list']) > 0:
            return True
        return False
    except Exception as e:
        print(f"Error al verificar symbol {symbol}: {e}")
        return False

def get_current_position(symbol):
    try:
        response_positions = session.get_positions(category="linear", symbol=symbol)
        if response_positions['retCode'] == 0:
            return response_positions['result']['list']
        else:
            print(f"Error al obtener la posición: {response_positions}")
            return None
    except Exception as e:
        print(f"Error al obtener la posición: {e}")
        return None

def get_open_positions_count():
    try:
        response_positions = session.get_positions(category="linear", settleCoin="USDT")
        if response_positions['retCode'] == 0:
            positions = response_positions['result']['list']
            open_positions = [position for position in positions if Decimal(position['size']) != 0]
            return len(open_positions)
        else:
            print(f"Error al obtener el conteo de posiciones abiertas: {response_positions}")
            return 0
    except Exception as e:
        print(f"Error al obtener el conteo de posiciones abiertas: {e}")
        return 0

def qty_step(symbol, amount_usdt):
    try:
        tickers = session.get_tickers(symbol=symbol, category="linear")
        for ticker_data in tickers["result"]["list"]:
            last_price = float(ticker_data["lastPrice"])

        last_price_decimal = Decimal(last_price)

        step_info = session.get_instruments_info(category="linear", symbol=symbol)
        qty_step = Decimal(step_info['result']['list'][0]['lotSizeFilter']['qtyStep'])

        base_asset_qty = amount_usdt / last_price_decimal

        qty_step_str = str(qty_step)
        if '.' in qty_step_str:
            decimals = len(qty_step_str.split('.')[1])
            base_asset_qty_final = round(base_asset_qty, decimals)
        else:
            base_asset_qty_final = int(base_asset_qty)

        return base_asset_qty_final
    except Exception as e:
        print(f"Error al calcular la cantidad del activo base: {e}")
        return None

def adjust_price(symbol, price):
    try:
        instrument_info = session.get_instruments_info(category="linear", symbol=symbol)
        tick_size = float(instrument_info['result']['list'][0]['priceFilter']['tickSize'])
        price_scale = int(instrument_info['result']['list'][0]['priceScale'])

        tick_dec = Decimal(f"{tick_size}")
        precision = Decimal(f"{10**price_scale}")
        price_decimal = Decimal(f"{price}")
        adjusted_price = (price_decimal * precision) / precision
        adjusted_price = (adjusted_price / tick_dec).quantize(Decimal('1'), rounding=ROUND_FLOOR) * tick_dec

        return float(adjusted_price)
    except Exception as e:
        print(f"Error al ajustar el precio: {e}")
        return None

# ===== CÁLCULO DE POSICIÓN 2 A 1 =====
def calcular_monto_operacion(monto_base, distancia_sl_porcentaje):
    """
    Calcula el monto real de la operación para lograr el ratio 2:1
    Ejemplo: Si monto_base = 100 USDT y SL = 1.5%, entonces operar con 66.67 USDT
    Para que si pierde el 1.5%, pierda 1 USDT, pero si gana 3% (2x1.5%), gane 2 USDT
    """
    monto_operacion = monto_base / Decimal(distancia_sl_porcentaje)
    return monto_operacion

def calcular_precio_proteccion_1a1(precio_entrada, distancia_sl_porcentaje, side):
    """
    Calcula el precio donde se debe colocar el SL en el precio de entrada (1 a 1)
    Esto ocurre cuando el precio se mueve 2x la distancia del SL (2:1)
    """
    distancia_decimal = distancia_sl_porcentaje / Decimal(100)

    if side == "Buy":
        # Para Long: el precio debe subir 2x la distancia del SL
        precio_objetivo_2a1 = precio_entrada * (Decimal(1) + (distancia_decimal * 2))
        return precio_objetivo_2a1
    elif side == "Sell":
        # Para Short: el precio debe bajar 2x la distancia del SL
        precio_objetivo_2a1 = precio_entrada * (Decimal(1) - (distancia_decimal * 2))
        return precio_objetivo_2a1

    return None

# ===== APERTURA DE POSICIONES =====
def abrir_posicion_long(symbol, monto_operacion, distancia_sl_porcentaje):
    try:
        if get_open_positions_count() >= Numero_de_posiciones:
            mensaje_count = "⚠️ Se alcanzó el máximo de posiciones abiertas. No se abrirá una nueva posición."
            enviar_mensaje_telegram(chat_id=chat_id, mensaje=mensaje_count)
            print(mensaje_count)
            return False

        positions_list = get_current_position(symbol)
        if positions_list and any(Decimal(position['size']) != 0 for position in positions_list):
            print(f"Ya hay una posición abierta en {symbol}. No se abrirá otra posición.")
            return False

        # Calcular cantidad a operar
        base_asset_qty_final = qty_step(symbol, monto_operacion)
        if base_asset_qty_final is None:
            return False

        # Abrir posición a mercado
        response_market_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            orderType="Market",
            qty=str(base_asset_qty_final),
        )

        time.sleep(3)
        if response_market_order['retCode'] != 0:
            print("❌ Error al abrir la posición: La orden de mercado no se completó correctamente.")
            return False

        # Obtener precio de entrada
        positions_list = get_current_position(symbol)
        current_price = Decimal(positions_list[0]['avgPrice'])

        # Calcular y colocar stop loss
        distancia_decimal = distancia_sl_porcentaje / Decimal(100)
        price_sl = adjust_price(symbol, current_price * (Decimal(1) - distancia_decimal))

        stop_loss_order = session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=str(price_sl),
            slTriggerBy="LastPrice",
            tpslMode="Full",
            slOrderType="Market",
        )

        # Calcular precio objetivo para protección 1 a 1
        precio_proteccion = calcular_precio_proteccion_1a1(current_price, distancia_sl_porcentaje, "Buy")

        # Inicializar tracking de la posición
        tracking_posiciones[symbol] = {
            "precio_maximo": current_price,
            "precio_entrada": current_price,
            "side": "Buy",
            "distancia_sl": distancia_sl_porcentaje
        }

        Mensaje_market = (
            f"<b>🟢 ¡POSICIÓN LONG ABIERTA! (2:1)</b>\n"
            f"🔹 Símbolo: <b>{symbol}</b>\n"
            f"💰 Monto operado: <b>{monto_operacion:.2f} USDT</b>\n"
            f"📍 Precio entrada: <b>{current_price}</b>\n"
            f"🛡️ Stop Loss: <b>{price_sl}</b> (-{float(distancia_sl_porcentaje):.2f}%)\n"
            f"🎯 Protección 1:1 en: <b>{precio_proteccion:.4f}</b> (+{float(distancia_sl_porcentaje * 2):.2f}%)\n"
            f"📊 Sistema de protección progresiva activado\n"
            f"✅ Estado: <i>Abierta con éxito</i>"
        )
        enviar_mensaje_telegram(chat_id=chat_id, mensaje=Mensaje_market)
        print(Mensaje_market)

        return True

    except Exception as e:
        print(f"❌ Error al abrir la posición long: {e}")
        return False

def abrir_posicion_short(symbol, monto_operacion, distancia_sl_porcentaje):
    try:
        if get_open_positions_count() >= Numero_de_posiciones:
            mensaje_count = "⚠️ Se alcanzó el máximo de posiciones abiertas. No se abrirá una nueva posición."
            enviar_mensaje_telegram(chat_id=chat_id, mensaje=mensaje_count)
            print(mensaje_count)
            return False

        positions_list = get_current_position(symbol)
        if positions_list and any(Decimal(position['size']) != 0 for position in positions_list):
            print(f"Ya hay una posición abierta en {symbol}. No se abrirá otra posición.")
            return False

        # Calcular cantidad a operar
        base_asset_qty_final = qty_step(symbol, monto_operacion)
        if base_asset_qty_final is None:
            return False

        # Abrir posición a mercado
        response_market_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell",
            orderType="Market",
            qty=str(base_asset_qty_final),
        )

        time.sleep(3)
        if response_market_order['retCode'] != 0:
            print("❌ Error al abrir la posición: La orden de mercado no se completó correctamente.")
            return False

        # Obtener precio de entrada
        positions_list = get_current_position(symbol)
        current_price = Decimal(positions_list[0]['avgPrice'])

        # Calcular y colocar stop loss
        distancia_decimal = distancia_sl_porcentaje / Decimal(100)
        price_sl = adjust_price(symbol, current_price * (Decimal(1) + distancia_decimal))

        stop_loss_order = session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=str(price_sl),
            slTriggerBy="LastPrice",
            tpslMode="Full",
            slOrderType="Market",
        )

        # Calcular precio objetivo para protección 1 a 1
        precio_proteccion = calcular_precio_proteccion_1a1(current_price, distancia_sl_porcentaje, "Sell")

        # Inicializar tracking de la posición
        tracking_posiciones[symbol] = {
            "precio_maximo": current_price,  # Para short, es el precio mínimo
            "precio_entrada": current_price,
            "side": "Sell",
            "distancia_sl": distancia_sl_porcentaje
        }

        Mensaje_market = (
            f"<b>🔴 ¡POSICIÓN SHORT ABIERTA! (2:1)</b>\n"
            f"🔹 Símbolo: <b>{symbol}</b>\n"
            f"💰 Monto operado: <b>{monto_operacion:.2f} USDT</b>\n"
            f"📍 Precio entrada: <b>{current_price}</b>\n"
            f"🛡️ Stop Loss: <b>{price_sl}</b> (+{float(distancia_sl_porcentaje):.2f}%)\n"
            f"🎯 Protección 1:1 en: <b>{precio_proteccion:.4f}</b> (-{float(distancia_sl_porcentaje * 2):.2f}%)\n"
            f"📊 Sistema de protección progresiva activado\n"
            f"✅ Estado: <i>Abierta con éxito</i>"
        )
        enviar_mensaje_telegram(chat_id=chat_id, mensaje=Mensaje_market)
        print(Mensaje_market)

        return True

    except Exception as e:
        print(f"❌ Error al abrir la posición short: {e}")
        return False

# ===== PROTECCIÓN 1 A 1 =====
def colocar_sl_en_entrada(symbol, precio_entrada, side, distancia_sl_porcentaje):
    """Coloca el stop loss en 1:1 (protege ganancia igual al riesgo inicial)"""
    try:
        # Calcular el SL en 1:1 (a la mitad del camino hacia el objetivo 2:1)
        distancia_decimal = distancia_sl_porcentaje / Decimal(100)

        if side == "Buy":
            # Para LONG: SL = entrada + distancia (protege ganancia = riesgo inicial)
            price_sl = adjust_price(symbol, precio_entrada * (Decimal(1) + distancia_decimal))
        else:  # Sell
            # Para SHORT: SL = entrada - distancia (protege ganancia = riesgo inicial)
            price_sl = adjust_price(symbol, precio_entrada * (Decimal(1) - distancia_decimal))

        stop_loss_order = session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=str(price_sl),
            slTriggerBy="LastPrice",
            tpslMode="Full",
            slOrderType="Market",
        )

        ganancia_protegida = float(distancia_sl_porcentaje)
        mensaje = (
            f"<b>🛡️ ¡PROTECCIÓN 1:1 ACTIVADA!</b>\n"
            f"🔹 Símbolo: <b>{symbol}</b>\n"
            f"📍 Stop Loss movido a: <b>{price_sl}</b>\n"
            f"💰 Ganancia protegida: <b>{ganancia_protegida:.2f}%</b>\n"
            f"✅ Ratio 1:1 asegurado"
        )
        enviar_mensaje_telegram(chat_id=chat_id, mensaje=mensaje)
        print(mensaje)

        return True

    except Exception as e:
        print(f"❌ Error al colocar SL en 1:1 para {symbol}: {e}")
        return False


def actualizar_sl_progresivo(symbol, nuevo_precio_sl):
    """Actualiza el stop loss de forma progresiva"""
    try:
        price_sl_adjusted = adjust_price(symbol, nuevo_precio_sl)

        stop_loss_order = session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=str(price_sl_adjusted),
            slTriggerBy="LastPrice",
            tpslMode="Full",
            slOrderType="Market",
        )

        return True

    except Exception as e:
        print(f"❌ Error al actualizar SL progresivo para {symbol}: {e}")
        return False

def monitorear_proteccion_progresiva():
    """
    Monitorea las posiciones para activar la protección progresiva por niveles:
    1. Primera protección (1:1): Cuando el precio avanza 2x el SL inicial
    2. Protecciones siguientes: Cada vez que el precio avanza 2% desde el último máximo,
       mueve el SL dejando un margen de 2%
    """
    while True:
        try:
            posiciones = session.get_positions(category="linear", settleCoin="USDT")
            for posicion in posiciones["result"]["list"]:
                size = Decimal(posicion["size"])
                if size == 0:
                    continue

                symbol = posicion["symbol"]
                side = posicion["side"]
                entry_price = Decimal(posicion["avgPrice"])

                # Verificar si tenemos tracking de esta posición
                if symbol not in tracking_posiciones:
                    # Inicializar tracking si no existe
                    tracking_posiciones[symbol] = {
                        "precio_maximo": entry_price,
                        "precio_entrada": entry_price,
                        "side": side
                    }

                # Obtener precio actual
                tickers = session.get_tickers(symbol=symbol, category="linear")
                last_price = None
                for ticker_data in tickers["result"]["list"]:
                    if ticker_data["symbol"] == symbol:
                        last_price = Decimal(ticker_data["lastPrice"])
                        break

                if last_price is None:
                    continue

                tracking_info = tracking_posiciones[symbol]
                precio_maximo_alcanzado = tracking_info["precio_maximo"]
                precio_entrada = tracking_info["precio_entrada"]
                distancia_sl_porcentaje = tracking_info.get("distancia_sl", Decimal(1.5))  # Default 1.5% si no existe

                # ===== FASE 1: PROTECCIÓN 1:1 (Primera protección) =====
                if symbol not in posiciones_con_stop:
                    # Calcular precio objetivo para 1 a 1
                    precio_objetivo_1a1 = calcular_precio_proteccion_1a1(precio_entrada, distancia_sl_porcentaje, side)

                    # Verificar si se alcanzó el objetivo (2:1)
                    if side == "Buy" and last_price >= precio_objetivo_1a1:
                        print(f"🎯 Precio objetivo 2:1 alcanzado para {symbol}. Activando protección 1:1...")
                        if colocar_sl_en_entrada(symbol, precio_entrada, side, distancia_sl_porcentaje):
                            posiciones_con_stop[symbol] = True
                            tracking_posiciones[symbol]["precio_maximo"] = last_price

                    elif side == "Sell" and last_price <= precio_objetivo_1a1:
                        print(f"🎯 Precio objetivo 2:1 alcanzado para {symbol}. Activando protección 1:1...")
                        if colocar_sl_en_entrada(symbol, precio_entrada, side, distancia_sl_porcentaje):
                            posiciones_con_stop[symbol] = True
                            tracking_posiciones[symbol]["precio_maximo"] = last_price

                # ===== FASE 2: PROTECCIÓN PROGRESIVA (Niveles siguientes) =====
                else:
                    margen_decimal = margen_proteccion_progresiva / Decimal(100)

                    if side == "Buy":
                        # Para LONG: Actualizar máximo si el precio actual es mayor
                        if last_price > precio_maximo_alcanzado:
                            # Calcular el avance desde el último máximo
                            avance_porcentaje = ((last_price - precio_maximo_alcanzado) / precio_maximo_alcanzado) * 100

                            # Si avanzó al menos 2%, actualizar SL
                            if avance_porcentaje >= margen_proteccion_progresiva:
                                # Nuevo SL: precio máximo anterior (dejando 2% de margen)
                                nuevo_sl = precio_maximo_alcanzado

                                if actualizar_sl_progresivo(symbol, nuevo_sl):
                                    print(f"📈 {symbol} - SL progresivo actualizado: {nuevo_sl:.4f}")

                                    # Actualizar el máximo alcanzado
                                    tracking_posiciones[symbol]["precio_maximo"] = last_price

                                    ganancia_acumulada = ((last_price - precio_entrada) / precio_entrada) * 100

                                    mensaje = (
                                        f"<b>🚀 Protección Progresiva Actualizada</b>\n"
                                        f"🔹 {symbol} (LONG)\n"
                                        f"📍 Nuevo SL: <b>{nuevo_sl:.4f}</b>\n"
                                        f"💹 Precio actual: <b>{last_price:.4f}</b>\n"
                                        f"📊 Ganancia protegida: <b>+{ganancia_acumulada:.2f}%</b>\n"
                                        f"🛡️ Margen de seguridad: {margen_proteccion_progresiva}%"
                                    )
                                    enviar_mensaje_telegram(chat_id=chat_id, mensaje=mensaje)

                    elif side == "Sell":
                        # Para SHORT: Actualizar mínimo si el precio actual es menor
                        if last_price < precio_maximo_alcanzado:
                            # Calcular el avance desde el último mínimo (para short)
                            avance_porcentaje = ((precio_maximo_alcanzado - last_price) / precio_maximo_alcanzado) * 100

                            # Si avanzó al menos 2%, actualizar SL
                            if avance_porcentaje >= margen_proteccion_progresiva:
                                # Nuevo SL: precio mínimo anterior (dejando 2% de margen)
                                nuevo_sl = precio_maximo_alcanzado

                                if actualizar_sl_progresivo(symbol, nuevo_sl):
                                    print(f"📉 {symbol} - SL progresivo actualizado: {nuevo_sl:.4f}")

                                    # Actualizar el mínimo alcanzado
                                    tracking_posiciones[symbol]["precio_maximo"] = last_price

                                    ganancia_acumulada = ((precio_entrada - last_price) / precio_entrada) * 100

                                    mensaje = (
                                        f"<b>🚀 Protección Progresiva Actualizada</b>\n"
                                        f"🔹 {symbol} (SHORT)\n"
                                        f"📍 Nuevo SL: <b>{nuevo_sl:.4f}</b>\n"
                                        f"💹 Precio actual: <b>{last_price:.4f}</b>\n"
                                        f"📊 Ganancia protegida: <b>+{ganancia_acumulada:.2f}%</b>\n"
                                        f"🛡️ Margen de seguridad: {margen_proteccion_progresiva}%"
                                    )
                                    enviar_mensaje_telegram(chat_id=chat_id, mensaje=mensaje)

        except Exception as e:
            print(f"❌ Error al monitorear protección progresiva: {e}")

        time.sleep(5)

# ===== COOLDOWN DE MONEDAS =====
def limpiar_cooldown():
    """Limpia las monedas que ya pasaron el periodo de cooldown"""
    while True:
        try:
            tiempo_actual = datetime.now()
            monedas_a_eliminar = []

            for symbol, timestamp in monedas_operadas.items():
                tiempo_transcurrido = (tiempo_actual - timestamp).total_seconds() / 60
                if tiempo_transcurrido >= cooldown_minutos:
                    monedas_a_eliminar.append(symbol)

            for symbol in monedas_a_eliminar:
                del monedas_operadas[symbol]
                print(f"✅ {symbol} eliminado del cooldown. Puede volver a operarse.")

        except Exception as e:
            print(f"❌ Error al limpiar cooldown: {e}")

        time.sleep(60)  # Revisar cada minuto

def verificar_cooldown(symbol):
    """Verifica si una moneda está en cooldown"""
    if symbol in monedas_operadas:
        tiempo_actual = datetime.now()
        tiempo_transcurrido = (tiempo_actual - monedas_operadas[symbol]).total_seconds() / 60
        tiempo_restante = cooldown_minutos - tiempo_transcurrido

        if tiempo_transcurrido < cooldown_minutos:
            print(f"⏳ {symbol} en cooldown. Tiempo restante: {tiempo_restante:.1f} minutos")
            return True

    return False

# ===== NOTIFICACIÓN DE PNL =====
def notificar_pnl_cerrado():
    ultimo_order_id_reportado = None

    while True:
        try:
            response = session.get_closed_pnl(category="linear", limit=1)
            if response["retCode"] == 0 and response["result"]["list"]:
                ultimo_pnl = response["result"]["list"][0]
                order_id = ultimo_pnl["orderId"]

                if ultimo_order_id_reportado is None:
                    ultimo_order_id_reportado = order_id
                elif order_id != ultimo_order_id_reportado:
                    symbol = ultimo_pnl["symbol"]
                    closed_pnl = Decimal(ultimo_pnl["closedPnl"]).quantize(Decimal("0.01"))
                    side = ultimo_pnl["side"]

                    # Limpiar el símbolo de las protecciones y tracking
                    if symbol in posiciones_con_stop:
                        del posiciones_con_stop[symbol]
                    if symbol in tracking_posiciones:
                        del tracking_posiciones[symbol]

                    if closed_pnl >= 0:
                        mensaje = (
                            f"<b>✅ ¡Operación cerrada en ganancia!</b> 🎉💰\n"
                            f"Símbolo: <b>{symbol}</b>\n"
                            f"Lado: <b>{side}</b>\n"
                            f"PNL: <b>+{closed_pnl} USDT</b>"
                        )
                    else:
                        mensaje = (
                            f"<b>❌ Operación cerrada en pérdida</b> 😢💸\n"
                            f"Símbolo: <b>{symbol}</b>\n"
                            f"Lado: <b>{side}</b>\n"
                            f"PNL: <b>{closed_pnl} USDT</b>"
                        )

                    enviar_mensaje_telegram(chat_id=chat_id, mensaje=mensaje)
                    print(f"📊 PNL notificado: {mensaje}")

                    ultimo_order_id_reportado = order_id

        except Exception as e:
            print(f"❌ Error al obtener PNL cerrado: {e}")

        time.sleep(10)

# ===== API FLASK PARA RECIBIR SEÑALES DEL ORÁCULO =====
@app.route('/signal', methods=['POST'])
def recibir_signal():
    try:
        data = request.json
        symbol = data.get('symbol')
        side = data.get('side')  # "long" o "short"
        distancia_sl = data.get('distancia_sl')  # Distancia del SL en % (opcional)

        if not symbol or not side:
            return jsonify({"status": "error", "message": "Faltan parámetros: symbol y side"}), 400

        # Normalizar side
        side = side.lower()
        if side not in ['long', 'short']:
            return jsonify({"status": "error", "message": "side debe ser 'long' o 'short'"}), 400

        # Si no se proporciona distancia_sl, usar un valor por defecto de 1.5%
        if distancia_sl is None:
            distancia_sl = 1.5
            print(f"⚠️ No se proporcionó distancia_sl, usando valor por defecto: 1.5%")

        distancia_sl_oraculo = Decimal(str(distancia_sl))

        # Agregar 0.5% extra a la distancia del SL para darle mas espacio
        distancia_sl_porcentaje = distancia_sl_oraculo + margen_extra_sl

        print(f"\n🔔 Señal recibida del Oráculo: {symbol} - {side.upper()}")
        print(f"📊 SL Oráculo: {float(distancia_sl_oraculo):.2f}% + Margen extra: {float(margen_extra_sl):.2f}% = SL Final: {float(distancia_sl_porcentaje):.2f}%")


        # Validar que la distancia del SL no sea mayor al 10%
        if distancia_sl_porcentaje > Decimal("10.0"):
            mensaje = f"⚠️ Stop Loss de {float(distancia_sl_porcentaje):.2f}% es mayor al 10%. Señal rechazada por alto riesgo."
            print(mensaje)
            return jsonify({"status": "rejected", "message": mensaje}), 200
        # Verificar si el symbol está en Bybit
        if not verificar_symbol_en_bybit(symbol):
            mensaje = f"⚠️ {symbol} no está disponible en Bybit Futuros. Ignorando señal."
            print(mensaje)
            return jsonify({"status": "ignored", "message": mensaje}), 200

        # Verificar cooldown
        if verificar_cooldown(symbol):
            mensaje = f"⏳ {symbol} está en cooldown. Esperando 60 minutos desde la última operación."
            return jsonify({"status": "ignored", "message": mensaje}), 200

        # Calcular monto de operación (ratio 2:1)
        monto_operacion = calcular_monto_operacion(monto_base_usdt, distancia_sl_porcentaje)

        print(f"💰 Monto base: {monto_base_usdt} USDT")
        print(f"📊 Distancia SL Final: {float(distancia_sl_porcentaje):.2f}%")
        print(f"💵 Monto a operar: {monto_operacion:.2f} USDT")

        # Abrir posición según la señal
        exito = False
        if side == 'long':
            exito = abrir_posicion_long(symbol, monto_operacion, distancia_sl_porcentaje)
        elif side == 'short':
            exito = abrir_posicion_short(symbol, monto_operacion, distancia_sl_porcentaje)

        if exito:
            # Agregar a monedas operadas
            monedas_operadas[symbol] = datetime.now()
            return jsonify({"status": "success", "message": f"Posición {side} abierta en {symbol}"}), 200
        else:
            return jsonify({"status": "error", "message": f"No se pudo abrir la posición en {symbol}"}), 500

    except Exception as e:
        print(f"❌ Error al procesar señal: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Endpoint para verificar el estado del bot"""
    try:
        posiciones_abiertas = get_open_positions_count()
        return jsonify({
            "status": "online",
            "posiciones_abiertas": posiciones_abiertas,
            "max_posiciones": Numero_de_posiciones,
            "monedas_en_cooldown": list(monedas_operadas.keys()),
            "monto_base": float(monto_base_usdt),
            "margen_proteccion": float(margen_proteccion_progresiva)
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def iniciar_flask():
    """Inicia el servidor Flask"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ===== MAIN =====
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 BOT 2 A 1 - INICIANDO")
    print("=" * 60)
    print(f"💰 Monto base: {monto_base_usdt} USDT")
    print(f"📊 SL dinámico: El Oráculo envía la distancia (ej: 1.5%, 2%, 3%)")
    print(f"🎯 Ratio: 2:1 (Ganar el doble de lo que arriesgas)")
    print(f"📈 Margen protección progresiva: {margen_proteccion_progresiva}%")
    print(f"🔢 Máximo posiciones simultáneas: {Numero_de_posiciones}")
    print(f"⏳ Cooldown por moneda: {cooldown_minutos} minutos")
    print(f"🌐 API escuchando en: http://0.0.0.0:5000")
    print("=" * 60)

    mensaje_inicio = (
        f"<b>🤖 Bot 2 a 1 Iniciado</b>\n"
        f"💰 Monto base: <b>{monto_base_usdt} USDT</b>\n"
        f"📊 SL: <b>Dinámico (del Oráculo)</b>\n"
        f"🎯 Ratio: <b>2:1</b>\n"
        f"📈 Protección progresiva: <b>{margen_proteccion_progresiva}%</b>\n"
        f"✅ Listo para operar"
    )
    enviar_mensaje_telegram(chat_id=chat_id, mensaje=mensaje_inicio)

    # Iniciar hilos
    flask_thread = threading.Thread(target=iniciar_flask)
    flask_thread.daemon = True
    flask_thread.start()

    monitor_thread = threading.Thread(target=monitorear_proteccion_progresiva)
    monitor_thread.daemon = True
    monitor_thread.start()

    cooldown_thread = threading.Thread(target=limpiar_cooldown)
    cooldown_thread.daemon = True
    cooldown_thread.start()

    pnl_thread = threading.Thread(target=notificar_pnl_cerrado)
    pnl_thread.daemon = True
    pnl_thread.start()

    print("\n✅ Todos los servicios iniciados correctamente")
    print("📡 Esperando señales del Oráculo...\n")

    # Mantener el programa corriendo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⚠️ Bot detenido por el usuario")
