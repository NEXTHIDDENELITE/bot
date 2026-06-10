import os
import json
import requests
import discord
from discord.ext import commands
from quart import Quart, request, jsonify
import asyncio

# ⚙️ Firebase Realtime Database URL
FIREBASE_BASE_URL = 'https://uid-whitelist-default-rtdb.firebaseio.com'

# ডিসকর্ড বট এবং কোয়ার্ট ওয়েব সার্ভার সেটিংস
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
app = Quart(__name__)

# ==========================================
# 🤖 ডিসকর্ড বট পার্ট (Discord Bot Commands)
# ==========================================
@bot.event
async def on_ready():
    print("==============================================")
    print(f"Logged in successfully as: {bot.user.name}")
    print("Firebase Realtime Database Connected!")
    print("==============================================")

@bot.command(name='free')
async def free_whitelist(ctx, uid: str = None):
    if uid is None:
        embed_error = discord.Embed(
            title="❌ ভুল ফরম্যাট!",
            description="দয়া করে কমান্ডটির সাথে আপনার সঠিক UID দিন।\n\n**সঠিক নিয়ম:**\n`!free <আপনার_UID>`\n\n*উদাহরণ:* `!free 8378790602`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_error)
        return

    if not uid.isdigit() or len(uid) < 8 or len(uid) > 12:
        embed_invalid = discord.Embed(
            title="❌ অবৈধ UID!",
            description="আপনার দেওয়া UID-টি সঠিক নয়। Free Fire UID শুধুমাত্র সংখ্যায় ৮ থেকে ১২ ডিজিটের হয়ে থাকে।",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_invalid)
        return

    status_msg = await ctx.send("⏳ *ডাটাবেজ চেক করা হচ্ছে, দয়া করে একটু অপেক্ষা করুন...*")

    try:
        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)
        
        if response.status_code == 200 and response.json() is not None:
            await status_msg.delete()
            embed_exist = discord.Embed(
                title="⚠️ অলরেডি রেজিস্টার্ড!",
                description=f"**UID {uid}** অলরেডি ডাটাবেজে হোয়াইটলিস্ট করা আছে মামা!",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed_exist)
            return

        user_data = {
            "discord_name": str(ctx.author.name),
            "discord_id": str(ctx.author.id),
            "status": "active"
        }
        
        save_response = requests.put(check_url, data=json.dumps(user_data))
        await status_msg.delete()

        if save_response.status_code == 200:
            embed_success = discord.Embed(
                title="✅ Whitelist Successful!",
                description="আপনার UID সফলভাবে প্যানেলের ডাটাবেজে যুক্ত করা হয়েছে।",
                color=discord.Color.green()
            )
            embed_success.add_field(name="Registered UID", value=f"`{uid}`", inline=False)
            embed_success.add_field(name="Authorized By", value=ctx.author.mention, inline=False)
            embed_success.add_field(name="Status", value="🟢 Active", inline=False)
            embed_success.set_footer(text="NHE Premium Bypass")
            await ctx.send(embed=embed_success)
        else:
            await ctx.send(f"❌ ডাটাবেজ এরর: সার্ভার কোড {save_response.status_code} দিয়েছে।")

    except Exception as e:
        print(f"Error: {e}")
        try: await status_msg.delete()
        except: pass
        await ctx.send("❌ সিস্টেমের কোনো একটি সমস্যা হয়েছে।")

# ==========================================
# 🌐 প্যানেল এপিআই পার্ট (C# Panel API Endpoints)
# ==========================================
@app.route('/api/uidipport', methods=['POST'])
async def uid_ip_port():
    try:
        req_data = await request.get_json(silent=True) or await request.form
        uid = req_data.get('uid') if req_data else None

        if not uid:
            return jsonify({"status": "failed", "message": "UID missing"}), 400

        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)

        if response.status_code == 200 and response.json() is not None:
            db_data = response.json()
            if db_data.get("status") == "active":
                return jsonify({
                    "status": "success",
                    "message": "Access Granted",
                    "ip": "127.0.0.1",
                    "port": "8080"
                }), 200

        return jsonify({"status": "failed", "message": "NOT whitelisted"}), 403

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/certificate', methods=['GET', 'POST'])
async def get_certificate():
    return jsonify({"status": "success", "certificate": "valid_cert_data_here"})

# ==========================================
# 🚀 রান করার মেইন ফাংশন
# ==========================================
async def main():
    TOKEN = os.environ.get('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing!")
        return

    port = int(os.environ.get("PORT", 5000))
    config = Quart.make_config(app)
    config.bind = [f"0.0.0.0:{port}"]
    
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host="0.0.0.0", port=port)
    )

if __name__ == "__main__":
    asyncio.run(main())
