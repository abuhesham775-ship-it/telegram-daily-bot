# -*- coding: utf-8 -*-
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import json
import os
from datetime import datetime
import threading

# ======== إعدادات البوت ========
TOKEN = "8688139648:AAHhWUMrES0sn76P-8KXUor0T81Zljm0VHI"  # ضع توكن البوت هنا
STATE_FILE = "state.json"
IMAGE_FOLDER = "images"

# إنشاء مجلد الصور إذا لم يكن موجود
if not os.path.exists(IMAGE_FOLDER):
    os.mkdir(IMAGE_FOLDER)

# تحميل الحالة من الملف أو إنشاء حالة جديدة
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {"last_index": 0, "daily_count": 2, "images": [], "channel_id": None}

# حفظ الحالة
def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ======== أوامر البوت ========
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "مرحبا! هذا بوت إدارة نشر الصور.\n\n"
        "أوامر مفيدة:\n"
        "/stats - حالة النشر\n"
        "/set_daily [عدد] - تعديل عدد الصور اليومية\n"
        "/list - عرض الصور المخزنة\n"
        "/remove [رقم] - حذف صورة\n"
        "/post_now - نشر الصور اليوم مباشرة\n"
        "/set_channel [قناة] - تحديد القناة التي سيتم النشر فيها\n\n"
        "ارسل صورة للبوت ليتم تخزينها."
    )

def stats(update: Update, context: CallbackContext):
    total = len(state["images"])
    posted = state["last_index"]
    remaining = total - posted
    update.message.reply_text(
        f"تم نشر: {posted}\nالمتبقي: {remaining}\nعدد الصور اليومية: {state['daily_count']}"
    )

def set_daily(update: Update, context: CallbackContext):
    try:
        count = int(context.args[0])
        state["daily_count"] = count
        save_state()
        update.message.reply_text(f"تم تعديل عدد الصور اليومية إلى: {count}")
    except:
        update.message.reply_text("استخدام الأمر: /set_daily [عدد]")

def list_images(update: Update, context: CallbackContext):
    msg = ""
    for i, img in enumerate(state["images"], 1):
        status = "✅" if i <= state["last_index"] else "⏳"
        msg += f"{i}. {img} {status}\n"
    update.message.reply_text(msg if msg else "لا توجد صور مخزنة.")

def remove(update: Update, context: CallbackContext):
    try:
        idx = int(context.args[0]) - 1
        removed = state["images"].pop(idx)
        save_state()
        update.message.reply_text(f"تم حذف الصورة: {removed}")
        os.remove(os.path.join(IMAGE_FOLDER, removed))
    except:
        update.message.reply_text("استخدام الأمر: /remove [رقم]")

def receive_photo(update: Update, context: CallbackContext):
    file = update.message.photo[-1].get_file()
    file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    path = os.path.join(IMAGE_FOLDER, file_name)
    file.download(path)
    state["images"].append(file_name)
    save_state()
    update.message.reply_text(f"تم حفظ الصورة: {file_name}")

def set_channel(update: Update, context: CallbackContext):
    channel_id = context.args[0] if context.args else None
    if channel_id and channel_id.startswith('@'):
        state["channel_id"] = channel_id
        save_state()
        update.message.reply_text(f"تم تحديد القناة: {channel_id}")
    else:
        update.message.reply_text("استخدام الأمر: /set_channel [اسم القناة]")

def post_now(update: Update, context: CallbackContext):
    bot = context.bot
    if not state["channel_id"]:
        update.message.reply_text("لم يتم تحديد القناة بعد. استخدم الأمر /set_channel لتحديد القناة.")
        return

    total = len(state["images"])
    posted = state["last_index"]
    daily = state["daily_count"]
    for _ in range(daily):
        if posted >= total:
            update.message.reply_text("لا توجد صور إضافية للنشر اليوم.")
            break
        image_path = os.path.join(IMAGE_FOLDER, state["images"][posted])
        bot.send_photo(state["channel_id"], open(image_path, "rb"))
        posted += 1
        state["last_index"] = posted
        save_state()
    update.message.reply_text(f"تم نشر {state['daily_count']} صور اليوم أو أقل إذا انتهت القائمة.")

# ======== النشر التلقائي يوميًا ========
def schedule_daily_post(bot: Bot):
    while True:
        if not state["channel_id"]:
            threading.Event().wait(10)
            continue

        total = len(state["images"])
        posted = state["last_index"]
        daily = state["daily_count"]
        for _ in range(daily):
            if posted >= total:
                break
            image_path = os.path.join(IMAGE_FOLDER, state["images"][posted])
            bot.send_photo(state["channel_id"], open(image_path, "rb"))
            posted += 1
            state["last_index"] = posted
            save_state()
        # الانتظار 24 ساعة
        threading.Event().wait(24*60*60)

# ======== إعداد البوت ========
updater = Updater(TOKEN)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("stats", stats))
dp.add_handler(CommandHandler("set_daily", set_daily))
dp.add_handler(CommandHandler("list", list_images))
dp.add_handler(CommandHandler("remove", remove))
dp.add_handler(CommandHandler("set_channel", set_channel))
dp.add_handler(CommandHandler("post_now", post_now))
dp.add_handler(MessageHandler(Filters.photo, receive_photo))

# بدء النشر اليومي في Thread منفصل
threading.Thread(target=schedule_daily_post, args=(updater.bot,), daemon=True).start()

updater.start_polling()
updater.idle()
