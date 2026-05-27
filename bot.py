import discord
from discord.ext import commands
import json
import time
import os
import asyncio              
from flask import Flask     
import threading            

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

def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r") as f: 
            return json.load(f)
    except Exception:
        print("⚠️ [File System] Whitelist JSON was corrupted or busy. Auto-resetting.")
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f: 
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"❌ [File System] Error saving database: {e}")

# ================= FLASK SERVER PART =================
app = Flask('')

@app.route('/', methods=['GET', 'POST'])
@app.route('/api/active_uids', methods=['GET', 'POST'])
@app.route('/api/uidipport', methods=['GET', 'POST'])
def handle_requests():
    # সরাসরি ফাইল থেকে একদম রিয়েল-টাইম ডেটা লোড করবে
    data = load_data()
    now = time.time()
    active_list = []

    for uid, info in data.items():
        if isinstance(info, dict):
            expiry = info.get("expiry", 0)
        else:
            expiry = info
            
        if now < expiry:
            active_list.append(str(uid).strip())

    response_text = "\n".join(active_list)
    
    return response_text, 200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

def run_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
# =====================================================================

@bot.event
async def on_ready():
    print(f"🔥 NHE Bot Pro v3 (Anti-Stuck Connected) is online as {bot.user.name}!")

def has_allowed_role(member):
    if not hasattr(member, 'roles'): return False
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

# ==================== 🛡️ CLEANED ANTI-STUCK MESSAGE PROCESSOR ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != CHANNEL_ID:
        return

    content = message.content.strip()
    valid_commands = ["!free", "!remove", "!info", "!post", "!vip", "!stop", "!on", "!allremove"]
    is_valid_command = any(content.startswith(cmd) for cmd in valid_commands)

    # স্প্যাম বা ফালতু মেসেজ হলে সাথে সাথে ডিলিট, কোনো লকিং নেই
    if not is_valid_command:
        try: 
            await message.delete()
        except: 
            pass
        return

    # কমান্ড প্রসেস করার জন্য বটের মেইন ইঞ্জিনে পাঠিয়ে দেওয়া হলো
    await bot.process_commands(message)

# ==================== !FREE COMMAND ====================
@bot.command()
async def free(ctx, uid: str):
    global IS_SERVER_STOPPED
    
    is_privileged = (ctx.author.id == OWNER_ID or 
                     ctx.author.id in VIP_MANAGERS or 
                     has_allowed_role(ctx.author))

    if IS_SERVER_STOPPED and not is_privileged:
        return

    if not (uid.isdigit() and 8 <= len(uid) <= 11):
        embed = discord.Embed(title="❌ Access Refused", description="UID formatting is invalid. Must be **8 to 11 pure digits**.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    data = load_data()
    now = time.time()
    
    # ডিভাইস লিমিট চেক (১টি ডিসকর্ড অ্যাকাউন্টের জন্য ১টি ইউআইডি)
    if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS:
        for existing_uid, info in data.items():
            if isinstance(info, dict) and info.get("discord_id") == ctx.author.id:
                if existing_uid == uid:
                    expiry = info.get("expiry", 0)
                    if expiry > now:
                        embed = discord.Embed(title="⚠️ System Notice", description=f"UID `{uid}` is already active.", color=0xffa500)
                        await ctx.send(embed=embed)
                        return
                else:
                    embed = discord.Embed(
                        title="🚫 Device Limit Exceeded",
                        description=f"Hey {ctx.author.mention}, you can only manage **1 UID per account**!\n\n**🔒 Active UID:** `{existing_uid}`\n\nTo change, type: `!remove {existing_uid}`",
                        color=0xff3333
                    )
                    await ctx.send(embed=embed)
                    return

    if uid in data:
        expiry = data[uid] if isinstance(data[uid], (int, float)) else data[uid].get("expiry", 0)
        if expiry > now:
            embed = discord.Embed(title="⚠️ System Notice", description=f"UID `{uid}` is already active in database.", color=0xffa500)
            await ctx.send(embed=embed)
            return

    # সরাসরি ২৪ ঘণ্টার জন্য ফাইলে পুশ
    expiry = now + 86400
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
    await ctx.send(embed=embed)

# ==================== !REMOVE COMMAND ====================
@bot.command()
async def remove(ctx, uid: str):
    global IS_SERVER_STOPPED
    is_privileged = (ctx.author.id == OWNER_ID or 
                     ctx.author.id in VIP_MANAGERS or 
                     has_allowed_role(ctx.author))

    if IS_SERVER_STOPPED and not is_privileged:
        return

    data = load_data()
    if uid in data:
        info = data[uid]
        
        if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS:
            linked_id = info.get("discord_id") if isinstance(info, dict) else None
            if linked_id != ctx.author.id:
                embed = discord.Embed(title="🔒 Action Denied", description="You do not own this UID!", color=0xff0000)
                await ctx.send(embed=embed)
                return
        
        del data[uid]
        save_data(data)
        embed = discord.Embed(title="🗑️ Authorization Revoked", description=f"UID `{uid}` unlinked successfully!", color=0x00ff00)
    else:
        embed = discord.Embed(title="❌ Data Not Found", description=f"UID `{uid}` not in database.", color=0xff0000)
    
    await ctx.send(embed=embed)

# ==================== 👑 EXCLUSIVE OWNER COMMANDS ====================

@bot.command()
async def stop(ctx):
    if ctx.author.id != OWNER_ID: return
    global IS_SERVER_STOPPED
    IS_SERVER_STOPPED = True
    try: await ctx.message.delete()
    except: pass

    embed = discord.Embed(
        title="🔒 NHE PREMIUM CLUSTER TERMINATED",
        description="### 🛑 Channel Status: LOCKDOWN\n\nOnly VIP and Admins can bypass right now.",
        color=0xff1111
    )
    await ctx.send(embed=embed)

@bot.command()
async def on(ctx):
    if ctx.author.id != OWNER_ID: return
    global IS_SERVER_STOPPED
    IS_SERVER_STOPPED = False
    try: await ctx.message.delete()
    except: pass

    embed = discord.Embed(title="🚀 TERMINAL SYSTEM ONLINE", description="### 🟢 Open for all roles.", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
async def allremove(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass
    save_data({})
    embed = discord.Embed(title="💥 CRITICAL RESET", description="All database slots cleared!", color=0xff0000)
    await ctx.send(embed=embed)

@bot.command()
async def vip(ctx):
    if ctx.author.id != OWNER_ID: return
    embed = discord.Embed(title="🌟 NHE VIP BROTHERS PANEL 🌟", color=0x00ffff)
    vip_list = "".join([f"**{i}.** <@{v_id}>\n" for i, v_id in enumerate(VIP_MANAGERS, 1)])
    embed.add_field(name="📋 Active VIP Managers", value=vip_list, inline=False)
    await ctx.send(embed=embed)
     
@bot.command()
async def info(ctx):
    if ctx.author.id != OWNER_ID: return
    data = load_data()
    now = time.time()
    active_count = len([u for u, info in data.items() if (info if isinstance(info, (int, float)) else info.get("expiry", 0)) > now])
        
    embed = discord.Embed(title="📊 Cluster Diagnostics", color=0x3498db)
    embed.add_field(name="Active Whitelists", value=f"`{active_count}`", inline=True)
    embed.add_field(name="System Status", value="Stable 🟢", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def post(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass
    target_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not target_channel: return
    embed = discord.Embed(title="🚨 SERVER ISSUE ALERT!", description="Unexpected technical issues. Back soon! 🚀", color=0xff0000)
    await target_channel.send(content="@everyone", embed=embed)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN: bot.run(TOKEN)
