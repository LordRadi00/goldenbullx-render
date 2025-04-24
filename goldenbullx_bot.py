import logging
import random
import csv
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

# === LOGGING SETUP ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === FUNZIONE PRINCIPALE DI INVIO SEGNALE ===
async def send_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Seleziona una pair dinamica basata sul mercato
    market_pair = "BTC/USDT"  # Puoi cambiare questa logica per un mercato dinamico (es. random o da una lista)

    # Aggiungi un segnale di confidenza random per il trend
    confidence = round(random.uniform(85, 95), 2)

    # Crea il pulsante inline per confermare il trade
    keyboard = [[InlineKeyboardButton(f"✅ CONFERMA LONG {market_pair}", callback_data=f"confirm_long_{confidence}_{market_pair}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Costruisci il messaggio con la pair dinamica
    message = (
        "🐂 *Bullish Trend Detected*\n"
        f"🤖 Confidence AI: {confidence}%\n"
        f"📊 Pair: {market_pair}\n"
        "⏱ Timeframe: 2m\n\n"
        "👉 Vuoi eseguire l’operazione?"
    )
    await update.message.reply_markdown(message, reply_markup=reply_markup)

# === CALLBACK BOTTONE ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Estrai la confidenza e la pair dal callback data
    data = query.data.split("_")
    confidence = data[2]  # Confidence
    market_pair = data[3]  # Pair di mercato

    user = query.from_user.first_name
    await query.edit_message_text(f"✅ Operazione LONG confermat! (AI confidence: {confidence}%) per {market_pair}")

    # Log in CSV: registra ogni conferma con dati aggiuntivi
    with open("trading_log.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([user, "LONG", market_pair, confidence])

# === COMANDO PER TEST (Benvenuto motivante) ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Messaggio motivante al primo avvio
    welcome_message = (
        "🎉 Benvenuto in GoldenBullX! 🎉\n"
        "Rimani in attesa per l'arrivo dei primi segnali di trading.\n"
        "Preparati ad agire sui segnali AI in tempo reale!\n\n"
        "👉 Scrivi /signal per ricevere il primo segnale."
    )
    await update.message.reply_text(welcome_message)

# === MAIN ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("signal", send_signal))
app.add_handler(CallbackQueryHandler(button_handler))

print("🤖 GoldenBullX attivo.")
app.run_polling()
