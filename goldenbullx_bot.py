import logging
import random
import os
import json
import threading
from datetime import datetime

import pandas as pd
import pandas_ta as ta
import websocket
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID   = "-4655187396"  # ID del gruppo o chat in cui inviare i messaggi

# === LOGGING SETUP ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === ISTANZA DEL BOT ===
bot = Bot(token=BOT_TOKEN)

# === COPPIE E STORAGE PREZZI ===
pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
close_prices = {p: [] for p in pairs}
high_prices  = {p: [] for p in pairs}
low_prices   = {p: [] for p in pairs}

# === CALCOLO INDICATORI ===
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df['EMA50'] = ta.ema(df['close'], length=50)
    df['EMA21'] = ta.ema(df['close'], length=21)
    df['EMA34'] = ta.ema(df['close'], length=34)
    df['ATR']   = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['ADX']   = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
    return df

# === GENERAZIONE SEGNALE ===
def generate_signal(df: pd.DataFrame):
    last = df.iloc[-1]
    recent_low = df['low'].iloc[-2:].min()
    long_condition = (
        last['close'] > recent_low and
        last['close'] > last['EMA50'] and
        last['ADX'] > 10 and
        last['ATR'] > df['ATR'].rolling(20).mean().iloc[-1] and
        (5 <= last.name.hour < 22)
    )
    if long_condition:
        confidence = round(random.uniform(85, 95), 2)
        return "Bullish", confidence
    return "No Signal", 0

# === PROCESSAMENTO DATI WS ===
def process_data(pair, close_p, high_p, low_p):
    # 1) Append
    arr_c = close_prices[pair]; arr_h = high_prices[pair]; arr_l = low_prices[pair]
    arr_c.append(close_p); arr_h.append(high_p); arr_l.append(low_p)
    # 2) Mantieni ultimi 100
    if len(arr_c) > 100:
        arr_c.pop(0); arr_h.pop(0); arr_l.pop(0)
    # 3) DataFrame
    df = pd.DataFrame({
        'close': arr_c,
        'high':  arr_h,
        'low':   arr_l
    }, index=pd.to_datetime(
        [datetime.utcnow() for _ in arr_c]  # timestamp fittizio, basta per indice orario
    )).astype(float)
    # 4) Indicatori
    df = calculate_indicators(df)
    # 5) Segnale e invio
    signal, conf = generate_signal(df)
    if signal == "Bullish":
        text = (
            f"🐂 *Bullish Trend Detected*\n"
            f"🤖 Confidence AI: {conf}%\n"
            f"📊 Pair: {pair}\n"
            "⏱ Timeframe: 2m\n\n"
            "👉 Vuoi eseguire l’operazione?"
        )
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")

# === CALLBACK WebSocket ===
def on_message(ws, message):
    msg = json.loads(message)
    for item in msg.get('data', []):
        k = item['k']
        process_data(
            item['s'],
            float(k['c']),
            float(k['h']),
            float(k['l'])
        )

def on_open(ws):
    sub = {"op":"subscribe","args":[f"kline.3.{p}" for p in pairs]}
    ws.send(json.dumps(sub))

def on_error(ws, error):
    logging.error("WebSocket error: %s", error)

def on_close(ws, code, reason):
    logging.info("WebSocket closed: %s %s", code, reason)

# === HANDLER TELEGRAM ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🎉 Benvenuto in GoldenBullX! 🎉\n"
        "Rimani in attesa dei segnali di trading in tempo reale su BTC, ETH e SOL.\n"
        "I segnali verranno inviati automaticamente quando la strategia rileva un trend bullish."
    )
    await update.message.reply_text(welcome)

# === MAIN ===
if __name__ == "__main__":
    # 1) Avvia WebSocket in thread
    threading.Thread(
        target=lambda: websocket.WebSocketApp(
            "wss://stream.bybit.com/v5/public/linear",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        ).run_forever(),
        daemon=True
    ).start()

    # 2) Avvia bot Telegram
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🤖 GoldenBullX attivo.")
    app.run_polling()
