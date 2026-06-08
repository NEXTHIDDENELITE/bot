import discord
from discord.ext import commands
import sqlite3
import time
import os
import random
import threading
from flask import Flask, request, Response

# 🌐 Selenium Automation Libraries for Cloud Hosting
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

DB_FILE = "bot_data.db"
CHANNEL_ID = 1507774505425178735 
ANNOUNCEMENT_CHANNEL_ID = 1480775677505441813 

OWNER_ID = 1483917215349735674
VIP_MANAGERS = [1464861365645607027, 1100273442894401616]
ALLOWED_ROLE_IDS = [1480832209995698259, 1480836036916674632]
IS_SERVER_STOPPED = False

TARGET_PORTAL_URL = "http://93.115.101.161:9293/free/1a8e2a51e1054b73d14199fff9486082"

# 📡 প্রক্সি আইপি-র পুল (রেন্ডারে আইপি ব্লক এড়ানোর জন্য তোমার কেনা প্রক্সিগুলো এখানে বসাবে)
PROXY_POOL = [
    # "IP:PORT" ফরম্যাটে এখানে আইপি যোগ করতে পারো
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whitelist (
            uid TEXT PRIMARY KEY,
            discord_id INTEGER,
            expiry REAL
        )
    ''')
    conn.commit()
    conn.close()

# ================= 🤖 CLOUD BROWSER AUTOMATION ENGINE =================
def run_browser_bypass(uid):
    """রেন্ডার ক্লাউড সার্ভারের ব্যাকগ্রাউন্ডে ক্রোম অন করে অটো-ক্লিক ও রিফ্রেশ মেকানিজম"""
    options = Options()
    
    # 🌟 রেন্ডার হোস্টিং সার্ভারে ক্র্যাশ এড়ানোর জন্য এই ৪টি অপশন বাধ্যতামূলক:
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

    if PROXY_POOL:
        selected_proxy = random.choice(PROXY_POOL)
        options.add_argument(f'--proxy-server={selected_proxy}')
        print(f"📡 [Proxy Engine] New Grid IP Session: {selected_proxy}")

    # রেন্ডার সার্ভারে ক্রোমের ড্রাইভ অটো-ডাউনলোড করার ক্লাউড মেথড
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"🌐 [Cloud Browser] Opening Target Portal...")
        driver.get(TARGET_PORTAL_URL)
        time.sleep(3) 

        # ১. UID বক্সে অটো-টাইপ করা
        wait = WebDriverWait(driver, 10)
        uid_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[placeholder*='UID']")))
        uid_field.clear()
        uid_field.send_keys(str(uid))
        print(f"✍️ [Cloud Browser] UID `{uid}` entered successfully.")
        time.sleep(1)

        # ২. নিচের লাল বাটনে অটো-ক্লিক করা
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn, button")
        submit_btn.click()
        print("🎯 [Cloud Browser] Claim/Submit Button Clicked!")
        time.sleep(4) 

        # ৩. সেশন রিফ্রেশ করা (পরবর্তী আইডির জ্যাম ক্লিয়ারিং)
        driver.refresh()
        print("🔄 [Cloud Browser] Browser page refreshed and cleared.")
        time.sleep(1)
        
        return True
    except Exception as e:
        print(f"❌ [Cloud Automation Error]: {e}")
        return False
    finally:
        driver.quit() # ব্যাকগ্রাউন্ড ব্রাউজার বন্ধ করা

# ================= FLASK LOCAL SERVER PART =================
app = Flask('')

@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT uid FROM whitelist WHERE expiry > ?", (time.time(),))
        rows = cursor.fetchall()
        conn.close()
        return Response("\n".join([row[0] for row in rows]), mimetype='text/plain')
    except Exception as e: return f"Database Error: {e}", 500

@app.route('/api/uidipport', methods=['GET', 'POST'])
@app.route('/api/certificate', methods=['GET', 'POST'])
def handle_requests():
    if 'certificate' in request.path: return "true", 200
    uid = request.args.get('uid') or request.form.get('uid')
    if not uid: return "missing_uid", 200

    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT expiry FROM whitelist WHERE uid = ?", (uid,))
    row = cursor.fetchone()
    conn.close()

    if row and time.time() < row[0]: return "active", 200
    return "not_whitelisted", 200

def run_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    # রেন্ডার সার্ভার অটোমেটিক এই পোর্ট ডিটেক্ট করবে
    port = int(os.environ.get("PORT", 5080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
# =====================================================================

@bot.event
async def on_ready():
    print(f"🔥 NHE Bot Pro v2 Online on Render Server Layer!")

def has_allowed_role(member):
    if not hasattr(member, 'roles'): return False
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != CHANNEL_ID: return
    await bot.process_commands(message)

# ==================== ADVANCED !FREE COMMAND ====================
@bot.command()
async def free(ctx, uid: str):
    if IS_SERVER_STOPPED and ctx.author.id != OWNER_ID: return

    if not (uid.isdigit() and 8 <= len(uid) <= 11):
        await ctx.send(embed=discord.Embed(title="❌ Error", description="Invalid UID Format!", color=0xff0000))
        return

    now = time.time()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT expiry FROM whitelist WHERE uid = ?", (uid,))
    row = cursor.fetchone()
    if row and row[0] > now:
        await ctx.send(embed=discord.Embed(title="⚠️ Notice", description="UID Already Active in NHE Database!", color=0xffa500))
        conn.close()
        return
    conn.close()

    loading_embed = discord.Embed(description=f"⏳ Launching Virtual Cloud Browser to bypass and claim UID `{uid}`...", color=discord.Color.blue())
    msg = await ctx.send(embed=loading_embed)

    # 🚀 রেন্ডার সার্ভার ব্যাকগ্রাউন্ডে ব্রাউজার ইঞ্জিন রান করবে
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_browser_bypass, uid)

    # মেয়াদ সেটআপ: ২৩ দিন
    expiry = now + 1987200

    # লোকাল ডাটাবেজে ইউআইডি সফলভাবে সেভ করা
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO whitelist (uid, discord_id, expiry) VALUES (?, ?, ?)", (uid, ctx.author.id, expiry))
    conn.commit()
    conn.close()

    # ডিসকর্ডে সাকসেস মেসেজ পাঠানো
    embed = discord.Embed(title="✅ Access Granted & Whitelisted", color=0x00ff00)
    embed.add_field(name="Target UID", value=f"`{uid}`", inline=True)
    embed.add_field(name="Cloud Grid Session", value="Cleared & Refreshed 🔄", inline=True)
    embed.add_field(name="Token Expiration", value=f"<t:{int(expiry)}:R>", inline=False)
    embed.set_footer(text="🤖 NHE Premium Auto-Clicker Cloud System")
    await msg.edit(embed=embed)

@bot.command()
async def remove(ctx, uid: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM whitelist WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()
    await ctx.send(f"Removed `{uid}`")

init_db()
threading.Thread(target=run_server, daemon=True).start()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN: bot.run(TOKEN)
else: print("❌ ERROR: DISCORD_TOKEN is missing from Environment Variables!")
