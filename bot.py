import logging
import re
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚠️ ضع التوكن الجديد هنا بين علامتي التنصيص
TOKEN = "8449444158:AAF99gwf9ZjJqvSDy-8q252Ctefp4KXZgb0"
# ==========================================

# إعدادات السجل (Logging) للمتابعة
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. دالة البدء (زر Start)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"مرحباً <b>{user.first_name}</b> 👋\n\n"
        f"<b>كل شيء جاهز للبدء🔥💪</b>\n"
        f"أنا جاهز لتحويل أسئلتك الدراسية إلى تنسيق (نص + اختبار).\n\n"
        f"اضغط على /help لمعرفة كيفية كتابة السؤال."
    )

# 2. دالة التعليمات (زر Help)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 <b>تعليمات الاستخدام:</b>\n\n"
        "أرسل السؤال والخيارات في رسالة واحدة، وفي النهاية حدد الجواب.\n\n"
        "<b>صيغ الجواب المقبولة:</b>\n"
        "• Answer: A\n"
        "• Answer is A\n"
        "• Answer is : A\n"
        "• الجواب: A\n\n"
        "<b>مثال (انسخ وأرسل للتجربة):</b>\n"
        "The heart is located in:\n"
        "A. Head\n"
        "B. Chest\n"
        "C. Leg\n"
        "D. Hand\n"
        "Answer: B"
    )
    await update.message.reply_html(help_text)

# 3. المعالجة الذكية للنص
async def handle_quiz_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return

    lines = text.split('\n')
    correct_option_index = -1
    clean_lines = []
    
    # تحسين التعبير النمطي (Regex) ليلتقط كل الصيغ
    # يلتقط: Answer, Ans, الجواب | بعدها مسافات | بعدها is, هو (اختياري) | بعدها : أو - (اختياري) | بعدها A-D
    answer_pattern = re.compile(r'(?:Answer|Ans|الجواب)\s*(?:is|هو)?\s*[:\-]?\s*([A-D])', re.IGNORECASE)

    for line in lines:
        match = answer_pattern.search(line)
        if match:
            # استخراج حرف الجواب وتحويله لرقم
            ans_char = match.group(1).upper()
            mapping = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            if ans_char in mapping:
                correct_option_index = mapping[ans_char]
            continue # لا ننسخ سطر الجواب للنص النهائي
        
        clean_lines.append(line)

    # التحقق من العثور على جواب
    if correct_option_index == -1:
        await update.message.reply_text(
            "⚠️ لم أستطع تحديد الجواب.\n"
            "تأكد من كتابة سطر مثل: <b>Answer: A</b> في نهاية الرسالة.",
            parse_mode='HTML'
        )
        return

    # إرسال الرسالة النصية (المفتاح)
    question_text = "\n".join(clean_lines).strip()
    await update.message.reply_text(f"Q/ {question_text}")

    # إرسال الاستفتاء (Quiz)
    try:
        await update.message.reply_poll(
            question="Select the correct option 👇",
            options=["A", "B", "C", "D"],
            type=Poll.QUIZ,
            correct_option_id=correct_option_index,
            is_anonymous=False
        )
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ تقني: {e}")

# الدالة الرئيسية للتشغيل
def main():
    app = Application.builder().token(TOKEN).build()

    # ربط الأوامر بالدوال
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # استقبال النصوص العادية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_creation))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
