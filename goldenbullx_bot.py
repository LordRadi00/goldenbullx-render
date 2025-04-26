import asyncio
from telegram import Bot

TOKEN = "7673882459:AAGQ3X1rZzv8TcjJS8yfiRzlqe0QlTSRg7s"
CHAT_ID = -4655187396  # puoi lasciarlo intero o tra virgolette: "-4655187396"

async def send_test_message():
    await asyncio.sleep(5)
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="✅ TEST: messaggio automatico inviato!")

if __name__ == '__main__':
    asyncio.run(send_test_message())
