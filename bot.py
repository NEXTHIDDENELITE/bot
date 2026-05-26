import discord
from discord.ext import commands
import json
import time
import os
import aiohttp              # For high-speed async HTTP requests
import asyncio              # For parallel thread execution
from flask import Flask, request  # For the local whitelist server
import threading                 # For running both the bot and server together
import random                    # For rotating User-Agents to mimic human traffic

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "whitelist.json"
CHANNEL_ID = 1507774505425178735 
ANNOUNCEMENT_CHANNEL_ID = 1480775677505441813 

# 👑 OWNER & DEVELOPER CONFIGURATION (Only this ID can use Admin/Info/Post/Vip Commands)
OWNER_ID = 1483917215349735674

# 🌟 VIP MANAGERS CONFIGURATION (Unlimited UIDs & Bypass Stop Lock)
VIP_MANAGERS = [1464861365645607027, 1100273442894401616]

# 🏷️ ALLOWED ROLE IDS DURING STOP MODE (এই রোল আইডিগুলো !stop এর মধ্যেও কমান্ড দিতে পারবে)
ALLOWED_ROLE_IDS = [1480832209995698259, 1480836036916674632]

# 🔒 Global Server Stop Status Tracker
IS_SERVER_STOPPED = False

# 🔒 File Lock to prevent JSON corruption when multi-users spam commands
file_lock = asyncio.Lock()
# 🌐 Global Session Instance to prevent memory leaks and speed up connections
bot.http_session = None

# পোর্টালের সিকিউরিটি বাইপাস করার জন্য র্যান্ডম ইউজার এজেন্ট লিস্ট
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"
]

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
    bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
    print(f"🔥 NHE Bot Pro v2 is online as {bot.user.name}!")
    print("🌐 Channel Lock & Admin Guard Running. Status: SECURE 🟢")

# Helper function to check if user has allowed role IDs
def has_allowed_role(member):
    if not hasattr(member, 'roles'): return False
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

# ==================== 🛡️ ANTI-SPAM & CHANNEL LOCK LOGIC ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != CHANNEL_ID:
        return

    # প্রিভিলেজড চেক (ওনার, ভিআইপি ম্যানেজার, অথবা এলাউড ২টা রোল আইডি)
    is_privileged = (message.author.id == OWNER_ID or 
                     message.author.id in VIP_MANAGERS or 
                     has_allowed_role(message.author))

    valid_commands = ["!free", "!remove", "!info", "!post", "!vip", "!stop", "!on", "!allremove"]
    content = message.content.strip()
    is_valid_command = any(content.startswith(cmd) for cmd in valid_commands)

    # 👑 🔥 [EXCLUSIVE OWNER COMMAND CHECK] !info, !post, !vip, !stop, !on, !allremove শুধু ওনার পারবে
    owner_only_commands = ["!info", "!post", "!vip", "!stop", "!on", "!allremove"]
    is_owner_command = any(content.startswith(cmd) for cmd in owner_only_commands)

    if is_owner_command and message.author.id != OWNER_ID:
        try:
            await message.delete()
            warn_msg = await message.channel.send(f"❌ {message.author.mention}, **Only the Bot Owner can use this command!**")
            await asyncio.sleep(4)
            await warn_msg.delete()
        except Exception:
            pass
        return

    # 🛑 ১. যখন সার্ভার !stop (লকড) থাকবে
    if IS_SERVER_STOPPED:
        if is_privileged:
            # প্রিভিলেজড মেম্বাররা কমান্ড দিলে তাদের মেসেজ ৫ সেকেন্ড পর ডিলিট করার ব্যাকএন্ড টাস্ক
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

    # 🚀 ২. যখন সার্ভার !on (আনলকড) থাকবে
    else:
        # কমান্ড ছাড়া অন্য কিছু (সাধারণ চ্যাট/লিংক/স্প্যাম) দিলে সাথে সাথে ডিলিট হবে
        if not is_valid_command:
            try:
                await message.delete()
                warn_msg = await message.channel.send(f"⚠️ {message.author.mention}, **Only working bot commands are allowed here!**")
                await asyncio.sleep(3)
                await warn_msg.delete()
            except Exception as e:
                print(f"❌ [Anti-Spam] Failed to delete non-command message: {e}")
            return

        # ভ্যালিড কমান্ড হলে মেসেজ ডিলিট হবে না, নরমালি প্রসেস হবে
        await bot.process_commands(message)

# ==================== ADVANCED PARALLEL REQUEST ENGINE ====================
async def post_to_portal(url, data, headers, portal_name, is_json=False):
    """Super-fast, isolated request worker with custom regex-like keyword mapping"""
    if bot.http_session is None or bot.http_session.closed:
        bot.http_session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        
    try:
        if is_json:
            kwargs = {"json": data}
        else:
            kwargs = {"data": data}

        async with bot.http_session.post(url, headers=headers, timeout=6, **kwargs) as response:
            res_text = await response.text()
            lowered_res = res_text.lower()
            
            if response.status in [200, 201]:
                block_keywords = ["already", "exists", "registered", "claimed", "বিদ্যমান", "ইতিমধ্যেই", "নিবন্ধিত", "success: false"]
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
    
    is_privileged = (ctx.author.id == OWNER_ID or 
                     ctx.author.id in VIP_MANAGERS or 
                     has_allowed_role(ctx.author))

    if IS_SERVER_STOPPED and not is_privileged:
        return

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
                            f"If you want to use a different UID, you must remove your current session first by typing:\n"
                            f"`!remove {existing_uid}`"
                        ),
                        color=0xff3333
                    )
                    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else bot.user.avatar.url)
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

    loading_embed = discord.Embed(
        description=f"⏳ Processing UID: `{uid}` across encrypted failover routes...",
        color=discord.Color.blue()
    )
    msg = await ctx.send(embed=loading_embed)

    portal1_url = "https://excheatsofficial.xyz/portal/59e63dd8193a762c"
    portal2_url = "https://www.anikxcheatx.com/free/bd45d206"

    form_data = {"uid": uid, "hardware_uid": uid}

    task1 = post_to_portal(portal1_url, form_data, {"Referer": portal1_url}, "Secure Route Alpha 🔒", is_json=False)
    task2 = post_to_portal(portal2_url, form_data, {"Referer": portal2_url}, "Secure Route Bravo 🛡️", is_json=False)

    results = await asyncio.gather(task1, task2)

    status_dict = {}
    any_success = False
    all_already_claimed = True

    for portal_name, status_text, is_success in results:
        status_dict[portal_name] = status_text
        if is_success: any_success = True
        if "Already" not in status_text: all_already_claimed = False

    footer_text = "🤖 Commands: !free [UID] | !remove [UID]"

    if all_already_claimed:
        embed = discord.Embed(
            title="⚠️ Registration Refused",
            description=f"**User ID:** `{uid}`\n\nThis target machine has already exhausted its trial token on this grid.",
            color=0xffa500
        )
        for name, status in status_dict.items():
            embed.add_field(name=name, value=f"`{status}`", inline=True)
        embed.set_footer(text=footer_text, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await msg.edit(embed=embed)
        if IS_SERVER_STOPPED:
            await asyncio.sleep(5)
            try: await msg.delete()
            except: pass
        return

    if not any_success:
        embed = discord.Embed(
            title="❌ Network Error",
            description=f"**User ID:** `{uid}`\n\nAll external synchronization channels returned fatal server codes.",
            color=0xff0000
        )
        for name, status in status_dict.items():
            embed.add_field(name=name, value=f"`{status}`", inline=True)
        embed.set_footer(text=footer_text, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await msg.edit(embed=embed)
        if IS_SERVER_STOPPED:
            await asyncio.sleep(5)
            try: await msg.delete()
            except: pass
        return

    expiry_duration = 259200 if status_dict.get("Secure Route Bravo 🛡️") == "Registered 🎉" else 86400
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
    embed.add_field(name="Database Sync", value="Active 🟢", inline=True)
    embed.add_field(name="Linked User", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="Token Expiration", value=f"<t:{int(expiry)}:R>", inline=False)
    embed.add_field(name="📡 Distributed Grid Status", value="\n".join([f"**{name}:** `{status}`" for name, status in status_dict.items()]), inline=False)
    
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    
    embed.set_footer(text=footer_text, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await msg.edit(embed=embed)

    if IS_SERVER_STOPPED:
        await asyncio.sleep(5)
        try: await msg.delete()
        except: pass

# =====================================================================

@bot.command()
async def remove(ctx, uid: str):
    global IS_SERVER_STOPPED
    is_privileged = (ctx.author.id == OWNER_ID or 
                     ctx.author.id in VIP_MANAGERS or 
                     has_allowed_role(ctx.author))

    if IS_SERVER_STOPPED and not is_privileged:
        return

    async with file_lock:
        data = load_data()
        
        if uid in data:
            info = data[uid]
            
            if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS:
                linked_id = info.get("discord_id") if isinstance(info, dict) else None
                if linked_id != ctx.author.id:
                    embed = discord.Embed(
                        title="🔒 Action Denied",
                        description=f"You do not own the whitelist for UID `{uid}`!\nYou cannot remove another member's device assignment.",
                        color=0xff0000
                    )
                    embed.set_footer(text="🤖 Device Authorization Security")
                    msg_deny = await ctx.send(embed=embed)
                    if IS_SERVER_STOPPED:
                        await asyncio.sleep(5)
                        try: await msg_deny.delete()
                        except: pass
                    return
            
            del data[uid]
            save_data(data)
            embed = discord.Embed(
                title="🗑️ Authorization Revoked",
                description=f"UID `{uid}` has been successfully unlinked and cleared from the master database!\n\nYour slot is now **empty** and ready for a new registration.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Data Not Found",
                description=f"UID `{uid}` could not be located inside any active database layers.",
                color=0xff0000
            )
    
    embed.set_footer(text="🤖 Commands: !free [UID] | !remove [UID]")
    msg = await ctx.send(embed=embed)
    
    if IS_SERVER_STOPPED:
        await asyncio.sleep(5)
        try: await msg.delete()
        except: pass

# ==================== 👑 ADVANCED EXCLUSIVE OWNER COMMANDS ====================

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
                if overwrite_target.permissions.administrator or overwrite_target.id in ALLOWED_ROLE_IDS:
                    continue
            
            overwrite = ctx.channel.overwrites_for(overwrite_target)
            overwrite.send_messages = False
            await ctx.channel.set_permissions(overwrite_target, overwrite=overwrite)
            
        everyone_overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        everyone_overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=everyone_overwrite)
        
        special_users = [OWNER_ID] + VIP_MANAGERS
        for user_id in special_users:
            member = ctx.guild.get_member(user_id)
            if member:
                user_overwrite = ctx.channel.overwrites_for(member)
                user_overwrite.send_messages = True
                await ctx.channel.set_permissions(member, overwrite=user_overwrite)

        for role_id in ALLOWED_ROLE_IDS:
            role = ctx.guild.get_role(role_id)
            if role:
                role_overwrite = ctx.channel.overwrites_for(role)
                role_overwrite.send_messages = True
                await ctx.channel.set_permissions(role, overwrite=role_overwrite)
        
    except Exception as e:
        print(f"❌ Failed to modify all roles permissions: {e}")

    embed = discord.Embed(
        title="🔒 NHE PREMIUM CLUSTER TERMINATED",
        description=(
            "### 🛑 Channel Status: CHAT OVERRIDE OFF\n\n"
            "**⚠️ THIS TIME UID WHITELIST ONLY ADMIN & VIP OWNER**\n\n"
            "Dear **NHE Members & All Roles**, this channel has been completely locked by the Administrator.\n"
            "All message-sending capabilities have been revoked for every role group.\n\n"
            "🌟 **Authorized System Personnel:**\n"
            "👑 **System Authority:** `NHE TEAM`\n"
            "👤 **VIP Manager 1 (KESMAT):** <@1464861365645607027>\n"
            "👤 **VIP Manager 2 (ROHAN):** <@1100273442894401616>\n\n"
            "> **Notice:** The system is going under routine database sync or temporary pause. "
            "Please wait patiently until the Owner reactivates the terminal grid. 🚀"
        ),
        color=0xff1111
    )
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text="👑 System Guard Protocol — NHE Team")
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
            
        everyone_overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        everyone_overwrite.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=everyone_overwrite)
        
        special_users = [OWNER_ID] + VIP_MANAGERS
        for user_id in special_users:
            member = ctx.guild.get_member(user_id)
            if member:
                await ctx.channel.set_permissions(member, overwrite=None)

        for role_id in ALLOWED_ROLE_IDS:
            role = ctx.guild.get_role(role_id)
            if role:
                await ctx.channel.set_permissions(role, overwrite=None)
                
    except Exception as e:
        print(f"❌ Failed to reset all roles permissions: {e}")

    embed = discord.Embed(
        title="🚀 TERMINAL SYSTEM ONLINE",
        description=(
            "### 🟢 Channel Status: OPEN FOR ALL ROLES\n\n"
            "The **NHE Whitelist Terminal** has been successfully unlocked by the Owner!\n"
            "All members and role groups can now run `!free [UID]` or `!remove [UID]` commands as usual."
        ),
        color=0x00ff00
    )
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text="👑 Active Authorization Mode — NHE Team")
    await ctx.send(embed=embed)

@bot.command()
async def allremove(ctx):
    if ctx.author.id != OWNER_ID: return
    
    try: await ctx.message.delete()
    except: pass

    async with file_lock:
        data = load_data()
        
        uid_list_text = ""
        if data:
            for count, (u, info) in enumerate(data.items(), 1):
                discord_mention = f"<@{info.get('discord_id')}>" if isinstance(info, dict) else "Legacy/Unknown"
                uid_list_text += f"**{count}.** UID: `{u}` ➔ Linked to: {discord_mention}\n"
        else:
            uid_list_text = "*No active UIDs found. Database is already clear!*"

        save_data({})

    embed = discord.Embed(
        title="💥 CRITICAL RESET: ALL AUTHORIZATIONS REVOKED",
        description="Every single whitelist instance has been successfully purged from the database cluster layer.",
        color=0xff0000
    )
    embed.add_field(name="📋 Removed UIDs List", value=uid_list_text, inline=False)
    embed.set_footer(text="👑 Master Clearance Command Issued")
    await ctx.send(embed=embed)

@bot.command()
async def vip(ctx):
    if ctx.author.id != OWNER_ID: return
    
    embed = discord.Embed(
        title="🌟 NHE VIP BROTHERS PANEL 🌟",
        description="This panel displays authorized personnel with **Unlimited UID Slots** and **System Override Bypass Permissions**.",
        color=0x00ffff
    )
    vip_list = ""
    for count, vip_id in enumerate(VIP_MANAGERS, 1):
        vip_list += f"**{count}.** Manager Mention: <@{vip_id}>\n➔ ID: `{vip_id}`\n\n"
        
    embed.add_field(name="📋 Active VIP Managers List", value=vip_list, inline=False)
    embed.set_footer(text="👑 Security Status: SECURE TERMINAL ACCESSED")
    await ctx.send(embed=embed)

# =====================================================================
     
@bot.command()
async def info(ctx):
    if ctx.author.id != OWNER_ID: return
    
    async with file_lock:
        data = load_data()
        now = time.time()
        
        active_uids = {}
        for u, info in data.items():
            expiry = info if isinstance(info, (int, float)) else info.get("expiry", 0)
            if expiry > now:
                active_uids[u] = info
                
        if len(active_uids) != len(data): save_data(active_uids)
        
    embed = discord.Embed(title="📊 Cluster Diagnostics", color=0x3498db)
    embed.add_field(name="Active Whitelists", value=f"`{len(active_uids)}`", inline=True)
    embed.add_field(name="System Runtime", value="Stable 🟢", inline=True)
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    
    embed.set_footer(text="🤖 Commands: !free [UID] | !remove [UID]")
    msg = await ctx.send(embed=embed)
    
    if IS_SERVER_STOPPED:
        await asyncio.sleep(5)
        try: await msg.delete()
        except: pass

@bot.command()
async def post(ctx):
    if ctx.author.id != OWNER_ID: return

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

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERROR: DISCORD_TOKEN Environment Variable is missing in Render Settings!")
