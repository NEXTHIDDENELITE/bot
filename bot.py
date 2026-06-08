import discord
from discord.ext import commands
import sqlite3
import time
import os
import aiohttp              # For high-speed async HTTP requests
import asyncio              # For parallel thread execution
from flask import Flask, request, Response  # For the local whitelist server
import threading             # For running both the bot and server together
import random                # For rotating User-Agents to mimic human traffic

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

DB_FILE = "bot_data.db"
CHANNEL_ID = 1507774505425178735 
ANNOUNCEMENT_CHANNEL_ID = 1480775677505441813 

# 👑 OWNER & DEVELOPER CONFIGURATION
OWNER_ID = 1483917215349735674

# 🌟 VIP MANAGERS CONFIGURATION
VIP_MANAGERS = [1464861365645607027, 1100273442894401616]

# 🏷️ ALLOWED ROLE IDS DURING STOP MODE
ALLOWED_ROLE_IDS = [1480832209995698259, 1480836036916674632]

# 🔒 Global Server Stop Status Tracker
IS_SERVER_STOPPED = False

# 🌐 Global Session Instance
bot.http_session = None

# 🌐 তোমার দেওয়া একদম নিখুঁত মেইন ড্যাশবোর্ড টোকেন লিংক
PORTAL_URLS = {
    "NHE Portal Grid ⚡": "http://93.115.101.161:9293/free/1a8e2a51e1054b73d14199fff9486082"
}

# পোর্টালের সিকিউরিটি বাইপাস করার জন্য র্যান্ডম ইউজার এজেন্ট লিস্ট
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
]

# ================= 🗄️ SQLITE DATABASE INITIALIZATION =================
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
        
        uid_list = [row[0] for row in rows]
        return Response("\n".join(uid_list), mimetype='text/plain')
    except Exception as e:
        return f"Database Error: {e}", 500

@app.route('/api/uidipport', methods=['GET', 'POST'])
@app.route('/api/certificate', methods=['GET', 'POST'])
def handle_requests():
    if 'certificate' in request.path:
        return "true", 200

    now = time.time()
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

    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT expiry FROM whitelist WHERE uid = ?", (uid,))
    row = cursor.fetchone()
    conn.close()

    if row:
        expiry = row[0]
        if now < expiry: return "active", 200  
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
    print("🌐 Direct Token URL Grid Connected Successfully 🟢")

def has_allowed_role(member):
    if not hasattr(member, 'roles'): return False
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

# ==================== 🛡️ ANTI-SPAM & CHANNEL LOCK LOGIC ====================
@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.channel.id != CHANNEL_ID: return

    is_privileged = (message.author.id == OWNER_ID or 
                     message.author.id in VIP_MANAGERS or 
                     has_allowed_role(message.author))

    valid_commands = ["!free", "!remove", "!info", "!post", "!vip", "!stop", "!on", "!allremove", "!url"]
    content = message.content.strip()
    is_valid_command = any(content.startswith(cmd) for cmd in valid_commands)

    owner_only_commands = ["!info", "!post", "!vip", "!stop", "!on", "!allremove", "!url"]
    is_owner_command = any(content.startswith(cmd) for cmd in owner_only_commands)

    if is_owner_command and message.author.id != OWNER_ID:
        try:
            await message.delete()
            warn_msg = await message.channel.send(f"❌ {message.author.mention}, **Only the Bot Owner can use this command!**")
            await asyncio.sleep(4)
            await warn_msg.delete()
        except Exception: pass
        return

    if IS_SERVER_STOPPED:
        if is_privileged:
            async def delete_user_msg(msg):
                await asyncio.sleep(5)
                try: await msg.delete()
                except: pass
            bot.loop.create_task(delete_user_msg(message))
            await bot.process_commands(message)
        else:
            try: await message.delete()
            except: pass
        return
    else:
        if not is_valid_command:
            try:
                await message.delete()
                warn_msg = await message.channel.send(f"⚠️ {message.author.mention}, **Only working bot commands are allowed here!**")
                await asyncio.sleep(3)
                await warn_msg.delete()
            except Exception as e:
                print(f"❌ [Anti-Spam] Failed to delete non-command message: {e}")
            return
        await bot.process_commands(message)

# ==================== ADVANCED PARALLEL REQUEST ENGINE ====================
async def post_to_portal(url, data, headers, portal_name):
    if bot.http_session is None or bot.http_session.closed:
        bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        
    try:
        headers["User-Agent"] = random.choice(USER_AGENTS)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        # সরাসরি মেইন ইউআরএল লিংকে ফর্ম সাবমিট করা হচ্ছে
        async with bot.http_session.post(url, headers=headers, data=data, timeout=8) as response:
            res_text = await response.text()
            lowered_res = res_text.lower()
            
            if response.status in [200, 201]:
                block_keywords = ["already", "exists", "registered", "claimed", "বিদ্যমান", "ইতিমধ্যেই", "নিবন্ধিত", "success: false", "failed"]
                if any(x in lowered_res for x in block_keywords):
                    return portal_name, "Already Claimed ⚠️", False
                else:
                    return portal_name, "Registered 🎉", True
            else:
                if "already" in lowered_res or "exist" in lowered_res:
                    return portal_name, "Already Claimed ⚠️", False
                return portal_name, f"Bypass Error ({response.status}) ❌", False
    except asyncio.TimeoutError:
        return portal_name, "Gateway Timeout 🔌", False
    except Exception:
        return portal_name, "Server Offline ❌", False

# ==================== ADVANCED BULLETPROOF !FREE COMMAND ====================
@bot.command()
async def free(ctx, uid: str):
    global IS_SERVER_STOPPED
    is_privileged = (ctx.author.id == OWNER_ID or ctx.author.id in VIP_MANAGERS or has_allowed_role(ctx.author))

    if IS_SERVER_STOPPED and not is_privileged: return

    if not (uid.isdigit() and 8 <= len(uid) <= 11):
        embed = discord.Embed(title="❌ Access Refused", description="UID formatting is invalid. Must be **8 to 11 pure digits**.", color=0xff0000)
        msg = await ctx.send(embed=embed)
        if IS_SERVER_STOPPED:  
            await asyncio.sleep(5)
            try: await msg.delete()
            except: pass
        return

    now = time.time()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()

    # ১ ডিভাইস লিমিট চেক
    if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS:
        cursor.execute("SELECT uid, expiry FROM whitelist WHERE discord_id = ?", (ctx.author.id,))
        existing = cursor.fetchone()
        if existing:
            existing_uid, expiry = existing
            if expiry > now:
                if existing_uid == uid:
                    embed = discord.Embed(
                        title="⚠️ System Notice", 
                        description=(
                            f"UID `{uid}` is already active and linked to your account.\n\n"
                            f"If you want to change it, use `!remove {uid}` to free your slot and then register again via `!free [UID]`."
                        ), 
                        color=0xffa500
                    )
                    await ctx.send(embed=embed)
                    conn.close()
                    return
                else:
                    embed = discord.Embed(
                        title="🚫 Device Limit Exceeded",
                        description=(
                            f"Hey {ctx.author.mention}, you can only manage **1 UID per Discord account**!\n\n"
                            f"**🔒 Currently Linked UID:** `{existing_uid}`\n\n"
                            f"If you want to use a different UID, remove your current slot first via:\n"
                            f"`!remove {existing_uid}`"
                        ),
                        color=0xff3333
                    )
                    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
                    embed.set_footer(text="🤖 NHE Premium Security Slot Lock")
                    await ctx.send(embed=embed)
                    conn.close()
                    return

    # আইডি ডাটাবেজে অলরেডি একটিভ আছে কিনা চেক
    cursor.execute("SELECT expiry FROM whitelist WHERE uid = ?", (uid,))
    row = cursor.fetchone()
    if row and row[0] > now:
        embed = discord.Embed(title="⚠️ System Notice", description=f"UID `{uid}` is already active in the database.", color=0xffa500)
        await ctx.send(embed=embed)
        conn.close()
        return

    conn.close()

    loading_embed = discord.Embed(description=f"⏳ Submitting Free Trial Request for UID: `{uid}`...", color=discord.Color.blue())
    msg = await ctx.send(embed=loading_embed)

    # আসল ফর্ম ফিল্ড সাবমিশন পেলোড (UID Input Field)
    form_payload = {"uid": str(uid)}

    tasks = [
        post_to_portal(url, form_payload, {"Referer": url, "Origin": "http://93.115.101.161:9293"}, name)
        for name, url in PORTAL_URLS.items()
    ]

    results = await asyncio.gather(*tasks)

    any_success = False
    all_already_claimed = True

    for portal_name, status_text, is_success in results:
        if is_success: 
            any_success = True
        if "Already" not in status_text: 
            all_already_claimed = False

    footer_text = "🤖 Commands: !free [UID] | !remove [UID]"
    grid_status = "Registered 🎉" if any_success else "Failed ❌"

    if all_already_claimed:
        embed = discord.Embed(title="⚠️ Registration Refused", description=f"**User ID:** `{uid}`\n\nThis target machine or IP grid has already exhausted its trial token.", color=0xffa500)
        embed.add_field(name="Distributed Grid Status", value=f"`{grid_status}`", inline=False)
        embed.set_footer(text=footer_text, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await msg.edit(embed=embed)
        return

    if not any_success:
        embed = discord.Embed(title="❌ Network Error", description=f"**User ID:** `{uid}`\n\nAll external synchronization channels returned fatal server codes.", color=0xff0000)
        embed.add_field(name="Distributed Grid Status", value=f"`{grid_status}`", inline=False)
        embed.set_footer(text=footer_text, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await msg.edit(embed=embed)
        return

    # স্ক্রিনশট অনুযায়ী ফ্রি ট্রায়াল সম্পূর্ণ ২৩ দিনের (২৩ দিন = ১৯৮৭ ۲۰۰ সেকেন্ড)
    expiry_duration = 1987200
    expiry = now + expiry_duration

    # ডাটাবেজে ইউআইডি সফলভাবে সেভ করা
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO whitelist (uid, discord_id, expiry) VALUES (?, ?, ?)", (uid, ctx.author.id, expiry))
    conn.commit()
    conn.close()

    embed = discord.Embed(title="✅ Access Granted & Whitelisted", color=0x00ff00)
    embed.add_field(name="Target UID", value=f"`{uid}`", inline=True)
    embed.add_field(name="Database Sync", value="Active 🟢", inline=True)
    embed.add_field(name="Linked User", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="Token Expiration", value=f"<t:{int(expiry)}:R>", inline=False)
    embed.add_field(name="📡 Distributed Grid Status", value=f"`{grid_status}`", inline=False)
    
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text=footer_text, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await msg.edit(embed=embed)

# ==================== 👑 EXCLUSIVE OWNER COMMANDS ====================

@bot.command()
async def url(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass

    try: status_msg = await ctx.author.send(embed=discord.Embed(description="⏳ Checking portal status... Please wait.", color=discord.Color.orange()))
    except discord.Forbidden: return

    embed = discord.Embed(title="🌐 Portal URL Status Diagnostic", color=0x3498db)
    
    if bot.http_session is None or bot.http_session.closed:
        bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())

    for name, url in PORTAL_URLS.items():
        try:
            async with bot.http_session.get(url, timeout=5, headers={"User-Agent": random.choice(USER_AGENTS)}) as resp:
                if resp.status in [200, 201, 405]: 
                    embed.add_field(name=name, value=f"🔗 {url}\n**Status:** `Working 🟢`", inline=False)
                else:
                    embed.add_field(name=name, value=f"🔗 {url}\n**Status:** `Not Working 🔴` (Code: {resp.status})", inline=False)
        except Exception:
            embed.add_field(name=name, value=f"🔗 {url}\n**Status:** `Not Working 🔴` (Offline/Timeout)", inline=False)

    await status_msg.edit(embed=embed)

@bot.command()
async def remove(ctx, uid: str):
    global IS_SERVER_STOPPED
    is_privileged = (ctx.author.id == OWNER_ID or ctx.author.id in VIP_MANAGERS or has_allowed_role(ctx.author))
    if IS_SERVER_STOPPED and not is_privileged: return

    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id FROM whitelist WHERE uid = ?", (uid,))
    row = cursor.fetchone()
    
    if row:
        linked_id = row[0]
        if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS and linked_id != ctx.author.id:
            embed = discord.Embed(title="🔒 Action Denied", description=f"You do not own the whitelist for UID `{uid}`!", color=0xff0000)
            await ctx.send(embed=embed)
            conn.close()
            return
            
        cursor.execute("DELETE FROM whitelist WHERE uid = ?", (uid,))
        conn.commit()
        embed = discord.Embed(title="🗑️ Authorization Revoked", description=f"UID `{uid}` has been successfully unlinked from SQL Database!", color=0x00ff00)
    else:
        embed = discord.Embed(title="❌ Data Not Found", description=f"UID `{uid}` could not be located inside database layers.", color=0xff0000)
        
    conn.close()
    await ctx.send(embed=embed)

@bot.command()
async def stop(ctx):
    if ctx.author.id != OWNER_ID: return
    global IS_SERVER_STOPPED
    IS_SERVER_STOPPED = True
    try: await ctx.message.delete()
    except: pass

    try:
        for overwrite_target in ctx.channel.overwrites.keys():
            if isinstance(overwrite_target, discord.Role):
                if overwrite_target.permissions.administrator or overwrite_target.id in ALLOWED_ROLE_IDS: continue
            overwrite = ctx.channel.overwrites_for(overwrite_target)
            overwrite.send_messages = False
            await ctx.channel.set_permissions(overwrite_target, overwrite=overwrite)
            
        everyone_overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        everyone_overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=everyone_overwrite)
    except Exception as e: print(f"❌ Role Error: {e}")

    embed = discord.Embed(title="🔒 NHE PREMIUM CLUSTER TERMINATED", description="### 🛑 Channel Status: CHAT OVERRIDE OFF\n\n**⚠️ THIS TIME UID WHITELIST ONLY ADMIN & VIP OWNER**", color=0xff1111)
    await ctx.send(embed=embed)

@bot.command()
async def on(ctx):
    if ctx.author.id != OWNER_ID: return
    global IS_SERVER_STOPPED
    IS_SERVER_STOPPED = False
    try: await ctx.message.delete()
    except: pass

    try:
        for overwrite_target in ctx.channel.overwrites.keys():
            overwrite = ctx.channel.overwrites_for(overwrite_target)
            overwrite.send_messages = True
            await ctx.channel.set_permissions(overwrite_target, overwrite=overwrite)
    except Exception as e: print(f"❌ Reset Error: {e}")

    embed = discord.Embed(title="🚀 TERMINAL SYSTEM ONLINE", description="### 🟢 Channel Status: OPEN FOR ALL ROLES", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
async def allremove(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass

    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM whitelist")
    conn.commit()
    conn.close()

    embed = discord.Embed(title="💥 CRITICAL RESET: ALL AUTHORIZATIONS PURGED", color=0xff0000)
    await ctx.send(embed=embed)

@bot.command()
async def vip(ctx):
    if ctx.author.id != OWNER_ID: return
    embed = discord.Embed(title="🌟 NHE VIP BROTHERS PANEL 🌟", color=0x00ffff)
    vip_list = "".join([f"**{c}.** Mention: <@{v_id}>\n" for c, v_id in enumerate(VIP_MANAGERS, 1)])
    embed.add_field(name="📋 Active VIP Managers List", value=vip_list, inline=False)
    await ctx.send(embed=embed)
     
@bot.command()
async def info(ctx):
    if ctx.author.id != OWNER_ID: return
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM whitelist")
    count = cursor.fetchone()[0]
    conn.close()
    await ctx.send(embed=discord.Embed(title="📊 Cluster Diagnostics", description=f"Active Whitelists: `{count}`", color=0x3498db))

@bot.command()
async def post(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass
    target_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if target_channel:
        await target_channel.send(content="@everyone", embed=discord.Embed(title="🚨 SERVER ISSUE ALERT!", description="Technical issues with **NHE UID Whitelist** server. Will be fixed soon!", color=0xff0000))

init_db()
threading.Thread(target=run_server, daemon=True).start()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN: bot.run(TOKEN)
else: print("❌ ERROR: DISCORD_TOKEN missing!")
