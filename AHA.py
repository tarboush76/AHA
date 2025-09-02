import os
import logging
import pandas as pd
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============ إعداد اللوج ============
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("results-bot")

# ============ قراءة التوكن ============
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Secrets")

# ============ تتبع المستخدمين ============
user_ids = set()
# ============ تحميل ملفات الإكسل ============
EXCEL_FILES = {
    "2025": "re25.xlsb",
    "2024": "re24.xlsb",
    "2023": "re23.xlsb",
    "2022": "re22.xlsb",
    "2021": "re21.xlsb"
}

dataframes = {}
for year, filename in EXCEL_FILES.items():
    try:
        if os.path.exists(filename):
            dataframes[year] = pd.read_excel(filename, engine="pyxlsb")
            log.info(f"✅ تم تحميل ملف {year}: {filename} ({len(dataframes[year])} صف)")
        else:
            log.warning(f"⚠️ الملف {filename} غير موجود")
    except Exception as e:
        log.error(f"❌ خطأ في تحميل ملف {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

# ============ دوال مساعدة ============
def get_year_from_number(number: str) -> str:
    """تحديد السنة من أول رقم"""
    first_digit = number[0] if number else ""
    if first_digit == "5":
        return "2025"
    elif first_digit == "4":
        return "2024"
    elif first_digit == "3":
        return "2023"
    elif first_digit == "2":
        return "2022"
    elif first_digit == "1":
        return "2021"
    return None

def find_col(df, candidates):
    for col in df.columns:
        for candidate in candidates:
            if candidate.lower() in col.lower():
                return col
    return None

def get_columns_for_df(df):
    NUMBER_COL_CANDIDATES = ["Number", "number", "رقم", "رقم_الجلوس", "roll", "seat", "id", "ID"]
    NAME_COL_CANDIDATES   = ["الاسم", "اسم", "name", "Name", "الطالب"]

    number_col = find_col(df, NUMBER_COL_CANDIDATES)
    name_col = find_col(df, NAME_COL_CANDIDATES)

    if not number_col:
        number_col = df.columns[0]

    if not name_col:
        for col in df.columns[1:]:
            if df[col].dtype == 'object':
                name_col = col
                break
        if not name_col:
            name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

    return number_col, name_col

# تنظيف الأعمدة
for year, df in dataframes.items():
    number_col, _ = get_columns_for_df(df)
    df[number_col] = df[number_col].astype(str).str.strip()
    dataframes[year] = df

def normalize_digits(s: str) -> str:
    if not isinstance(s, str):
        return s
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return s.translate(trans).strip()

def format_row(row: pd.Series, df, year: str) -> str:
    number_col, name_col = get_columns_for_df(df)

    parts = [
        f"📅 السنة: {year}",
        f"👤 الاسم: {row.get(name_col, '-')}",
        f"🔢 رقم الجلوس: {row.get(number_col, '-')}"
    ]

    for col in df.columns:
        if col not in [name_col, number_col]:
            val = row.get(col, "-")
            if pd.isna(val):
                val = "-"
            if isinstance(val, (int, float)) and not pd.isna(val):
                status = "✅" if val >= 50 else "❌"
                parts.append(f"{col}: {val} {status}")
            else:
                parts.append(f"{col}: {val}")

    return "\n".join(parts)

# ============ الأوامر ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files_info = []
    total_count = 0
    for year, df in dataframes.items():
        files_info.append(f"• {year}: {len(df)} نتيجة")
        total_count += len(df)

    msg = (
        "👋 أهلاً بك في بوت النتائج!\n\n"
        "📊 الملفات المتاحة:\n" + "\n".join(files_info) + f"\n"
        f"📈 إجمالي النتائج: {total_count}\n\n"
        "🔍 كيفية البحث:\n"
        "• أرسل رقم الجلوس (يحدد العام من الرقم الأول)\n"
        "• أو أرسل الاسم للبحث في جميع الملفات\n\n"
        "مثال:\n"
        "512345 → نتائج 2025\n"
        "423456 → نتائج 2024\n"
        "٣٢١٠ (بالأرقام العربية) → نتائج 2023"
    )
    await update.message.reply_text(msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = (update.message.text or "").strip()
        if not text:
            await update.message.reply_text("أرسل رقم الجلوس أو الاسم.")
            return

        q = normalize_digits(text)

        if q.isdigit():
            year = get_year_from_number(q)
            if not year or year not in dataframes:
                await update.message.reply_text("❌ الرقم لا يطابق أي سنة معروفة")
                return

            df = dataframes[year]
            number_col, _ = get_columns_for_df(df)
            result = df[df[number_col].astype(str).str.strip() == q]

            if result.empty:
                await update.message.reply_text(f"❌ لم أجد الرقم {q} في ملف {year}")
                return

            row = result.iloc[0]
            await update.message.reply_text(format_row(row, df, year))
            return

        # بحث بالاسم
        all_results = []
        for year, df in dataframes.items():
            _, name_col = get_columns_for_df(df)
            mask = df[name_col].astype(str).str.contains(q, case=False, na=False)
            result = df[mask]
            if not result.empty:
                for _, row in result.iterrows():
                    all_results.append((row, df, year))

        if not all_results:
            await update.message.reply_text(f"❌ لم أجد أي اسم يحتوي على: {q}")
            return

        MAX_ROWS = 3
        if len(all_results) > MAX_ROWS:
            await update.message.reply_text(f"🔎 وُجد {len(all_results)} نتيجة، سأعرض أول {MAX_ROWS}")
            all_results = all_results[:MAX_ROWS]

        for row, df, year in all_results:
            await update.message.reply_text(format_row(row, df, year))

    except Exception as e:
        log.error(f"خطأ في البحث: {e}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء البحث")

# ============ تشغيل البوت ============
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("🚀 بدء تشغيل البوت...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
