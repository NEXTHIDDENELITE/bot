import discord
from discord.ext import commands
import json
import time
import os
import aiohttp              # For high-speed async HTTP requests
import asyncio              # For parallel thread execution
from flask import Flask, request  # For the local whitelist server
import threading                 # For running both the bot and server together
import random                    # For rotating User-Agents
import re                        # For parsing live proxy IPs

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "whitelist.json"
CHANNEL_ID = 1507774505425178735 
ANNOUNCEMENT_CHANNEL_ID = 1480775677505441813 

# 👑 OWNER & DEVELOPER CONFIGURATION (Your ID)
OWNER_ID = 1483917215349735674

# 🔒 File Lock to prevent JSON corruption
file_lock = asyncio.Lock()
bot.http_session = None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
]

# 📝 গ্লোবাল ফুটার টেক্সট
FOOTER_TEXT = "🤖 Commands: !free [UID] | !info | !remove [UID] (Admin)"

def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except Exception:
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)
    except Exception: pass

# ================= 📡 LIVE UNLIMITED PROXY SCRAPER ENGINE =================
async def fetch_live_proxy():
    """পাবলিক API থেকে তাত্ক্ষণিকভাবে একটি সচল প্রক্সি আইপি খুঁজে বের করার ইঞ্জিন"""
    proxy_sources = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
    ]
    
    backup_proxies = [
        "http://43.134.33.129:80", "http://167.71.229.4:8080", 
        "http://20.111.54.16:80", "http://185.195.22.2:80"
    ]
    
    if bot.http_session is None or bot.http_session.closed:
        bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        
    try:
        source_url = random.choice(proxy_sources)
        async with bot.http_session.get(source_url, timeout=5) as response:
            if response.status == 200:
                text = await response.text()
                matches = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+\b', text)
                if matches:
                    selected_proxy = f"http://{random.choice(matches)}"
                    print(f"📡 [Proxy Engine] Rotated to fresh IP: {selected_proxy}")
                    return selected_proxy
    except Exception as e:
        print(f"⚠️ [Proxy Engine] Failed to fetch live proxy: {e}")
        
    return random.choice(backup_proxies)

# ================= FLASK LOCAL SERVER PART =================
app = Flask('')

@app.route('/')
def home():
    return "🔥 NHE Bot Pro v2 is fully operational and alive! 🟢", 200

@app.route('/api/uidipport', methods=['GET', 'POST'])
@app.route('/api/certificate', methods=['GET', 'POST'])
def handle_requests():
    if 'certificate' in request.path:
        return "true", 200

    data = load_data()
    now = time.time()
    uid = request.args.get('uid') or request.form.get('uid') or request.args.get('id') or request.form.get('id')

    if not uid: return "missing_uid", 200

    if uid in data:
        if now < data[uid]: return "active", 200  
        else: return "expired", 200
            
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
    bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
    print(f"🔥 NHE Bot Pro v2 is online as {bot.user.name}!")

# ==================== 🛡️ ANTI-SPAM & OWNER BYPASS LOGIC ====================
@bot.event
async def on_message(message):
    if message.author.bot: return

    if message.channel.id == CHANNEL_ID:
        # 👑 আপনি (Owner) মেসেজ দিলে বট কোনো অ্যাকশন নেবে না, ডিলিটও করবে না
        if message.author.id == OWNER_ID:
            await bot.process_commands(message)
            return

        # 👥 সাধারণ মেম্বারদের জন্য চেক লজিক
        valid_commands = ["!free", "!remove", "!info", "!post"]
        content = message.content.strip()
        is_valid = any(content.startswith(cmd) for cmd in valid_commands)
        
        if not is_valid:
            try:
                await message.delete()
                warn_msg = await message.channel.send(f"⚠️ {message.author.mention}, **Only working bot commands are allowed here!**")
                await asyncio.sleep(3)
                await warn_msg.delete()
            except: pass
            return

        if content.startswith("!post") or content.startswith("!remove"):
            if message.author.id != OWNER_ID:
                try:
                    await message.delete()
                    warn_msg = await message.channel.send(f"❌ {message.author.mention}, **You do not have permission!**")
                    await asyncio.sleep(4)
                    await warn_msg.delete()
                except: pass
                return

    await bot.process_commands(message)

# ==================== ADVANCED PARALLEL REQUEST ENGINE ====================
async def post_to_portal(url, data, headers, portal_name, is_json=False, use_proxy=False):
    if bot.http_session is None or bot.http_session.closed:
        bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        
    try:
        kwargs = {"json": data} if is_json else {"data": data}
        if use_proxy:
            kwargs["proxy"] = await fetch_live_proxy()

        async with bot.http_session.post(url, headers=headers, timeout=10, **kwargs) as response:
            if response.status in [200, 201]:
                res_text = await response.text()
                lowered_res = res_text.lower()
                
                block_keywords = ["already", "exists", "registered", "claimed", "বিদ্যমান", "ইতিমধ্যেই", "নিবন্ধিত"]
                if any(x in lowered_res for x in block_keywords):
                    return portal_name, "Already Claimed ⚠️", False
                else:
                    return portal_name, "Registered 🎉", True
            else:
                return portal_name, f"Bypass Link Error ({response.status}) ❌", False
    except Exception:
        if use_proxy:
            return await post_to_portal(url, data, headers, portal_name, is_json, use_proxy=False)
        return portal_name, "Server Offline ❌", False

# ==================== ADVANCED BULLETPROOF !FREE COMMAND ====================
@bot.command()
async def free(ctx, uid: str):
    if not (uid.isdigit() and 8 <= len(uid) <= 11):
        embed = discord.Embed(title="❌ Access Refused", description="UID formatting is invalid. Must be **8 to 11 pure digits**.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    async with file_lock:
        data = load_data()
    now = time.time()
    
    if uid in data and data[uid] > now:
        embed = discord.Embed(title="⚠️ System Notice", description=f"UID `{uid}` is already active in the cluster database.", color=0xffa500)
        await ctx.send(embed=embed)
        return

    loading_embed = discord.Embed(description=f"⏳ Processing UID: `{uid}` across encrypted failover routes...", color=discord.Color.blue())
    msg = await ctx.send(embed=loading_embed)

    portal1_url = "https://excheatsofficial.xyz/portal/59e63dd8193a762c"
    portal2_url = "https://www.anikxcheatx.com/free/bd45d206"
    portal3_url = "http://92.118.206.166:30022/NAZMUL%20EXE/free_access"

    form_data = {"uid": uid, "hardware_uid": uid}
    
    headers_charlie = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "http://92.118.206.166:30022",
        "Referer": "http://92.118.206.166:30022/NAZMUL%20EXE/",
        "Connection": "keep-alive"
    }

    task1 = post_to_portal(portal1_url, form_data, {"Referer": portal1_url}, "Secure Route Alpha 🔒", is_json=False, use_proxy=False)
    task2 = post_to_portal(portal2_url, form_data, {"Referer": portal2_url}, "Secure Route Bravo 🛡️", is_json=False, use_proxy=False)
    task3 = post_to_portal(portal3_url, form_data, headers_charlie, "Secure Route Charlie ⚡", is_json=True, use_proxy=True)

    results = await asyncio.gather(task1, task2, task3)

    status_dict = {}
    any_success = False
    all_already_claimed = True

    for portal_name, status_text, is_success in results:
        status_dict[portal_name] = status_text
        if is_success: any_success = True
        if "Already" not in status_text: all_already_claimed = False

    if all_already_claimed:
        embed = discord.Embed(title="⚠️ Registration Refused", description=f"**User ID:** `{uid}`\n\nThis target machine has already exhausted its trial token.", color=0xffa500)
        for name, status in status_dict.items():
            embed.add_field(name=name, value=f"`{status}`", inline=True)
        embed.set_footer(text=FOOTER_TEXT, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await msg.edit(embed=embed)
        return

    if not any_success:
        embed = discord.Embed(title="❌ Network Error", description=f"**User ID:** `{uid}`\n\nAll external synchronization channels returned fatal server codes.", color=0xff0000)
        for name, status in status_dict.items():
            embed.add_field(name=name, value=f"`{status}`", inline=True)
        embed.set_footer(text=FOOTER_TEXT, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await msg.edit(embed=embed)
        return

    expiry_duration = 259200 if status_dict.get("Secure Route Bravo 🛡️") == "Registered 🎉" else 86400
    expiry = now + expiry_duration

    async with file_lock:
        data = load_data()
        data[uid] = expiry
        save_data(data)

    embed = discord.Embed(title="✅ Access Granted & Whitelisted", color=0x00ff00)
    embed.add_field(name="Target UID", value=f"`{uid}`", inline=True)
    embed.add_field(name="Database Sync", value="Active 🟢", inline=True)
    embed.add_field(name="Token Expiration", value=f"<t:{int(expiry)}:R>", inline=False)
    embed.add_field(name="📡 Distributed Grid Status", value="\n".join([f"**{name}:** `{status}`" for name, status in status_dict.items()]), inline=False)
    
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text=FOOTER_TEXT, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await msg.edit(embed=embed)

# =====================================================================

@bot.command()
async def remove(ctx, uid: str):
    if ctx.author.id != OWNER_ID: return
    async with file_lock:
        data = load_data()
        if uid in data:
            del data[uid]
            save_data(data)
            embed = discord.Embed(title="🗑️ Authorization Revoked", description=f"UID `{uid}` cleared.", color=0xff0000)
        else:
            embed = discord.Embed(title="❌ Entry Non-Existent", description=f"UID `{uid}` not found.", color=0xff0000)
    embed.set_footer(text=FOOTER_TEXT, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
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
    embed.set_footer(text=FOOTER_TEXT, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=embed)

@bot.command()
async def post(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass
    target_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not target_channel: return

    embed = discord.Embed(
        title="🚨 SERVER ISSUE ALERT!", 
        description="We are facing issues with our whitelist server. Free access will return soon! 🎁🚀", 
        color=0xff0000 
    )
    embed.set_footer(text="— NHE Team")
    await target_channel.send(content="@everyone", embed=embed)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN: bot.run(TOKEN)
