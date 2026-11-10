import os
import io
import asyncio
import logging
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types
from aiohttp import web

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

# 簡單的 HTTP 伺服器，讓 Render 的 Web Service 認定 App 正在運行
async def handle_health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not tg_token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN environment variable")

    # 1. 建立 Telegram Bot Application
    bot_app = Application.builder().token(tg_token).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # 2. 啟動 Telegram Bot Polling
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

    # 3. 啟動 aiohttp Web 伺服器滿足 Render 連線需求
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print(f"Web 伺服器與 Bot 成功喺 Port {port} 運行中...")
    
    # 維持異步事件循環運行
    try:
        await asyncio.Event().wait()
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

if __name__ == '__main__':
    asyncio.run(main())

if __name__ == '__main__':
    main()
