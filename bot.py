import discord
from discord.ext import commands
import json
import time
import os
import aiohttp             # For high-speed async HTTP requests
import asyncio             # For parallel thread execution
from flask import Flask, request  # For the local whitelist server
import threading                # For running both the bot and server together

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "whitelist.json"
CHANNEL_ID = 1507774505425178735 
ANNOUNCEMENT_CHANNEL_ID = 1480775677505441813 

# 👑 OWNER & DEVELOPER CONFIGURATION (Only this ID can use Admin Commands)
OWNER_ID = 1483917215349735674

# 🔒 File Lock to prevent JSON corruption when multi-users spam commands
file_lock = asyncio.Lock()
# 🌐 Global Session Instance to prevent memory leaks and speed up connections
bot.http_session = None

def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except Exception:
        print("⚠️ [File System] Whitelist JSON was corrupted! Auto-resetting.")
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)
    except Exception as e:
        print(f"❌ [File System] Error saving database: {e}")

# ================= FLASK LOCAL SERVER PART =================
app = Flask('')

@app.route('/api/uidipport', methods=['GET', 'POST'])
@app.route('/api/certificate', methods=['GET', 'POST'])
def handle_requests():
    if 'certificate' in request.path:
        return "true", 200

    data = load_data()
    now = time.time()
    uid = None
    
    uid = request.args.get('uid') or request.form.get('uid')
    if not uid:
        uid = request.args.get('id') or request.args.get('user_id') or request.form.get('id')

    if not uid:
        try:
            input_data = request.get_json(silent=True)
            if input_data: uid = input_data.get('uid') or input_data.get('id')
        except Exception: pass

    if not uid:
        try:
            raw_data = request.data.decode('utf-8').strip()
            if raw_data.isdigit(): uid = raw_data
        except Exception: pass

    if not uid: return "missing_uid", 200

    if uid in data:
        if now < data[uid]: return "active", 200  
        else: return "expired", 200
            
    return "not_whitelisted", 200

def run_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # Suppress spammy server logs to keep console clean
    app.run(host='127.0.0.1', port=5080, debug=False, use_reloader=False)
# =====================================================================

@bot.event
async def on_ready():
    # Initialize global persistent session pool on startup
    bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
    print(f"🔥 NHE Bot Pro v2 is online as {bot.user.name}!")
    print("🌐 Full Bypass Headers & Anti-Spam Running. Status: SECURE 🟢")

# ==================== 🛡️ ANTI-SPAM AUTO DELETE LOGIC ====================
@bot.event
async def on_message(message):
    # বটের নিজের মেসেজ ইগনোর করবে
    if message.author.bot:
        return

    # শুধুমাত্র নির্দিষ্ট হোয়ایتলিস্ট চ্যানেলে ফিল্টার কাজ করবে
    if message.channel.id == CHANNEL_ID:
        valid_commands = ["!free", "!remove", "!info", "!post"]
        content = message.content.strip()
        
        # মেসেজটি ভ্যালিড কমান্ড দিয়ে শুরু হচ্ছে কিনা চেক করা
        is_valid = any(content.startswith(cmd) for cmd in valid_commands)
        
        # যদি ভ্যালিড কমান্ড না হয়, চ্যাট ক্লিন রাখতে ইনস্ট্যান্ট ডিলিট করবে
        if not is_valid:
            try:
                await message.delete()
                warn_msg = await message.channel.send(f"⚠️ {message.author.mention}, **Only working bot commands are allowed here!**")
                await asyncio.sleep(3)
                await warn_msg.delete()
            except Exception as e:
                print(f"❌ [Anti-Spam] Failed to delete message: {e}")
            return

        # 👑 !post এবং !remove কমান্ডের জন্য অনার আইডি ভ্যালিডেশন লক
        if content.startswith("!post") or content.startswith("!remove"):
            if message.author.id != OWNER_ID:
                try:
                    await message.delete()
                    warn_msg = await message.channel.send(f"❌ {message.author.mention}, **You do not have permission to use admin commands!**")
                    await asyncio.sleep(4)
                    await warn_msg.delete()
                except Exception:
                    pass
                return # অনার না হলে কমান্ড রান করা ব্লক করে দেবে

    # মেসেজ এবং পারমিশন ঠিক থাকলে কমান্ড এক্সিকিউট করবে
    await bot.process_commands(message)

# ==================== ADVANCED PARALLEL REQUEST ENGINE ====================
async def post_to_portal(url, data, headers, portal_name):
    """Super-fast, isolated request worker with custom regex-like keyword mapping"""
    if bot.http_session is None or bot.http_session.closed:
        bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        
    try:
        async with bot.http_session.post(url, data=data, headers=headers, timeout=6) as response:
            if response.status == 200:
                res_text = await response.text()
                lowered_res = res_text.lower()
                
                # High accuracy registration checking blocks
                block_keywords = ["already", "exists", "registered", "claimed", "বিদ্যমান", "ইতিমধ্যেই", "নিবন্ধিত"]
                if any(x in lowered_res for x in block_keywords):
                    return portal_name, "Already Claimed ⚠️", False
                else:
                    return portal_name, "Registered 🎉", True
            else:
                return portal_name, f"Bypass Link Error ({response.status}) ❌", False
    except asyncio.TimeoutError:
        return portal_name, "Gateway Timeout 🔌", False
    except Exception:
        return portal_name, "Server Offline ❌", False

# ==================== ADVANCED BULLETPROOF !FREE COMMAND ====================
@bot.command()
async def free(ctx, uid: str):
    # Safe length and character inspection
    if not (uid.isdigit() and 8 <= len(uid) <= 11):
        embed = discord.Embed(title="❌ Access Refused", description="UID formatting is invalid. Must be **8 to 11 pure digits**.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Thread-Safe Database Query Lock
    async with file_lock:
        data = load_data()
    now = time.time()
    
    if uid in data and data[uid] > now:
        embed = discord.Embed(title="⚠️ System Notice", description=f"UID `{uid}` is already active in the cluster database.", color=0xffa500)
        await ctx.send(embed=embed)
        return

    loading_embed = discord.Embed(
        description=f"⏳ Processing UID: `{uid}` across encrypted failover routes...",
        color=discord.Color.blue()
    )
    msg = await ctx.send(embed=loading_embed)

    # Core Cluster Endpoint Configs
    portal1_url = "https://excheatsofficial.xyz/portal/59e63dd8193a762c"
    portal2_url = "https://www.anikxcheatx.com/free/bd45d206"
    portal3_url = "http://92.118.206.166:30022/NAZMUL%20EXE/free_access"

    form_data = {"uid": uid, "hardware_uid": uid}
    
    # 🔥 Anti-Bot 403 Forbidden Bypass Full Headers for Portal 3
    headers_charlie = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
        "Cache-Control": "max-age=0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "http://92.118.206.166:30022",
        "Referer": "http://92.118.206.166:30022/NAZMUL%20EXE/",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive"
    }

    # Blazing-fast concurrent fire (Parallel I/O multiplexing)
    task1 = post_to_portal(portal1_url, form_data, {"Referer": portal1_url}, "Secure Route Alpha 🔒")
    task2 = post_to_portal(portal2_url, form_data, {"Referer": portal2_url}, "Secure Route Bravo 🛡️")
    task3 = post_to_portal(portal3_url, form_data, headers_charlie, "Secure Route Charlie ⚡")

    results = await asyncio.gather(task1, task2, task3)

    status_dict = {}
    any_success = False
    all_already_claimed = True

    for portal_name, status_text, is_success in results:
        status_dict[portal_name] = status_text
        if is_success: any_success = True
        if "Already" not in status_text: all_already_claimed = False

    # 1. Block duplicate attempts globally
    if all_already_claimed:
        embed = discord.Embed(
            title="⚠️ Registration Refused",
            description=f"**User ID:** `{uid}`\n\nThis target machine has already exhausted its trial token on this grid.",
            color=0xffa500
        )
        for name, status in status_dict.items():
            embed.add_field(name=name, value=f"`{status}`", inline=True)
        await msg.edit(embed=embed)
        return

    # 2. Complete breakdown routing error
    if not any_success:
        embed = discord.Embed(
            title="❌ Network Error",
            description=f"**User ID:** `{uid}`\n\nAll external synchronization channels returned fatal server codes.",
            color=0xff0000
        )
        for name, status in status_dict.items():
            embed.add_field(name=name, value=f"`{status}`", inline=True)
        await msg.edit(embed=embed)
        return

    # 3. Dynamic expiry locking logic (Route Bravo grants 3 days, others 1 day)
    expiry_duration = 259200 if status_dict.get("Secure Route Bravo 🛡️") == "Registered 🎉" else 86400
    expiry = now + expiry_duration

    # Thread-Safe Database Write Lock
    async with file_lock:
        data = load_data()
        data[uid] = expiry
        save_data(data)

    # 🔄 Title changed back to your classic favorite
    embed = discord.Embed(title="✅ Access Granted & Whitelisted", color=0x00ff00)
    embed.add_field(name="Target UID", value=f"`{uid}`", inline=True)
    embed.add_field(name="Database Sync", value="Active 🟢", inline=True)
    embed.add_field(name="Token Expiration", value=f"<t:{int(expiry)}:R>", inline=False)
    embed.add_field(name="📡 Distributed Grid Status", value="\n".join([f"**{name}:** `{status}`" for name, status in status_dict.items()]), inline=False)
    
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text="NHE Network Security Core", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await msg.edit(embed=embed)

# =====================================================================

@bot.command()
async def remove(ctx, uid: str):
    if ctx.author.id != OWNER_ID:
        return

    async with file_lock:
        data = load_data()
        if uid in data:
            del data[uid]
            save_data(data)
            embed = discord.Embed(title="🗑️ Authorization Revoked", description=f"UID `{uid}` successfully cleared from main cluster.", color=0xff0000)
        else:
            embed = discord.Embed(title="❌ Entry Non-Existent", description=f"UID `{uid}` could not be located inside active layers.", color=0xff0000)
    await ctx.send(embed=embed)
     
@bot.command()
async def info(ctx):
    async with file_lock:
        data = load_data()
        now = time.time()
        active_uids = {u: e for u, e in data.items() if e > now}
        if len(active_uids) != len(data): save_data(active_uids)
        
    embed = discord.Embed(title="📊 Cluster Diagnostics", color=0x3498db)
    embed.add_field(name="Active Whitelists", value=f"`{len(active_uids)}`", inline=True)
    embed.add_field(name="System Runtime", value="Stable 🟢", inline=True)
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def post(ctx):
    if ctx.author.id != OWNER_ID:
        return

    try: await ctx.message.delete()
    except: pass

    target_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not target_channel: return

    embed = discord.Embed(
        title="🚨 SERVER ISSUE ALERT!", 
        description=(
            "We are currently facing unexpected technical issues with our **NHE UID Whitelist** server.\n\n"
            "**As soon as the server is fixed, we will provide it to everyone for FREE once again! 🎁🚀**\n\n"
            "Sorry for the trouble and thank you for your patience. 🖤"
        ), 
        color=0xff0000 
    )
    embed.set_footer(text="— NHE Team")
    await target_channel.send(content="@everyone", embed=embed)

# Clean thread runtime execution
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

bot.run('')