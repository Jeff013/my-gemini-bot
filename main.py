Python
import os
import io
import logging
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_INSTRUCTION = "你係一個精明、友善且幽默嘅 AI 助手，請統一用廣東話口語回覆使用者。"
user_chats = {}

def get_user_chat(chat_id: int):
    if chat_id not in user_chats:
        user_chats[chat_id] = client.chats.create(
            model='gemini-1.5-flash',
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
    return user_chats[chat_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id in user_chats:
        del user_chats[chat_id]
    await update.message.reply_text("你好！我係免費嘅 Gemini AI 助手，請隨便問我問題或者傳圖片畀我！")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text
    chat = get_user_chat(chat_id)
    try:
        response = chat.send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("系統處理時出咗錯，請稍後再試。")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caption = update.message.caption or "請分析呢張圖片。"
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[image, caption],
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Photo Error: {e}")
        await update.message.reply_text("分析圖片時出咗錯。")

def main():
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(tg_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == '__main__':
    main()
