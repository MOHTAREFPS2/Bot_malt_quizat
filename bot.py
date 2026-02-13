import logging
import re
import asyncio
import html
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚠️ ضع التوكن الخاص بك هنا
TOKEN = "8507142363:AAGSBcles2E_MerbjHeMP2lX1SaUIbfrEcM"

# ⚠️ اسم المستخدم المسموح له فقط (بدون @)
ALLOWED_USERNAME = "mohtaref_p"
# ==========================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING  # تقليل الازعاج في التيرمكس
)

ignored_users = set()

async def check_auth(update: Update):
    user = update.effective_user
    if user.username and user.username.lower() == ALLOWED_USERNAME.lower():
        return True
    if user.id in ignored_users:
        return False
    
    rejection_msg = (
        "⛔ <b>عذراً دكتور</b>\n"
        f"المستخدم المصرح له فقط هو @{ALLOWED_USERNAME}"
    )
    await update.message.reply_html(rejection_msg)
    ignored_users.add(user.id)
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    
    welcome_msg = (
        f"👋 <b>أهلاً بك دكتور @{ALLOWED_USERNAME}</b>\n\n"
        f"🤖 <b>نظام إدارة الأسئلة الطبي (MCQ)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>المميزات:</b>\n"
        f"• السؤال بخط عريض (Bold).\n"
        f"• دعم <b>التوضيح (Explanation)</b> عند الحل.\n"
        f"• فصل الخيارات بشكل مريح.\n\n"
        f"💡 <b>لإضافة توضيح:</b> ضع سطر <code>Exp: ...</code> أو <code>توضيح: ...</code> مع السؤال."
    )
    await update.message.reply_html(welcome_msg)

# --- دالة مساعدة: معالجة النص واستخراج التوضيح ---
def parse_quiz_text(text):
    # Regex للجواب
    answer_regex = re.compile(r'(?:Answer|Ans|الإ?جابة(?:.*)?)\s*(?:is|هو)?\s*[:\-]?\s*([A-E])', re.IGNORECASE)
    # Regex للخيارات
    option_line_regex = re.compile(r'^\s*([A-E])\s*[\.\)\-]', re.IGNORECASE)
    # Regex للتوضيح (الجديد)
    explanation_regex = re.compile(r'^(?:Exp|Explanation|توضيح)\s*[:\-]?\s*(.*)', re.IGNORECASE)

    raw_lines = text.split('\n')
    questions_batch = []
    
    current_q_text_lines = []
    current_opts_lines = []
    current_explanation = None # متغير لحفظ التوضيح
    found_options_start = False

    # سنستخدم حلقة while للتحكم الأفضل في قراءة الأسطر
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i].strip()
        i += 1
        
        if not line: continue 

        # 1. هل السطر هو "الجواب"؟
        match_ans = answer_regex.search(line)
        if match_ans:
            ans_char = match_ans.group(1).upper()
            mapping = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}
            
            # --- محاولة قراءة التوضيح في السطر التالي إذا وجد ---
            # ننظر للسطر القادم دون تحريك المؤشر i بشكل دائم إلا إذا كان توضيحاً
            if i < len(raw_lines):
                next_line = raw_lines[i].strip()
                match_exp = explanation_regex.match(next_line)
                if match_exp:
                    current_explanation = match_exp.group(1)
                    i += 1 # تجاوز سطر التوضيح لأننا قرأناه
            
            # حفظ السؤال
            if ans_char in mapping and (current_q_text_lines or current_opts_lines):
                correct_index = mapping[ans_char]
                
                # تحديد الخيارات
                max_option_index = 1 
                for opt_line in current_opts_lines:
                    opt_match = option_line_regex.match(opt_line)
                    if opt_match:
                        found_char = opt_match.group(1).upper()
                        if found_char in mapping and mapping[found_char] > max_option_index:
                            max_option_index = mapping[found_char]
                
                full_options_list = ["A", "B", "C", "D", "E"]
                dynamic_options = full_options_list[:max_option_index+1]

                questions_batch.append({
                    'question_body': "\n".join(current_q_text_lines),
                    'options_text': "\n".join(current_opts_lines),
                    'answer_index': correct_index,
                    'options_list': dynamic_options,
                    'explanation': current_explanation # إضافة التوضيح هنا
                })
            
            # تصفير المتغيرات
            current_q_text_lines = []
            current_opts_lines = []
            current_explanation = None
            found_options_start = False
            continue

        # 2. هل السطر هو "توضيح" (جاء قبل الجواب مثلاً)؟
        match_exp_line = explanation_regex.match(line)
        if match_exp_line:
            current_explanation = match_exp_line.group(1)
            continue

        # 3. هل السطر هو خيار؟
        is_option = option_line_regex.match(line)
        if is_option:
            found_options_start = True
        
        if found_options_start:
            if is_option and current_opts_lines: 
                 current_opts_lines.append("") 
            current_opts_lines.append(line)
        else:
            current_q_text_lines.append(line)
            
    return questions_batch

# --- المعالج الرئيسي ---
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return

    text_content = ""
    if update.message.document:
        doc = update.message.document
        if 'text' in doc.mime_type or doc.file_name.endswith('.txt'):
            status_msg = await update.message.reply_text("📂 جاري التحليل... ⏳")
            file_obj = await doc.get_file()
            byte_array = await file_obj.download_as_bytearray()
            try: text_content = byte_array.decode('utf-8')
            except: text_content = byte_array.decode('cp1256', errors='ignore')
            await status_msg.delete()
        else:
            await update.message.reply_text("❌ أرسل ملف .txt فقط")
            return
    elif update.message.text:
        text_content = update.message.text

    if not text_content: return

    questions = parse_quiz_text(text_content)

    if not questions:
        await update.message.reply_text("⚠️ لم أجد أسئلة. تأكد من التنسيق.")
        return

    await update.message.reply_text(f"✅ تم تجهيز {len(questions)} سؤال مع التوضيحات. 🚀")

    for i, q in enumerate(questions):
        try:
            if q['answer_index'] >= len(q['options_list']):
                full_opts = ["A", "B", "C", "D", "E"]
                q['options_list'] = full_opts[:q['answer_index']+1]

            question_number = i + 1
            
            # تجهيز النصوص
            safe_q_body = html.escape(q['question_body'])
            safe_opts_body = html.escape(q['options_text'])
            final_msg = f"<b>Q{question_number}/ {safe_q_body}</b>\n\n{safe_opts_body}"
            
            # تجهيز التوضيح (مع قص النص إذا كان طويلاً جداً لأن تيليجرام يقبل 200 حرف فقط للتوضيح)
            expl_text = None
            if q['explanation']:
                # تنظيف وقص التوضيح لـ 200 حرف لتجنب الأخطاء
                expl_text = q['explanation'][:200]
            
            await update.message.reply_text(final_msg, parse_mode='HTML')
            
            await update.message.reply_poll(
                question=f"Select Answer for Q{question_number} ⬇️",
                options=q['options_list'],
                type=Poll.QUIZ,
                correct_option_id=q['answer_index'],
                explanation=expl_text, # ✅ هنا يتم إرسال التوضيح
                is_anonymous=False
            )
            
            await asyncio.sleep(1.5) 
            
        except Exception as e:
            await update.message.reply_text(f"خطأ في Q{i+1}: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    app.add_handler(MessageHandler(
        (filters.TEXT & ~filters.COMMAND) | filters.Document.MimeType("text/plain"), 
        handle_input
    ))
    
    print("✅ Bot is running with Explanations...")
    try:
        app.run_polling(poll_interval=1.0)
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
    finally:
        print("\n🛑 Bot Stopped.")

if __name__ == "__main__":
    main()
