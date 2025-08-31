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
user_ids = set()  # مجموعة لحفظ معرفات المستخدمين الفريدة

# ============ تحميل ملفات الإكسل ============
EXCEL_FILES = {
    "2021": "re21.xlsb",
    "2022": "re22.xlsb",
    "2023": "re23.xlsb",
    "2024": "re24.xlsb",
    "2025": "re25.xlsb"
}

# التحقق من وجود الملفات وتحميلها
dataframes = {}
for year, filename in EXCEL_FILES.items():
    try:
        if os.path.exists(filename):
            # استخدام محرك 'pyxlsb' لقراءة ملفات .xlsb
            dataframes[year] = pd.read_excel(filename, engine='pyxlsb')
            log.info(f"تم تحميل ملف {year}: {filename} ({len(dataframes[year])} صف)")
        else:
            log.warning(f"الملف {filename} غير موجود")
    except ImportError:
        log.error("❌ لم يتم تثبيت مكتبة pyxlsb. الرجاء تثبيتها: pip install pyxlsb")
        raise
    except Exception as e:
        log.error(f"خطأ في تحميل ملف {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

log.info(f"تم تحميل {len(dataframes)} ملف نتائج")

# ====== باقي الكود (get_year_from_number, get_columns_for_df, start, handle_text...) ======
# يبقى كما هو في ملفك السابق
