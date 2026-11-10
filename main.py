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

# 讀取 Gemini API Key
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

SYSTEM_INSTRUCTION = "你係一個精明、友善且幽默嘅 AI 助手，請統一用廣東話口語回覆使用者。"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("你好！我係免費嘅 Gemini AI 助手，請隨便問我問題或者傳圖片畀我！")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    try:
        if not client:
            raise ValueError("GEMINI_API_KEY 未設定")
        
        # 使用最新 SDK 標準語法調用 gemini-2.5-flash 或 gemini-1.5-flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Error: {e}")
        # 如果 2.5 失敗，嘗試降級備用 1.5-flash
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=user_text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.7,
                )
            )
            await update.message.reply_text(response.text)
        except Exception as e2:
            logging.error(f"Fallback Error: {e2}")
            await update.message.reply_text("系統處理時出咗錯，請檢查 API Key 是否正確。")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caption = update.message.caption or "請分析呢張圖片。"
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, caption],
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Photo Error: {e}")
        await update.message.reply_text("分析圖片時出咗錯。")

async def handle_health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not tg_token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN environment variable")

    bot_app = Application.builder().token(tg_token).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

    app = web.Application()
    app.router.add_get('/', handle_health_check)
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

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
