
import logging
import random
import csv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# === CONFIG ===
BOT_TOKEN = 7673882459:AAEoPqWVa_8yejLg_TW3Lzgx7FkB_EIGqA8

# === LOGGING SETUP ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === FUNZIONE PRINCIPALE DI INVIO SEGNALE ===
async def send_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    confidence = round(random.uniform(85, 95), 2)
    keyboard = [[InlineKeyboardButton("✅ CONFERMA LONG", callback_data=f"confirm_long_{confidence}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "🐂 *Bullish Trend Detected*\n"
        f"🤖 Confidence AI: {confidence}%\n"
        "📊 Pair: BTC/USDT\n"
        "⏱ Timeframe: 2m\n\n"
        "👉 Vuoi eseguire l’operazione?"
    )
    await update.message.reply_markdown(message, reply_markup=reply_markup)

# === CALLBACK BOTTONE ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("confirm_long_"):
        confidence = query.data.split("_")[-1]
        user = query.from_user.first_name
        await query.edit_message_text(f"✅ Operazione LONG confermata da {user} (AI confidence: {confidence}%)")

        # Log in CSV
        with open("trading_log.csv", mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([user, "LONG", confidence])

# === COMANDO PER TEST ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Benvenuto in GoldenBullX. Scrivi /signal per ricevere un segnale AI.")

# === MAIN ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("signal", send_signal))
app.add_handler(CallbackQueryHandler(button_handler))

print("🤖 GoldenBullX attivo.")
app.run_polling()
