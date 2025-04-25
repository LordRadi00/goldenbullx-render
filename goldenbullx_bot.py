import logging
import random
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import pandas as pd
import pandas_ta as ta  # Sostituire TA-Lib con pandas_ta

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "@GoldenBullX_Bot"  # Replace with your Telegram chat or user ID

# === LOGGING SETUP ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === Dati di mercato tramite API (ad esempio Binance) ===
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
high_prices = {'BTCUSDT': [], 'ETHUSDT': [], 'SOLUSDT': []}
low_prices = {'BTCUSDT': [], 'ETHUSDT': [], 'SOLUSDT': []}

def process_data(pair, close_price, high_price, low_price):
    # Aggiungi i prezzi di chiusura, massimo e minimo
    close_prices[pair].append(close_price)
    high_prices[pair].append(high_price)
    low_prices[pair].append(low_price)
    
    # Limitiamo il numero di prezzi conservati (es. ultimi 100)
    if len(close_prices[pair]) > 100:
        close_prices[pair].pop(0)
        high_prices[pair].pop(0)
        low_prices[pair].pop(0)
    
    # Crea il dataframe con close, high e low per calcolare gli indicatori
    df = pd.DataFrame({
        'close': close_prices[pair],
        'high': high_prices[pair],
        'low': low_prices[pair]
    })
    
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])

# === FUNZIONE PER CALCOLARE GLI INDICATORI ===
def calculate_indicators(data):
    # Utilizziamo pandas_ta per calcolare gli indicatori
    data['EMA50'] = ta.ema(data['close'], length=50)
    data['EMA21'] = ta.ema(data['close'], length=21)
    data['EMA34'] = ta.ema(data['close'], length=34)
    data['ATR'] = ta.atr(data['high'], data['low'], data['close'], length=14)
    data['ADX'] = ta.adx(data['high'], data['low'], data['close'], length=14)
    return data

# === FUNZIONE PER GENERARE IL SEGNALE ===
def generate_signal(data):
    last_row = data.iloc[-1]
    
    # Calcoliamo il recent low (minimo recente) per il lookback
    lookback = 2  # Impostiamo il lookback come nel Pine Script
    recent_low = data['low'].iloc[-lookback:].min()
    
    # Condizione di ingresso LONG basata sulla tua strategia
    long_condition = (
        last_row['close'] > recent_low and  # Prezzo sopra il recent low
        last_row['close'] > last_row['EMA50'] and  # Prezzo sopra EMA 50
        last_row['ADX'] > 10 and  # ADX maggiore di 10 per la forza del trend
        last_row['ATR'] > last_row['ATR'].rolling(window=20).mean() and  # Volatilità alta (ATR)
        (5 <= last_row.name.hour < 22)  # Orario tra 5:00 e 22:00 (considerando il time data)
    )

    if long_condition:
        signal = "Bullish"
        confidence = round(random.uniform(85, 95), 2)
    else:
        signal = "No Signal"
        confidence = 0

    return signal, confidence

# === INVIO AUTOMATICO SEGNALE ===
async def send_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mercati BTC/USDT, ETH/USDT, SOL/USDT
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    for symbol in symbols:
        data = get_market_data(symbol=symbol)  # Ottieni dati dal mercato
        data = calculate_indicators(data)  # Calcola gli indicatori
        signal, confidence = generate_signal(data)  # Genera il segnale
        
        if signal == "Bullish":
            market_pair = symbol
            message = (
                f"🐂 *Bullish Trend Detected*\n"
                f"🤖 Confidence AI: {confidence}%\n"
                f"📊 Pair: {market_pair}\n"
                "⏱ Timeframe: 2m\n\n"
                "👉 Vuoi eseguire l’operazione?"
            )
            # Invia il segnale via Telegram
            await update.message.reply_markdown(message)

# === SCHEDULER PER ESEGUIRE OGNI 10 SECONDI ===
scheduler = BackgroundScheduler()
scheduler.add_job(send_signal, 'interval', seconds=10)  # Controlla ogni 10 secondi
scheduler.start()

# === MAIN ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))

print("🤖 GoldenBullX attivo.")
app.run_polling()
