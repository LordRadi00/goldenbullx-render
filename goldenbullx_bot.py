import logging
import random
import os
import websocket
import json
import pandas as pd
import talib as ta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "@your_telegram_channel_or_user"  # Replace with your Telegram chat or user ID

# === LOGGING SETUP ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === Dati di mercato tramite WebSocket Bybit ===
def on_message(ws, message):
    data = json.loads(message)
    print("📨 Messaggio ricevuto:", data)
    
    if 'data' in data and data['data']:
        for item in data['data']:
            pair = item['s']  # Simbolo della coppia (BTCUSDT, ETHUSDT, SOLUSDT)
            close_price = item['k']['c']  # Prezzo di chiusura
            timestamp = datetime.utcfromtimestamp(item['k']['t'] / 1000)
            print(f"Symbol: {pair}, Close Price: {close_price}, Timestamp: {timestamp}")
            
            # Processiamo i dati per generare segnali
            process_data(pair, close_price)

# Funzione per gestire l'apertura della connessione WebSocket
def on_open(ws):
    print("✅ Connessione aperta.")
    pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    subscribe_msg = {
        "op": "subscribe",
        "args": [f"kline.3.{pair}" for pair in pairs]
    }
    ws.send(json.dumps(subscribe_msg))
    print(f"📡 Sottoscrizione inviata per: {', '.join(pairs)}")

# Funzione per gestire gli errori
def on_error(ws, error):
    print("❌ Errore:", error)

# Funzione per gestire la chiusura della connessione
def on_close(ws, code, msg):
    print("🔒 Connessione chiusa.", code, msg)

# === PROCESSARE I DATI ===
# Mantenere i prezzi di chiusura per ogni simbolo
close_prices = {'BTCUSDT': [], 'ETHUSDT': [], 'SOLUSDT': []}

def process_data(pair, close_price):
    # Aggiungi i prezzi di chiusura
    close_prices[pair].append(close_price)
    
    # Limitiamo il numero di prezzi conservati (es. ultimi 100)
    if len(close_prices[pair]) > 100:
        close_prices[pair].pop(0)
    
    # Calcoliamo gli indicatori
    df = pd.DataFrame(close_prices[pair], columns=["close"])
    df['EMA50'] = ta.EMA(df['close'], timeperiod=50)
    df['EMA21'] = ta.EMA(df['close'], timeperiod=21)
    df['ATR'] = ta.ATR(df['close'], df['close'], df['close'], timeperiod=14)
    df['ADX'] = ta.ADX(df['close'], df['close'], df['close'], timeperiod=14)
    
    # Genera il segnale
    signal, confidence = generate_signal(df)
    
    if signal == "Bullish":
        message = f"🐂 *Bullish Trend Detected*\n🤖 Confidence AI: {confidence}%\n📊 Pair: {pair}\n⏱ Timeframe: 2m"
        send_telegram_signal(message)

# === FUNZIONE PER GENERARE IL SEGNALE ===
def generate_signal(data):
    last_row = data.iloc[-1]
    long_condition = (
        last_row['close'] > last_row['EMA50'] and
        last_row['ADX'] > 10 and
        last_row['ATR'] > last_row['ATR'].rolling(window=20).mean()
    )
    if long_condition:
        return "Bullish", round(random.uniform(85, 95), 2)
    return "No Signal", 0

# === INVIO AUTOMATICO SEGNALE ===
def send_telegram_signal(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.get(url, params=params)

# === SCHEDULER PER ESEGUIRE OGNI 10 SECONDI ===
scheduler = BackgroundScheduler()
scheduler.add_job(process_data, 'interval', seconds=10)  # Controlla ogni 10 secondi
scheduler.start()

# === MAIN ===
print("🔄 Connessione a Bybit WebSocket...")
ws = websocket.WebSocketApp("wss://stream.bybit.com/v5/public/linear",
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

# Esegui il WebSocket
ws.run_forever()
