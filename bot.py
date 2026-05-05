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
    img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    thresh = cv2.dilate(thresh, kernel, iterations=1)

    # =========================
    # 🧠 كشف البطاقات
    # =========================
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cards = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        if 250 < w < 2000 and 100 < h < 1000:
            crop = img[y:y+h, x:x+w]
            cards.append((y, x, crop))

    cards.sort(key=lambda c: (c[0], c[1]))

    print("Detected cards:", len(cards))

    found_cards = []

    # =========================
    # 🔍 تحليل كل بطاقة
    # =========================
    if len(cards) >= 1:

        for i, (_, _, card_img) in enumerate(cards):

            path = f"card_{i}.jpg"
            cv2.imwrite(path, card_img)

            with open(path, 'rb') as f:
                response = requests.post(
                    'https://api.ocr.space/parse/image',
                    files={'file': f},
                    data={'apikey': API_KEY}
                )

            result = response.json()

            try:
                text = result['ParsedResults'][0]['ParsedText']
            except:
                text = ""

            numbers = re.findall(r'\d+', text)

            user = None
            password = None

            for n in numbers:
                if len(n) == 6:
                    user = n
                elif len(n) == 4:
                    password = n

            if user and password:
                found_cards.append(f"{user}:{password}")

            os.remove(path)

    # =========================
    # 🔁 fallback (في حال فشل الكشف)
    # =========================
    if not found_cards:

        print("Fallback mode activated")

        with open(file_path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={'file': f},
                data={'apikey': API_KEY}
            )

        result = response.json()

        try:
            text = result['ParsedResults'][0]['ParsedText']
        except:
            text = ""

        numbers = re.findall(r'\d+', text)
        numbers = [n for n in numbers if len(n) in [4,6]]

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

    os.remove(file_path)

    # =========================
    # 📩 إرسال النتائج
    # =========================
    if not found_cards:
        await update.message.reply_text("❌ لم يتم التعرف على بطاقات")
        return

    for card in set(found_cards):
        user, password = card.split(":")

        text_msg = f"""
━━━━━━━━━━━━━━
👤 USER: {user}
🔒 PASS: {password}
━━━━━━━━━━━━━━
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

print("🤖 يعمل بأقوى نسخة حالياً...")
app.run_polling()
