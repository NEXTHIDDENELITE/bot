import discord
from discord.ext import commands
import json
import time
import os
from flask import Flask, request
import threading
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "whitelist.json"
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

# 🔒 File Lock to prevent JSON corruption
file_lock = asyncio.Lock()

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

@app.route('/')
def home():
    return "🔥 NHE Bot Pro v2 is fully operational and alive! 🟢", 200

# dnSpy প্যানেল ডাটা চেক করার জন্য এপিআই রুট
@app.route('/api/uidipport', methods=['GET', 'POST'])
@app.route('/api/active_uids', methods=['GET', 'POST']) # dnSpy এর সাথে মিল রাখার জন্য অতিরিক্ত রুট
@app.route('/api/certificate', methods=['GET', 'POST'])
def handle_requests():
    if 'certificate' in request.path:
        return "true", 200

    data = load_data()
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

    if uid in data:
        expiry = data[uid] if isinstance(data[uid], (int, float)) else data[uid].get("expiry", 0)
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
    print(f"🔥 NHE Bot Pro v2 is online as {bot.user.name}!")
    print("🌐 Clean Database Engine Running. Status: SECURE 🟢")

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

    valid_commands = ["!free", "!remove", "!info", "!post", "!vip", "!stop", "!on", "!allremove"]
    content = message.content.strip()
    is_valid_command = any(content.startswith(cmd) for cmd in valid_commands)

    owner_only_commands = ["!info", "!post", "!vip", "!stop", "!on", "!allremove"]
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
            except Exception: pass
            return

        await bot.process_commands(message)

# ==================== CLEAN LOCAL !FREE COMMAND ====================
@bot.command()
async def free(ctx, uid: str):
    global IS_SERVER_STOPPED
    
    is_privileged = (ctx.author.id == OWNER_ID or 
                     ctx.author.id in VIP_MANAGERS or 
                     has_allowed_role(ctx.author))

    if IS_SERVER_STOPPED and not is_privileged: return

    if not (uid.isdigit() and 8 <= len(uid) <= 11):
        embed = discord.Embed(title="❌ Access Refused", description="UID formatting is invalid. Must be **8 to 11 pure digits**.", color=0xff0000)
        msg = await ctx.send(embed=embed)
        if IS_SERVER_STOPPED:  
            await asyncio.sleep(5)
            try: await msg.delete()
            except: pass
        return

    async with file_lock:
        data = load_data()
    now = time.time()
    
    if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS:
        for existing_uid, info in data.items():
            if isinstance(info, dict) and info.get("discord_id") == ctx.author.id:
                if existing_uid == uid:
                    expiry = info.get("expiry", 0)
                    if expiry > now:
                        embed = discord.Embed(title="⚠️ System Notice", description=f"UID `{uid}` is already active and linked to your account.", color=0xffa500)
                        msg_exist = await ctx.send(embed=embed)
                        if IS_SERVER_STOPPED:
                            await asyncio.sleep(5)
                            try: await msg_exist.delete()
                            except: pass
                        return
                else:
                    embed = discord.Embed(
                        title="🚫 Device Limit Exceeded",
                        description=(
                            f"Hey {ctx.author.mention}, you can only manage **1 UID per Discord account**!\n\n"
                            f"**🔒 Currently Linked UID:** `{existing_uid}`\n\n"
                            f"If you want to use a different UID, remove your current session first:\n"
                            f"`!remove {existing_uid}`"
                        ),
                        color=0xff3333
                    )
                    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
                    embed.set_footer(text="🤖 NHE Premium Security Slot Lock")
                    msg_limit = await ctx.send(embed=embed)
                    if IS_SERVER_STOPPED:
                        await asyncio.sleep(5)
                        try: await msg_limit.delete()
                        except: pass
                    return

    if uid in data:
        expiry = data[uid] if isinstance(data[uid], (int, float)) else data[uid].get("expiry", 0)
        if expiry > now:
            embed = discord.Embed(title="⚠️ System Notice", description=f"UID `{uid}` is already active in the database.", color=0xffa500)
            msg = await ctx.send(embed=embed)
            if IS_SERVER_STOPPED:
                await asyncio.sleep(5)
                try: await msg.delete()
                except: pass
            return

    # বাইরের পোর্টাল ছাড়া সরাসরি নিজস্ব ডাটাবেজে ২৪ ঘণ্টার (৮৬৪০০ সেকেন্ড) জন্য হোয়াইটলিস্ট অ্যাক্সেস
    expiry_duration = 86400 
    expiry = now + expiry_duration

    async with file_lock:
        data = load_data()
        data[uid] = {
            "expiry": expiry,
            "discord_id": ctx.author.id
        }
        save_data(data)

    embed = discord.Embed(title="✅ Access Granted & Whitelisted", color=0x00ff00)
    embed.add_field(name="Target UID", value=f"`{uid}`", inline=True)
    embed.add_field(name="Database Sync", value="Local Active 🟢", inline=True)
    embed.add_field(name="Linked User", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="Token Expiration", value=f"<t:{int(expiry)}:R>", inline=False)
    
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text="🤖 Local Database Bypass Active")
    await ctx.send(embed=embed)

# ==================== REMOVE COMMAND ====================
@bot.command()
async def remove(ctx, uid: str):
    global IS_SERVER_STOPPED
    is_privileged = (ctx.author.id == OWNER_ID or 
                     ctx.author.id in VIP_MANAGERS or 
                     has_allowed_role(ctx.author))

    if IS_SERVER_STOPPED and not is_privileged: return

    async with file_lock:
        data = load_data()
        
        if uid in data:
            info = data[uid]
            if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS:
                linked_id = info.get("discord_id") if isinstance(info, dict) else None
                if linked_id != ctx.author.id:
                    embed = discord.Embed(title="🔒 Action Denied", description=f"You do not own the whitelist for UID `{uid}`!", color=0xff0000)
                    await ctx.send(embed=embed)
                    return
            
            del data[uid]
            save_data(data)
            embed = discord.Embed(title="🗑️ Authorization Revoked", description=f"UID `{uid}` successfully cleared from local database!", color=0x00ff00)
        else:
            embed = discord.Embed(title="❌ Data Not Found", description=f"UID `{uid}` not found in active layers.", color=0xff0000)
    
    await ctx.send(embed=embed)

# ==================== ADMIN & CONTROL COMMANDS ====================
@bot.command()
async def stop(ctx):
    if ctx.author.id != OWNER_ID: return
    global IS_SERVER_STOPPED
    IS_SERVER_STOPPED = True
    try: await ctx.message.delete()
    except: pass
    embed = discord.Embed(title="🔒 NHE PREMIUM CLUSTER LOCKED", description="Channel locked by Administrator. Only Admin/VIP can issue whitelist.", color=0xff1111)
    await ctx.send(embed=embed)

@bot.command()
async def on(ctx):
    if ctx.author.id != OWNER_ID: return
    global IS_SERVER_STOPPED
    IS_SERVER_STOPPED = False
    try: await ctx.message.delete()
    except: pass
    embed = discord.Embed(title="🚀 TERMINAL SYSTEM ONLINE", description="The Whitelist Terminal is now open for all roles group.", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
async def allremove(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass
    async with file_lock:
        save_data({})
    embed = discord.Embed(title="💥 CRITICAL RESET: ALL AUTHORIZATIONS PURGED", description="Database has been completely cleared.", color=0xff0000)
    await ctx.send(embed=embed)

@bot.command()
async def vip(ctx):
    if ctx.author.id != OWNER_ID: return
    embed = discord.Embed(title="🌟 NHE VIP BROTHERS PANEL 🌟", description="Unlimited UID Slots and Override Bypass Active.", color=0x00ffff)
    await ctx.send(embed=embed)
     
@bot.command()
async def info(ctx):
    if ctx.author.id != OWNER_ID: return
    async with file_lock:
        data = load_data()
    embed = discord.Embed(title="📊 Cluster Diagnostics", color=0x3498db)
    embed.add_field(name="Active Whitelists", value=f"`{len(data)}`", inline=True)
    embed.add_field(name="System Runtime", value="Stable 🟢", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def post(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass
    target_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not target_channel: return
    embed = discord.Embed(title="🚨 SERVER ISSUE ALERT!", description="Technical issues under maintenance. Will be free again soon!", color=0xff0000)
    await target_channel.send(content="@everyone", embed=embed)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERROR: DISCORD_TOKEN Environment Variable is missing!")
