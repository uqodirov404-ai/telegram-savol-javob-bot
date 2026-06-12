# 🤖 Telegram Savol-Javob Bot

Telegram guruhda savol-javob sessiyasini kuzatuvchi bot.  
`/boshladik` buyrug'i bilan sessiya boshlanadi, `/yakunladik` buyrug'i bilan yakunlanadi va statistika chiqariladi.

---

## 🛠 O'rnatish

### 1. Bot token olish

1. Telegramda [@BotFather](https://t.me/BotFather) ga kiring
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: `SinifStatBot`)
4. Bot username kiriting (masalan: `sinif_stat_bot`)
5. BotFather sizga token yuboradi — uni saqlab qo'ying

---

### 2. Loyihani tayyorlash

```powershell
# Papkaga kiring
cd C:\Users\hp\.gemini\antigravity\scratch\telegram-savol-javob-bot

# .env fayl yarating
Copy-Item .env.example .env

# .env faylni oching va tokeningizni kiriting
notepad .env
```

`.env` faylida `your_bot_token_here` o'rniga o'z tokeningizni yozing:
```
BOT_TOKEN=1234567890:AABBccDDeeFFggHH...
```

---

### 3. Kutubxonalarni o'rnatish

`uv` (tavsiya etiladi):
```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

yoki oddiy `pip`:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### 4. Botni guruhga qo'shish va admin qilish

1. Telegram guruhingizga botingizni qo'shing (`@your_bot_username`)
2. Guruh sozlamalarida botni **Admin** qiling
3. Admin huquqlaridan kamida **"Xabarlarni o'qish"** bo'lishi kerak

---

### 5. Botni ishga tushirish

```powershell
python bot.py
```

Bot ishlayotganini ko'rsangiz, hammasi tayyor!

---

## 📖 Foydalanish

| Buyruq | Tavsif |
|--------|--------|
| `/boshladik` | Sessiyani boshlaydi (faqat admin) |
| `/yakunladik` | Sessiyani to'xtatadi va statistikani chiqaradi (faqat admin) |
| `/holat` | Joriy sessiya holati — kim nechta xabar yozgan (faqat admin) |

---

## 📊 Statistika namunasi

```
📊 Sessiya Statistikasi
⏱ Davomiyligi: 45 daqiqa

🏆 Eng faol ishtirokchilar:
🥇 @ali_karimov — 12 ta xabar
🥈 @vali_rahimov — 8 ta xabar
🥉 @guli_umarova — 5 ta xabar
4. @soli_nazarov — 3 ta xabar
5. @user123 — 1 ta xabar

👥 Jami ishtirokchilar: 5 nafar
💬 Jami xabarlar: 29 ta
```

---

## ❓ Ko'p so'raladigan savollar

**Bot xabarlarni ko'rmaяpti?**
- Bot guruhda admin bo'lishi kerak
- Guruh "Privacy mode" o'chirilgan bo'lishi kerak (BotFather → Bot Settings → Group Privacy → Turn off)

**Sessiya boshlanmayapti?**
- `/boshladik` buyrug'ini faqat admin yubora oladi

**Token noto'g'ri xatosi?**
- `.env` faylida `BOT_TOKEN=` to'g'ri kiritilganini tekshiring
- Tokendan oldin/keyin bo'sh joy bo'lmasligi kerak

---

## 📁 Fayl tuzilmasi

```
telegram-savol-javob-bot/
├── bot.py           ← Asosiy bot kodi
├── database.py      ← SQLite bilan ishlash
├── config.py        ← Sozlamalar
├── requirements.txt ← Kutubxonalar
├── .env.example     ← Namuna token fayli
├── .env             ← Sizning tokeningiz (git'ga kirmaydi)
└── sessions.db      ← Baza (avtomatik yaratiladi)
```
