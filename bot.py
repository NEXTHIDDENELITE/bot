import discord
from discord.ext import commands
import sqlite3
import time
import os
import random
import asyncio
import aiohttp
from flask import Flask, request, Response
import threading

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

# 🌐 স্ক্রিনশটের মেইন পোর্টাল গেটওয়ে ইউআরএল
BASE_PORTAL_URL = "http://93.115.101.161:9293/free/1a8e2a51e1054b73d14199fff9486082"

# 📡 প্রক্সি আইপি-র পুল (আইপি ব্লকিং সম্পূর্ণ বাইপাস করার জন্য তোমার কেনা প্রক্সিগুলো এখানে বসাবে)
# ফরম্যাট: "http://IP:PORT" অথবা "http://username:password@IP:PORT"
PROXY_POOL = [
    # "http://45.77.55.12:8080",
    # "http://185.220.101.5:3128"
]

# ব্রাউজারের ছদ্মবেশ নেওয়ার জন্য র্যান্ডম ইউজার এজেন্ট
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
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

# ================= 📡 HIGH-SPEED PROXY REQUEST ENGINE =================
async def send_uid_request(uid):
    """প্রতিবার নতুন আইপি ও নতুন এজেন্ট দিয়ে লিঙ্কে হিট করে সেশন রিফ্রেশ করার মেকানিজম"""
    # লিঙ্কের শেষে ?uid=আইডি যোগ করা হচ্ছে
    target_url = f"{BASE_PORTAL_URL}?uid={uid}"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "close" # হিট করার সাথে সাথেই যেন কানেকশন রিফ্রেশ/ক্লোজ হয়ে যায়
    }
    
    # প্রক্সি সিলেক্ট করা
    proxy = random.choice(PROXY_POOL) if PROXY_POOL else None
    
    # কুকি ও সেশন জ্যাম ক্লিয়ার রাখার জন্য প্রতিবার ফ্রেশ সেশন ওপেন করা
    async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar()) as session:
        try:
            print(f"🚀 [Request Engine] Target: {target_url} via Proxy: {proxy}")
            async with session.get(target_url, headers=headers, proxy=proxy, timeout=8) as response:
                response_text = await response.text()
                print(f"📡 [Response Received]: {response_text}")
                return True
        except Exception as e:
            print(f"❌ [Request Error]: {e}")
            return False

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
    port = int(os.environ.get("PORT", 5080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
# =====================================================================

@bot.event
async def on_ready():
    print(f"🔥 NHE Bot Pro v2 Online - Screen URL Logic Loaded Stable!")

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

    loading_embed = discord.Embed(description=f"⏳ Routing request through unique proxy grid to bypass UID `{uid}`...", color=discord.Color.blue())
    msg = await ctx.send(embed=loading_embed)

    # 🚀 ব্যাকগ্রাউন্ডে এপিআই লিঙ্কে হিট ও রিফ্রেশ সেশন ফায়ার করা
    await send_uid_request(uid)

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
    embed.add_field(name="Proxy Link Grid", value="Cleaned & Refreshed 🔄", inline=True)
    embed.add_field(name="Token Expiration", value=f"<t:{int(expiry)}:R>", inline=False)
    embed.set_footer(text="🤖 NHE Premium Auto-Route Gate System")
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
else: print("❌ ERROR: DISCORD_TOKEN is missing!")
