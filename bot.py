TOKEN = "8661659579:AAHHymnlHlifda9mXfWmw0BkbmyqLJWlk-0"
API_KEY = "K82327231288957"


import requests
import re
import os
import asyncio
import cv2

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)




# =========================
# 📥 استقبال الصورة
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("⏳ جاري التحليل...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    file_path = "image.jpg"
    await file.download_to_drive(file_path)

    # حذف الصورة من الشات
    try:
        await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
    except:
        pass

    # =========================
    # 🔥 معالجة الصورة
    # =========================
    img = cv2.imread(file_path)

    # تكبير الصورة
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # تحسين
    gray = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)[1]

    cv2.imwrite("processed.jpg", gray)

    # =========================
    # 🔍 OCR
    # =========================
    with open("processed.jpg", 'rb') as f:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'file': f},
            data={
                'apikey': API_KEY,
                'isOverlayRequired': True
            }
        )

    result = response.json()

    # استخراج النص
    if "ParsedResults" in result and result["ParsedResults"]:
        text = result["ParsedResults"][0]["ParsedText"]
    else:
        text = ""

    os.remove("processed.jpg")
    os.remove(file_path)

    # =========================
    # 🧠 استخراج الأرقام
    # =========================
    numbers = re.findall(r'\d+', text)

    # فلترة (4 أو 6 أرقام فقط)
    numbers = [n for n in numbers if len(n) in [4, 6]]

    print("NUMBERS:", numbers)

    # =========================
    # 🔥 الربط الصحيح (بدون خطأ)
    # =========================
    found_cards = []

    i = 0
    while i < len(numbers) - 1:
        a = numbers[i]
        b = numbers[i + 1]

        if len(a) == 6 and len(b) == 4:
            found_cards.append(f"{a}:{b}")
            i += 2

        elif len(b) == 6 and len(a) == 4:
            found_cards.append(f"{b}:{a}")
            i += 2

        else:
            i += 1

    print("CARDS:", found_cards)

    # =========================
    # 📩 إرسال النتائج
    # =========================
    if not found_cards:
        await update.message.reply_text("❌ لم يتم التعرف على أي بطاقات")
        return

    for card in found_cards:
        user, password = card.split(":")

        text_msg = f"""
{user}
{password}

"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❤️", callback_data="del")]
        ])

        await update.message.reply_text(
            text_msg.strip(),
            reply_markup=keyboard
        )


# =========================
# ❤️ زر الحذف
# =========================
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    asyncio.create_task(
        delete_later(context, query.message.chat_id, query.message.message_id)
    )


# =========================
# ⏱️ حذف بعد 12 ساعة
# =========================
async def delete_later(context, chat_id, message_id):
    await asyncio.sleep(43200)
#43200
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass


# =========================
# تشغيل البوت
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(CallbackQueryHandler(handle_buttons))

print("🤖 البوت يعمل بشكل صحيح 100%...")
app.run_polling()