# 🤖 Wingo 30 Telegram Bot - Setup Guide

## 📋 Requirements
- Python 3.10+
- Telegram Bot Token
- 4 Telegram Channels (Bot ko Admin banana padega)

---

## ⚙️ Step 1: Bot Token Lo
1. Telegram pe @BotFather kholo
2. `/newbot` send karo
3. Naam aur username do
4. Token copy karo

---

## 📢 Step 2: Channel IDs Nikalo
1. @userinfobot pe apna channel forward karo
2. Ya @RawDataBot use karo
3. Channel ID milega (jaise: -1001234567890)

---

## 🔧 Step 3: bot.py Edit Karo
```python
BOT_TOKEN = "1234567890:ABC..."    # Apna token
BOT_USERNAME = "my_wingo_bot"      # Apna username

ADMIN_IDS = [YOUR_TELEGRAM_ID]     # @userinfobot se apna ID lo

CHANNELS = [
    {"name": "My Channel 1", "username": "mychannel1", "id": -1001234567890},
    {"name": "My Channel 2", "username": "mychannel2", "id": -1001234567891},
    {"name": "My Channel 3", "username": "mychannel3", "id": -1001234567892},
    {"name": "My Channel 4", "username": "mychannel4", "id": -1001234567893},
]
```

---

## 🚀 Step 4: Install & Run
```bash
pip install -r requirements.txt
python bot.py
```

---

## 👑 Admin Commands
- `/broadcast Hello everyone!` → Sabko message bhejo
- `/stats` → Total users dekho

---

## ✅ Important: Bot ko Channel Admin Banao
Har channel mein bot ko Admin add karo with permissions:
- ✅ Add Members (check membership ke liye)

---

## 📱 Bot Features
- 🔒 Force Join - 4+ channels verify
- 🎯 Wingo 30 Prediction (BIG/SMALL)
- 📊 Confidence % with bar graph
- 👑 Admin broadcast & stats
- 💾 SQLite user database
