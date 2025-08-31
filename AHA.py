import os
import logging
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- إعداد اللوج ----------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("results-bot")

# ---------------- التوكن ----------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Secrets")

# ---------------- تحميل ملفات الإكسل ----------------
EXCEL_FILES = {
    "2023": "results_2023.xlsx",
    "2024": "results_2024.xlsx",
    "2025": "results_2025.xlsx"
}

dataframes = {}
for year, filename in EXCEL_FILES.items():
    try:
        if os.path.exists(filename):
            dataframes[year] = pd.read_excel(filename)
            log.info(f"✅ تم تحميل ملف {year}: {filename} ({len(dataframes[year])} صف)")
        else:
            log.warning(f"⚠️ الملف {filename} غير موجود")
    except Exception as e:
        log.error(f"❌ خطأ في تحميل ملف {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

# ---------------- دوال مساعدة ----------------
def get_year_from_number(number: str) -> str:
    """تحديد السنة من أول رقم في رقم الجلوس"""
    if number.startswith("5"):
        return "2025"
    elif number.startswith("4"):
        return "2024"
    elif number.startswith("3"):
        return "2023"
    return None

def find_col(df, candidates):
    """البحث عن عمود من قائمة مرشحين"""
    for col in df.columns:
        for candidate in candidates:
            if candidate.lower() in col.lower():
                return col
    return None

def get_columns_for_df(df):
    """الحصول على أعمدة الرقم والاسم"""
    number_col = find_col(df, ["رقم", "roll", "seat", "id", "number"])
    name_col = find_col(df, ["الاسم", "اسم", "name", "student"])
    if not number_col:
        number_col = df.columns[0]
    if not name_col:
        name_col = df.columns[1]
    return number_col, name_col

def format_row(row: pd.Series, df, year: str) -> str:
    """تنسيق صف النتيجة"""
    number_col, name_col = get_columns_for_df(df)
    parts = []
    parts.append(f"📅 السنة: {year}")
    parts.append(f"👤 الاسم: {row.get(name_col, '-')}")
    parts.append(f"🔢 رقم الجلوس: {row.get(number_col, '-')}")
    for col in df.columns:
        if col not in [name_col, number_col]:
            val = row.get(col, "-")
            if pd.isna(val):
                val = "-"
            parts.append(f"{col}: {val}")
    return "\n".join(parts)

# ---------------- أوامر البوت ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 أهلاً بك في بوت النتائج!\n\n"
        "🔍 ابحث برقم الجلوس مباشرة:\n"
        "• يبدأ بـ 5 → 2025\n"
        "• يبدأ بـ 4 → 2024\n"
        "• يبدأ بـ 3 → 2023\n\n"
        "أرسل الرقم الآن للحصول على النتيجة."
    )
    await update.message.reply_text(msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q:
        await update.message.reply_text("❌ أرسل رقم الجلوس.")
        return

    if q.isdigit():
        year = get_year_from_number(q)
        if not year or year not in dataframes:
            await update.message.reply_text("❌ رقم الجلوس لا يتبع لأي عام متاح.")
            return
        df = dataframes[year]
        number_col, _ = get_columns_for_df(df)
        result = df[df[number_col].astype(str).str.strip() == q]
        if result.empty:
            await update.message.reply_text(f"❌ لم أجد رقم {q} في {year}")
            return
        row = result.iloc[0]
        await update.message.reply_text(format_row(row, df, year))
    else:
        await update.message.reply_text("❌ أدخل رقم جلوس صحيح.")

# ---------------- تشغيل البوت ----------------
def main():
    log.info("🚀 بدء تشغيل البوت...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    log.info("✅ البوت يعمل الآن (Polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
