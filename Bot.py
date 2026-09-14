#!/usr/bin/env python3
# Xenon OSINT Bot v4.3 FINAL - Fixed Admin ID + Full Working

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import requests
import json
import sqlite3
import time
import logging
import sys
from datetime import datetime

# ============================================
# LOGGING
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)

# ============================================
# CONFIG
# ============================================
BOT_TOKEN = "8658575917:AAE-Liy4lJnH2cUpsS1Syy7ihPHsU84Puvk"

# ✅ OWNER ID FIXED
ADMIN_IDS = [8989514737]

DB_FILE = "credits.db"
SEARCH_COST = 10
DEFAULT_CREDITS = 50

CHANNEL1 = "@Nakulcyber"
CHANNEL2 = "@Nakulcyber"

# ============================================
# API ENDPOINTS
# ============================================
API_ENDPOINTS = {
    'NUM': 'https://osint.invalidayushh.workers.dev/numv2?key=30d-demo&q=',
    'VEH': 'https://vehicle2.asurpapa.workers.dev/vehicle-info?registration_number=',
}

API_EXAMPLES = {
    'NUM': '9876543210',
    'VEH': 'JH05DE7988',
}

API_NAMES = {
    'NUM': '📱 Number Information',
    'VEH': '🚗 Vehicle Information',
}

BUTTON_CONFIG = {
    "📱 NUMBER INFO": {"stage": "NUM", "name": "Number Info", "prompt": "📱 NUMBER INFO\nSend 10-digit number:", "example": "9876543210"},
    "🚗 VEHICLE INFO": {"stage": "VEH", "name": "Vehicle Info", "prompt": "🚗 VEHICLE INFO\nSend registration number:", "example": "JH05DE7988"},
}

MENU_BUTTONS = [
    "📱 NUMBER INFO", "🚗 VEHICLE INFO", "💳 BALANCE", "➕ REQUEST",
    "📊 STATS", "🆘 HELP", "📢 CHANNELS", "🔙 BACK", "🔙 USER MENU",
    "📊 ADMIN STATS", "👥 USER LIST", "💰 GIVE CREDITS", "📋 TRANSACTIONS",
    "📩 CREDIT REQUESTS", "📢 BROADCAST", "➕ GIVE ALL CREDITS",
    "➖ DEDUCT ALL CREDITS", "🔄 RESET ALL CREDITS"
]

# ============================================
# DATABASE
# ============================================
def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        credits INTEGER DEFAULT 50,
        role TEXT DEFAULT 'user',
        joined_date TEXT DEFAULT CURRENT_TIMESTAMP,
        total_searches INTEGER DEFAULT 0,
        username TEXT,
        first_name TEXT,
        last_name TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, type TEXT, amount INTEGER,
        description TEXT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_user_credits(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        credits = row[0]
    else:
        c.execute("INSERT INTO users (user_id, credits, first_name) VALUES (?, ?, ?)",
                  (user_id, DEFAULT_CREDITS, 'User'))
        conn.commit()
        credits = DEFAULT_CREDITS
    conn.close()
    return credits

def update_credits(user_id, amount, description=""):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    old = row[0] if row else 0
    new = old + amount
    if row:
        c.execute("UPDATE users SET credits=? WHERE user_id=?", (new, user_id))
    else:
        c.execute("INSERT INTO users (user_id, credits) VALUES (?, ?)", (user_id, new))
    c.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (?, ?, ?, ?)",
              (user_id, 'update', amount, description))
    conn.commit()
    conn.close()
    return True, old, new

def deduct_credit(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, credits) VALUES (?, ?)", (user_id, DEFAULT_CREDITS))
        conn.commit()
        conn.close()
        return True, DEFAULT_CREDITS - SEARCH_COST
    credits = row[0]
    if credits < SEARCH_COST:
        conn.close()
        return False, credits
    new = credits - SEARCH_COST
    c.execute("UPDATE users SET credits=?, total_searches=total_searches+1 WHERE user_id=?", (new, user_id))
    c.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (?, ?, ?, ?)",
              (user_id, 'search', -SEARCH_COST, 'Search deduct'))
    conn.commit()
    conn.close()
    return True, new

def is_admin(user_id):
    return int(user_id) in [int(x) for x in ADMIN_IDS]

def get_user_stats(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute("SELECT credits, total_searches, joined_date FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'credits': row[0], 'searches': row[1], 'joined': row[2] or ''}
    return {'credits': get_user_credits(user_id), 'searches': 0, 'joined': datetime.now().isoformat()}

def get_all_users():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute("SELECT user_id, credits, total_searches, username, first_name FROM users ORDER BY credits DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_user_ids():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_transactions(limit=10):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute("SELECT user_id, type, amount, description, timestamp FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def check_user_credits(user_id):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# ============================================
# INIT
# ============================================
init_db()
bot = telebot.TeleBot(BOT_TOKEN)
user_state = {}
pending_credit_requests = {}

# ============================================
# MENUS
# ============================================
def user_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📱 NUMBER INFO"),
        KeyboardButton("🚗 VEHICLE INFO"),
        KeyboardButton("💳 BALANCE"),
        KeyboardButton("➕ REQUEST"),
        KeyboardButton("📊 STATS"),
        KeyboardButton("🆘 HELP"),
        KeyboardButton("📢 CHANNELS")
    )
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📊 ADMIN STATS"), KeyboardButton("👥 USER LIST"),
        KeyboardButton("💰 GIVE CREDITS"), KeyboardButton("📋 TRANSACTIONS"),
        KeyboardButton("📩 CREDIT REQUESTS"), KeyboardButton("📢 BROADCAST"),
        KeyboardButton("➕ GIVE ALL CREDITS"), KeyboardButton("➖ DEDUCT ALL CREDITS"),
        KeyboardButton("🔄 RESET ALL CREDITS"), KeyboardButton("🔙 USER MENU")
    )
    return markup

def back_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton("🔙 BACK"))
    return markup

# ============================================
# FORMAT FUNCTIONS
# ============================================
def format_number_info(data):
    try:
        lines = ["📱 *NUMBER INFORMATION*", "━━━━━━━━━━━━━━━━━━━━━━━"]
        def extract(obj, prefix=""):
            result = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ['ails', 'developer', 'BUY_API', 'SUPPORT', 'buy_api', 'support']:
                        continue
                    if isinstance(v, (dict, list)):
                        result.extend(extract(v, f"{prefix}{k} → "))
                    else:
                        if v and str(v).strip():
                            result.append(f"• *{prefix}{k}*: `{v}`")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    result.extend(extract(item, f"{prefix}[{i}] → "))
            return result
        entries = extract(data)
        if not entries:
            lines.append("❌ No data found")
        else:
            lines.extend(entries[:30])
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Parse error: {e}"

def format_vehicle_info(data):
    try:
        lines = ["🚗 *VEHICLE INFORMATION*", "━━━━━━━━━━━━━━━━━━━━━━━"]
        found = {
            'registration': None, 'model': None, 'owner': None,
            'rto': None, 'challans': None, 'challan_amount': None,
            'challan_details': []
        }
        def deep_search(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    kl = k.lower()
                    if ('registration' in kl or 'reg_number' in kl) and isinstance(v, str) and len(v) >= 8:
                        found['registration'] = v
                    if k == 'title' and isinstance(v, str) and len(v) >= 8 and found['registration'] is None:
                        found['registration'] = v
                    if k == 'subTitle' and isinstance(v, str):
                        if found['model'] is None:
                            found['model'] = v
                    if ('owner' in kl or 'title' in kl) and isinstance(v, str) and '*' in v:
                        found['owner'] = v
                    if kl == 'rto' and isinstance(v, str):
                        found['rto'] = v
                    if 'totalpendingchallanscount' in kl:
                        found['challans'] = v
                    if 'amount' in kl and isinstance(v, (int, float)) and found['challan_amount'] is None:
                        found['challan_amount'] = v
                    if kl == 'offences' and isinstance(v, list):
                        for off in v:
                            if isinstance(off, dict) and 'offenceName' in off:
                                found['challan_details'].append(off['offenceName'])
                    deep_search(v)
            elif isinstance(obj, list):
                for item in obj:
                    deep_search(item)
        deep_search(data)

        if found['registration']:
            lines.append(f"📌 *Number*: `{found['registration']}`")
        if found['model']:
            lines.append(f"🏍️ *Model*: {found['model']}")
        if found['owner']:
            lines.append(f"👤 *Owner*: {found['owner']}")
        if found['rto']:
            lines.append(f"🏢 *RTO*: {found['rto']}")
        if found['challans']:
            lines.append(f"⚠️ *Pending Challans*: {found['challans']}")
        if found['challan_amount']:
            lines.append(f"💰 *Total Amount*: ₹{found['challan_amount']}")
        if found['challan_details']:
            lines.append("\n📋 *Offences*:")
            for off in found['challan_details'][:5]:
                lines.append(f"  • {off}")
        if len(lines) == 2:
            lines.append("⚠️ Limited data received")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Parse error: {e}"

# ============================================
# COMMANDS
# ============================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_state[user_id] = None
    credits = get_user_credits(user_id)
    stats = get_user_stats(user_id)
    welcome = f"""
☠️ *XENON OSINT v4.3*
━━━━━━━━━━━━━━━━━━━━━━━
👤 User: {message.from_user.first_name}
💳 Balance: {credits} credits
🔎 Cost: {SEARCH_COST}/search
📊 Searches: {stats['searches']}
━━━━━━━━━━━━━━━━━━━━━━━
📢 {CHANNEL1}
"""
    if is_admin(user_id):
        bot.send_message(message.chat.id, welcome + "\n👑 *ADMIN MODE*", parse_mode='Markdown', reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, welcome, parse_mode='Markdown', reply_markup=user_menu())

@bot.message_handler(commands=['balance'])
def balance_command(message):
    user_id = message.from_user.id
    user_state[user_id] = None
    credits = get_user_credits(user_id)
    stats = get_user_stats(user_id)
    text = f"💳 *BALANCE*\nCredits: {credits}\nSearches: {stats['searches']}\nCost: {SEARCH_COST}/search"
    if is_admin(user_id):
        bot.reply_to(message, text, parse_mode='Markdown', reply_markup=admin_menu())
    else:
        bot.reply_to(message, text, parse_mode='Markdown', reply_markup=user_menu())

@bot.message_handler(commands=['help'])
def help_command(message):
    user_state[message.from_user.id] = None
    text = f"""
☠️ *XENON OSINT v4.3*
━━━━━━━━━━━━━━━━━━━━━━━
📱 *NUMBER INFO* - 10 digit number
🚗 *VEHICLE INFO* - Registration number
💳 *BALANCE* - Check credits
➕ *REQUEST* - Ask admin for credits
📊 *STATS* - Your usage
━━━━━━━━━━━━━━━━━━━━━━━
Cost: {SEARCH_COST} credits/search
📢 {CHANNEL1}
"""
    if is_admin(message.from_user.id):
        bot.reply_to(message, text, parse_mode='Markdown', reply_markup=admin_menu())
    else:
        bot.reply_to(message, text, parse_mode='Markdown', reply_markup=user_menu())

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    user_state[message.from_user.id] = None
    if is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Cancelled.", reply_markup=admin_menu())
    else:
        bot.reply_to(message, "❌ Cancelled.", reply_markup=user_menu())

# ============================================
# ADMIN - ADDCREDITS (FIXED)
# ============================================
@bot.message_handler(commands=['addcredits'])
def addcredits_command(message):
    user_id = message.from_user.id
    logging.info(f"addcredits called by {user_id} | Admin IDs: {ADMIN_IDS}")
    
    if not is_admin(user_id):
        bot.reply_to(message, f"⛔ ACCESS DENIED.\nYour ID: `{user_id}`\nAdmin IDs: {ADMIN_IDS}", parse_mode='Markdown')
        return
    
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "Usage: `/addcredits <user_id> <amount>`\nExample: `/addcredits 5826371894 500`", parse_mode='Markdown')
        return
    
    try:
        target = int(args[1])
        amount = int(args[2])
        
        if amount <= 0:
            bot.reply_to(message, "❌ Amount must be positive.")
            return
        
        success, old, new = update_credits(target, amount, f"Admin {user_id} added {amount}")
        
        if not success:
            bot.reply_to(message, "❌ Failed to add credits.")
            return
        
        bot.reply_to(message, 
            f"✅ *CREDITS ADDED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: `{target}`\n"
            f"💰 Old: {old}\n"
            f"➕ Added: +{amount}\n"
            f"💳 New: *{new}*",
            parse_mode='Markdown', reply_markup=admin_menu())
        
        try:
            bot.send_message(target, 
                f"🎉 *CREDITS ADDED!*\n"
                f"➕ Admin added: +{amount}\n"
                f"💳 New Balance: *{new}*",
                parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Notification failed: {e}")
            bot.reply_to(message, f"⚠️ Credits added but notification failed: {e}")
        
        if target in pending_credit_requests:
            del pending_credit_requests[target]
            
    except ValueError:
        bot.reply_to(message, "❌ Invalid user_id or amount.")
    except Exception as e:
        logging.error(f"addcredits error: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)[:200]}")

@bot.message_handler(commands=['checkcredits'])
def checkcredits_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, f"⛔ ACCESS DENIED. Your ID: `{message.from_user.id}`", parse_mode='Markdown')
        return
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Usage: `/checkcredits <user_id>`", parse_mode='Markdown')
        return
    try:
        target = int(args[1])
        credits = check_user_credits(target)
        if credits is None:
            bot.reply_to(message, f"❌ User `{target}` not found.")
        else:
            bot.reply_to(message, f"💳 User `{target}`: *{credits}* credits", parse_mode='Markdown', reply_markup=admin_menu())
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# ============================================
# STATE CLEAR HANDLER
# ============================================
@bot.message_handler(func=lambda msg: msg.text in MENU_BUTTONS, content_types=['text'])
def handle_menu_buttons(message):
    user_id = message.from_user.id
    user_state[user_id] = None
    text = message.text
    
    if text in BUTTON_CONFIG:
        handle_lookup_button(message)
    elif text == "💳 BALANCE":
        balance_command(message)
    elif text == "📊 STATS":
        stats_btn(message)
    elif text == "🆘 HELP":
        help_command(message)
    elif text == "📢 CHANNELS":
        channels_btn(message)
    elif text == "➕ REQUEST":
        request_credits(message)
    elif text == "🔙 BACK":
        send_welcome(message)
    elif is_admin(user_id):
        if text == "📊 ADMIN STATS":
            admin_stats(message)
        elif text == "👥 USER LIST":
            user_list_btn(message)
        elif text == "💰 GIVE CREDITS":
            give_credits_panel(message)
        elif text == "📋 TRANSACTIONS":
            transactions_btn(message)
        elif text == "📩 CREDIT REQUESTS":
            credit_requests_panel(message)
        elif text == "📢 BROADCAST":
            broadcast_panel(message)
        elif text == "➕ GIVE ALL CREDITS":
            give_all_credits(message)
        elif text == "➖ DEDUCT ALL CREDITS":
            deduct_all_credits(message)
        elif text == "🔄 RESET ALL CREDITS":
            reset_all_credits(message)
        elif text == "🔙 USER MENU":
            send_welcome(message)

# ============================================
# LOOKUP BUTTON
# ============================================
def handle_lookup_button(message):
    user_id = message.from_user.id
    credits = get_user_credits(user_id)
    config = BUTTON_CONFIG[message.text]
    user_state[user_id] = {'stage': config['stage']}
    prompt = f"""
{config['prompt']}
━━━━━━━━━━━━━━━━━━━━━━━
💳 Balance: {credits} credits
🔍 Cost: {SEARCH_COST} credits
📌 Example: `{config['example']}`
━━━━━━━━━━━━━━━━━━━━━━━
Send /cancel to cancel.
"""
    bot.reply_to(message, prompt, parse_mode='Markdown', reply_markup=back_menu())

# ============================================
# SEARCH
# ============================================
@bot.message_handler(func=lambda msg: user_state.get(msg.from_user.id, {}) 
                     and user_state.get(msg.from_user.id, {}).get('stage') in API_ENDPOINTS
                     and msg.text not in MENU_BUTTONS
                     and not msg.text.startswith('/'))
def generic_lookup(message):
    user_id = message.from_user.id
    stage = user_state.get(user_id, {}).get('stage')
    query = message.text.strip()
    
    if not query:
        bot.reply_to(message, "❌ Send valid input.")
        user_state[user_id] = None
        return
    
    if not is_admin(user_id):
        success, new_credits = deduct_credit(user_id)
        if not success:
            bot.reply_to(message, f"❌ *INSUFFICIENT CREDITS!*\nBalance: {new_credits}\nUse ➕ REQUEST.",
                         parse_mode='Markdown', reply_markup=user_menu())
            user_state[user_id] = None
            return
    
    msg = bot.reply_to(message, f"🔍 Searching `{query}`...", parse_mode='Markdown')
    
    try:
        url = API_ENDPOINTS[stage] + query
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=30)
        
        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except:
            pass
        
        if r.status_code == 200:
            try:
                data = r.json()
                if not data:
                    bot.reply_to(message, f"❌ No data found for `{query}`", parse_mode='Markdown', reply_markup=user_menu())
                else:
                    if stage == 'VEH':
                        output = format_vehicle_info(data)
                    else:
                        output = format_number_info(data)
                    
                    if is_admin(user_id):
                        footer = "\n\n👑 ADMIN (FREE)"
                    else:
                        footer = f"\n\n💳 Remaining: {get_user_credits(user_id)} credits"
                    
                    full = output + footer
                    if len(full) > 4000:
                        for i in range(0, len(full), 4000):
                            chunk = full[i:i+4000]
                            bot.reply_to(message, chunk, parse_mode='Markdown')
                    else:
                        if is_admin(user_id):
                            bot.reply_to(message, full, parse_mode='Markdown', reply_markup=admin_menu())
                        else:
                            bot.reply_to(message, full, parse_mode='Markdown', reply_markup=user_menu())
            except json.JSONDecodeError:
                bot.reply_to(message, "❌ Invalid response from API", reply_markup=user_menu())
        else:
            bot.reply_to(message, f"❌ HTTP {r.status_code} - Try again later.", reply_markup=user_menu())
    except requests.exceptions.Timeout:
        bot.reply_to(message, "⏰ Timeout - Try again.", reply_markup=user_menu())
    except Exception as e:
        logging.error(f"Search error: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)[:200]}", reply_markup=user_menu())
    
    user_state[user_id] = None

# ============================================
# USER FUNCTIONS
# ============================================
def stats_btn(message):
    user_id = message.from_user.id
    stats = get_user_stats(user_id)
    text = f"📊 *YOUR STATS*\n💳 Credits: {stats['credits']}\n🔍 Searches: {stats['searches']}\n📅 Joined: {stats['joined'][:10]}"
    if is_admin(user_id):
        bot.reply_to(message, text, parse_mode='Markdown', reply_markup=admin_menu())
    else:
        bot.reply_to(message, text, parse_mode='Markdown', reply_markup=user_menu())

def channels_btn(message):
    bot.reply_to(message, f"📢 *CHANNELS*\n{CHANNEL1}\n{CHANNEL2}", parse_mode='Markdown', reply_markup=user_menu())

def request_credits(message):
    user_state[message.from_user.id] = {'stage': 'awaiting_amount'}
    bot.reply_to(message, "💳 Enter amount of credits you need (e.g. 50):", reply_markup=back_menu())

@bot.message_handler(func=lambda msg: user_state.get(msg.from_user.id, {}).get('stage') == 'awaiting_amount')
def request_amount(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if text == '/cancel':
        user_state[user_id] = None
        bot.reply_to(message, "❌ Cancelled.", reply_markup=user_menu())
        return
    if not text.isdigit():
        bot.reply_to(message, "❌ Enter a valid number.")
        return
    amount = int(text)
    pending_credit_requests[user_id] = {'amount': amount, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    for admin in ADMIN_IDS:
        try:
            bot.send_message(admin,
                f"📩 *CREDIT REQUEST*\nUser: {message.from_user.first_name}\nID: `{user_id}`\nAmount: {amount}\n\nUse: `/addcredits {user_id} {amount}`",
                parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Request notify failed: {e}")
    bot.reply_to(message, f"✅ Request sent for {amount} credits.", reply_markup=user_menu())
    user_state[user_id] = None

# ============================================
# ADMIN FUNCTIONS
# ============================================
def admin_stats(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(credits), SUM(total_searches) FROM users")
    users, credits, searches = c.fetchone()
    conn.close()
    bot.reply_to(message, f"📊 *ADMIN STATS*\n👥 Users: {users}\n💰 Total Credits: {credits or 0}\n🔍 Searches: {searches or 0}",
                 parse_mode='Markdown', reply_markup=admin_menu())

def user_list_btn(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    users = get_all_users()
    if not users:
        bot.reply_to(message, "No users found.", reply_markup=admin_menu())
        return
    text = "👥 *USER LIST*\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    for u in users[:20]:
        name = u[4] or "Unknown"
        text += f"`{u[0]}` | {name[:15]} | {u[1]} credits\n"
    if len(users) > 20:
        text += f"\n... and {len(users)-20} more"
    bot.reply_to(message, text[:4000], parse_mode='Markdown', reply_markup=admin_menu())

def transactions_btn(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    txns = get_transactions(10)
    if not txns:
        bot.reply_to(message, "No transactions.", reply_markup=admin_menu())
        return
    text = "📋 *RECENT TRANSACTIONS*\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    for t in txns:
        emoji = "➕" if t[2] > 0 else "➖"
        text += f"{emoji} `{t[0]}` | {t[1]} | {t[2]}\n"
    bot.reply_to(message, text[:4000], parse_mode='Markdown', reply_markup=admin_menu())

def give_credits_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    bot.reply_to(message,
        "💰 *GIVE CREDITS*\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Commands:\n"
        "`/addcredits <user_id> <amount>`\n"
        "`/checkcredits <user_id>`\n\n"
        "Example:\n"
        "`/addcredits 5826371894 500`",
        parse_mode='Markdown', reply_markup=admin_menu())

def credit_requests_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    if not pending_credit_requests:
        bot.reply_to(message, "📭 No pending requests.", reply_markup=admin_menu())
        return
    text = "📩 *PENDING REQUESTS*\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid, req in list(pending_credit_requests.items())[-10:]:
        text += f"User: `{uid}` | {req['amount']} credits\nUse: `/addcredits {uid} {req['amount']}`\n\n"
    bot.reply_to(message, text[:4000], parse_mode='Markdown', reply_markup=admin_menu())

def broadcast_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    user_state[message.from_user.id] = {'stage': 'awaiting_broadcast'}
    bot.reply_to(message, "📢 Send message to broadcast to ALL users.\n/cancel to cancel.", reply_markup=back_menu())

@bot.message_handler(func=lambda msg: user_state.get(msg.from_user.id, {}).get('stage') == 'awaiting_broadcast')
def process_broadcast(message):
    if not is_admin(message.from_user.id):
        return
    text = message.text
    if text == '/cancel':
        user_state[message.from_user.id] = None
        bot.reply_to(message, "❌ Cancelled.", reply_markup=admin_menu())
        return
    users = get_all_user_ids()
    sent = 0; failed = 0
    for uid in users:
        try:
            bot.send_message(uid, f"📢 *ANNOUNCEMENT*\n\n{text}\n\n{CHANNEL1}", parse_mode='Markdown')
            sent += 1
        except:
            failed += 1
    bot.reply_to(message, f"✅ Broadcast sent: {sent} | Failed: {failed}", reply_markup=admin_menu())
    user_state[message.from_user.id] = None

def give_all_credits(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    user_state[message.from_user.id] = {'stage': 'awaiting_giveall'}
    bot.reply_to(message, "➕ Enter amount to GIVE to ALL users:", reply_markup=back_menu())

def deduct_all_credits(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    user_state[message.from_user.id] = {'stage': 'awaiting_deductall'}
    bot.reply_to(message, "➖ Enter amount to DEDUCT from ALL users:", reply_markup=back_menu())

def reset_all_credits(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ACCESS DENIED.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = ?", (DEFAULT_CREDITS,))
    count = c.rowcount
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Reset all {count} users to {DEFAULT_CREDITS} credits.", reply_markup=admin_menu())

@bot.message_handler(func=lambda msg: user_state.get(msg.from_user.id, {}).get('stage') in ['awaiting_giveall', 'awaiting_deductall'])
def process_all_credits(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    stage = user_state[user_id]['stage']
    text = message.text.strip()
    if text == '/cancel':
        user_state[user_id] = None
        bot.reply_to(message, "❌ Cancelled.", reply_markup=admin_menu())
        return
    if not text.isdigit():
        bot.reply_to(message, "❌ Enter a valid number.")
        return
    amount = int(text)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if stage == 'awaiting_giveall':
        c.execute("UPDATE users SET credits = credits + ?", (amount,))
        msg = f"✅ Gave {amount} credits to ALL users."
    else:
        c.execute("UPDATE users SET credits = credits - ?", (amount,))
        msg = f"✅ Deducted {amount} credits from ALL users."
    count = c.rowcount
    conn.commit()
    conn.close()
    bot.reply_to(message, f"{msg}\nUsers affected: {count}", reply_markup=admin_menu())
    user_state[user_id] = None

# ============================================
# FALLBACK
# ============================================
@bot.message_handler(func=lambda msg: True)
def fallback(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        bot.reply_to(message, "⚠️ Use buttons from admin menu.", reply_markup=admin_menu())
    else:
        bot.reply_to(message, "⚠️ Use buttons from menu.", reply_markup=user_menu())

# ============================================
# MAIN LOOP (AUTO-RESTART)
# ============================================
if __name__ == "__main__":
    print("="*50)
    print(" ☠️ XENON OSINT BOT v4.3 STARTED ☠️")
    print(f" Bot: {BOT_TOKEN[:15]}...")
    print(f" Admin ID: {ADMIN_IDS}")
    print("="*50)
    
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=10, long_polling_timeout=5, none_stop=True)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            print(f"⚠️ Error: {e}")
            print("🔄 Restarting in 5 seconds...")
            time.sleep(5)
