import os
import re
import base64
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= SOZLAMALAR =================
BOT_TOKEN = "9106360642:AAGYHF6FLXlUmXkFGv7vzbfo-i2i5942fLM"
VT_API_KEY = "2f4bcaf0c43efc2349978b8b57298d7acd9a4df7071848b5fe11b2dfd6958804"

# ================= BUYRUQLAR (COMMANDS) =================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bot ishga tushganda yuboriladigan xabar
    message = update.business_message or update.message
    if message:
        await message.reply_text("👋 Assalomu alaykum! Men STYX Security botiman.\n\nMeni Telegram Business orqali shaxsiy profilingizga yoki guruhlarga qo'shing. To'liq yo'riqnoma uchun /help buyrug'ini bosing.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /help bosilganda chiqadigan qo'llanma
    help_text = (
        "🛡 **STYX Security Bot Qo'llanmasi**\n\n"
        "Men shubhali ssilkalar va APK fayllarni STYX Security xavfsizlik bazalari yordamida tekshiraman.\n\n"
        "Mendan qanday foydalanish mumkin?\n"
        "1️⃣ **Shaxsiy chatlarda (Chat Automation):** Telegram sozlamalaridan 'Business' -> 'Chat Automation' bo'limiga kirib, meni profilingizga ulab qo'ying. Men sizga kelgan barcha fayllarni avtomat tekshiraman.\n"
        "2️⃣ **Guruhlarda:** Meni o'z guruhingizga qo'shing. Men fonda ishlab, xavfli ssilkalar fosh etilganda xabar beraman.\n"
        "3️⃣ **To'g'ridan-to'g'ri:** Menga istalgan ssilka yoki APK faylni forward qiling yoki yuboring.\n\n"
        "⚠️ _Eslatma: Telegram qoidalariga ko'ra, 20 MB dan katta fayllarni yuklab ola bilmayman._"
    )
    message = update.business_message or update.message
    if message:
        await message.reply_text(help_text, parse_mode="Markdown")

# ================= ASOSIY TEKSHIRUV QISMI =================
async def check_security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.business_message or update.message
    if not message:
        return

    # ================= 1. APK FAYL TEKSHIRISH =================
    if message.document and message.document.file_name and message.document.file_name.lower().endswith('.apk'):
        if message.document.file_size > 20971520:
            await message.reply_text("⚠️ **Kechirasiz!** Fayl hajmi 20 MB dan katta. Telegram cheklovi tufayli bot buni yuklay olmaydi.", parse_mode="Markdown")
            return
            
        msg = await message.reply_text("📦 APK fayl aniqlandi! Yuklab olinmoqda... ⏳")
        
        try:
            telegram_file = await context.bot.get_file(message.document.file_id)
            file_path = f"{message.document.file_name}"
            await telegram_file.download_to_drive(file_path)
            
            await msg.edit_text("🔄 Fayl STYX Security serveriga yuklanmoqda... ⏳")
            
            url = "https://www.virustotal.com/api/v3/files"
            headers = {"x-apikey": VT_API_KEY}
            with open(file_path, "rb") as f:
                response = requests.post(url, headers=headers, files={"file": (message.document.file_name, f)})
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            if response.status_code == 200:
                analysis_id = response.json()['data']['id']
                await msg.edit_text(
                    f"✅ **Fayl STYX Security tahliliga yuborildi!**\n\n"
                    f"Antiviruslar xulosasini ko'rish uchun havolaga kiring:\n"
                    f"🔗 https://www.virustotal.com/gui/file-analysis/{analysis_id}",
                    disable_web_page_preview=True
                )
            else:
                await msg.edit_text(f"⚠️ STYX Security serveriga yuklashda xato (Kodi: {response.status_code})")
        except Exception as e:
            await msg.edit_text(f"⚠️ Xatolik yuz berdi: {str(e)}")
        return

    # ================= 2. URL (SSILKA) TEKSHIRISH =================
    text = message.text or message.caption or ""
    urls = re.findall(r"http[s]?://[^\s]+", text)
    
    if urls:
        target_url = urls[0]
        if "t.me/" in target_url or "telegram.me/" in target_url:
            return
            
        msg = await message.reply_text("🔍 Ssilka aniqlandi! Xavfsizlik tekshirilmoqda... ⏳")
        
        try:
            url_id = base64.urlsafe_b64encode(target_url.encode()).decode().strip("=")
            headers = {"x-apikey": VT_API_KEY}
            response = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers)
            
            if response.status_code == 200:
                stats = response.json()['data']['attributes']['last_analysis_stats']
                malicious = stats['malicious']
                harmless = stats['harmless']
                undetected = stats['undetected']
                suspicious = stats.get('suspicious', 0)
                
                total = malicious + harmless + undetected + suspicious
                if total > 0:
                    safe_percent = ((total - malicious - suspicious) / total) * 100
                    if malicious == 0 and suspicious == 0:
                        natija = f"✅ **100% Xavfsiz!**\n(Tekshirildi: {total} ta antivirus)"
                    else:
                        natija = f"⚠️ **DIQQAT: XAVFLI!** ({safe_percent:.1f}% xavfsiz)\n{malicious} ta antivirus xavf topdi!"
                    await msg.edit_text(natija)
                else:
                    await msg.edit_text("⚠️ STYX Security bazasida bu ssilka haqida ma'lumot topilmadi (Ssilka hali skaner qilinmagan bo'lishi mumkin).")
            else:
                await msg.edit_text("⚠️ STYX Security serveri bilan bog'lanib bo'lmadi.")
        except Exception as e:
            await msg.edit_text(f"⚠️ Xatolik yuz berdi: {str(e)}")

# ================= DASTURNI ISHGA TUSHIRISH =================
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Buyruqlar uchun maxsus handlerlar
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    
    # Qolgan barcha matn va fayllar uchun
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, check_security))
    
    print("STYX Security boti to'liq ishga tushdi! (Terminalni yopib qo'ymang)")
    app.run_polling()