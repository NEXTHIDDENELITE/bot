import discord
from discord.ext import commands
import time
import os
import asyncio              # Parallel thread execution এর জন্য
from flask import Flask     # লোকাল হোস্টিং ডেটাবেজ সার্ভারের জন্য
import threading                 # বট এবং ফ্লাস্ক সার্ভার একসাথে চালানোর জন্য

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

# 💾 LIVE MEMORY DATABASE (ফাইল সিস্টেমের ঝামেলা ছাড়া সরাসরি র‍্যামে ডেটা থাকবে)
live_whitelist_db = {}

# ================= FLASK SERVER PART (FIXED FOR C# CLIENT) =================
app = Flask('')

@app.route('/', methods=['GET', 'POST'])
@app.route('/api/active_uids', methods=['GET', 'POST'])
@app.route('/api/uidipport', methods=['GET', 'POST'])
def handle_requests():
    now = time.time()
    active_list = []

    # লাইভ মেমোরি থেকে সব একটিভ ইউআইডি চেক করা হচ্ছে
    for uid, info in list(live_whitelist_db.items()):
        if isinstance(info, dict):
            expiry = info.get("expiry", 0)
        else:
            expiry = info
            
        if now < expiry:
            active_list.append(str(uid).strip())
        else:
            # মেয়াদ শেষ হয়ে গেলে অটোমেটিক মেমোরি থেকে রিমুভ হবে
            if uid in live_whitelist_db:
                del live_whitelist_db[uid]

    response_text = "\n".join(active_list)
    
    # C# WebClient যাতে কোনো বাধা বা ক্যাশ ছাড়া সরাসরি নতুন ডেটা পায়
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
    print(f"🔥 NHE Bot Pro v2 (Live Memory Mode) is online as {bot.user.name}!")

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
        except Exception:
            pass
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
        msg = await ctx.send(embed=embed)
        if IS_SERVER_STOPPED:  
            await asyncio.sleep(5)
            try: await msg.delete()
            except: pass
        return

    now = time.time()
    
    # ডিভাইস লিমিট চেক (১টি ডিসকর্ড অ্যাকাউন্টের জন্য ১টি ইউআইডি)
    if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS:
        for existing_uid, info in list(live_whitelist_db.items()):
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
                    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
                    embed.set_footer(text="🤖 NHE Premium Security Slot Lock")
                    msg_limit = await ctx.send(embed=embed)
                    if IS_SERVER_STOPPED:
                        await asyncio.sleep(5)
                        try: await msg_limit.delete()
                        except: pass
                    return

    if uid in live_whitelist_db:
        expiry = live_whitelist_db[uid] if isinstance(live_whitelist_db[uid], (int, float)) else live_whitelist_db[uid].get("expiry", 0)
        if expiry > now:
            embed = discord.Embed(title="⚠️ System Notice", description=f"UID `{uid}` is already active in the database.", color=0xffa500)
            msg = await ctx.send(embed=embed)
            if IS_SERVER_STOPPED:
                await asyncio.sleep(5)
                try: await msg.delete()
                except: pass
            return

    # সরাসরি ২৪ ঘণ্টার জন্য লাইভ মেমোরিতে একটিভ হবে
    expiry_duration = 86400 
    expiry = now + expiry_duration

    live_whitelist_db[uid] = {
        "expiry": expiry,
        "discord_id": ctx.author.id
    }

    embed = discord.Embed(title="✅ Access Granted & Whitelisted", color=0x00ff00)
    embed.add_field(name="Target UID", value=f"`{uid}`", inline=True)
    embed.add_field(name="Database Sync", value="Live Memory Active 🟢", inline=True)
    embed.add_field(name="Linked User", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="Token Expiration", value=f"<t:{int(expiry)}:R>", inline=False)
    
    footer_text = "🤖 Live Database Bypass Active"
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    if ctx.author.avatar: embed.set_footer(text=footer_text, icon_url=ctx.author.avatar.url)
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

    if uid in live_whitelist_db:
        info = live_whitelist_db[uid]
        
        if ctx.author.id != OWNER_ID and ctx.author.id not in VIP_MANAGERS:
            linked_id = info.get("discord_id") if isinstance(info, dict) else None
            if linked_id != ctx.author.id:
                embed = discord.Embed(
                    title="🔒 Action Denied",
                    description=f"You do not own the whitelist for UID `{uid}`!\nYou cannot remove another member's device assignment.",
                    color=0xff0000
                )
                msg_deny = await ctx.send(embed=embed)
                if IS_SERVER_STOPPED:
                    await asyncio.sleep(5)
                    try: await msg_deny.delete()
                    except: pass
                return
        
        del live_whitelist_db[uid]
        embed = discord.Embed(
            title="🗑️ Authorization Revoked",
            description=f"UID `{uid}` has been successfully unlinked from the database!",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(
            title="❌ Data Not Found",
            description=f"UID `{uid}` could not be located inside active database.",
            color=0xff0000
        )
    
    msg = await ctx.send(embed=embed)
    if IS_SERVER_STOPPED:
        await asyncio.sleep(5)
        try: await msg.delete()
        except: pass

# ==================== 👑 EXCLUSIVE OWNER COMMANDS ====================

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
        print(f"❌ Failed to modify roles: {e}")

    embed = discord.Embed(
        title="🔒 NHE PREMIUM CLUSTER TERMINATED",
        description=(
            "### 🛑 Channel Status: CHAT OVERRIDE OFF\n\n"
            "**⚠️ THIS TIME UID WHITELIST ONLY ADMIN & VIP OWNER**\n\n"
            "Dear **NHE Members**, this channel has been completely locked by the Administrator.\n\n"
            "🌟 **Authorized System Personnel:**\n"
            "👑 **System Authority:** `NHE TEAM`\n"
            "👤 **VIP Manager 1:** <@1464861365645607027>\n"
            "👤 **VIP Manager 2:** <@1100273442894401616>"
        ),
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
        print(f"❌ Failed to reset roles: {e}")

    embed = discord.Embed(
        title="🚀 TERMINAL SYSTEM ONLINE",
        description="### 🟢 Channel Status: OPEN FOR ALL ROLES\n\nAll members can now run bot commands as usual.",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
async def allremove(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except: pass

    uid_list_text = ""
    if live_whitelist_db:
        for count, (u, info) in enumerate(list(live_whitelist_db.items()), 1):
            discord_mention = f"<@{info.get('discord_id')}>" if isinstance(info, dict) else "Unknown"
            uid_list_text += f"**{count}.** UID: `{u}` ➔ Linked to: {discord_mention}\n"
    else:
        uid_list_text = "*Database is already clear!*"

    live_whitelist_db.clear()

    embed = discord.Embed(title="💥 CRITICAL RESET: ALL AUTHORIZATIONS REVOKED", description=uid_list_text, color=0xff0000)
    await ctx.send(embed=embed)

@bot.command()
async def vip(ctx):
    if ctx.author.id != OWNER_ID: return
    embed = discord.Embed(title="🌟 NHE VIP BROTHERS PANEL 🌟", color=0x00ffff)
    vip_list = "".join([f"**{i}.** <@{v_id}> (`{v_id}`)\n" for i, v_id in enumerate(VIP_MANAGERS, 1)])
    embed.add_field(name="📋 Active VIP Managers List", value=vip_list, inline=False)
    await ctx.send(embed=embed)
     
@bot.command()
async def info(ctx):
    if ctx.author.id != OWNER_ID: return
    now = time.time()
    active_count = len([u for u, info in list(live_whitelist_db.items()) if (info if isinstance(info, (int, float)) else info.get("expiry", 0)) > now])
        
    embed = discord.Embed(title="📊 Cluster Diagnostics", color=0x3498db)
    embed.add_field(name="Active Whitelists", value=f"`{active_count}`", inline=True)
    embed.add_field(name="System Runtime", value="Stable 🟢", inline=True)
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
        description="We are currently facing unexpected technical issues with our server. As soon as it's fixed, it will be back online! 🚀", 
        color=0xff0000 
    )
    await target_channel.send(content="@everyone", embed=embed)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN: bot.run(TOKEN)
