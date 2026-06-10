import os
import json
import requests
import discord
from discord.ext import commands
from quart import Quart, request, Response
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

# ১. আইপি এবং পোর্ট রেসপন্স এন্ডপয়েন্ট (POST এবং GET দুটাই হ্যান্ডেল করবে)
@app.route('/api/uidipport', methods=['GET', 'POST'])
async def uid_ip_port():
    try:
        # প্যানেল থেকে পাঠানো UID গেট করা (C# যেভাবে রিকোয়েস্ট পাঠায় সে অনুযায়ী)
        uid = request.args.get('uid')
        if not uid:
            if request.method == 'POST':
                req_data = await request.get_json(silent=True) or await request.form
                uid = req_data.get('uid') if req_data else None

        if not uid:
            return Response("UID missing", status=400, mimetype='text/plain')

        # Firebase ডাটাবেজে এই UID-টি হোয়াইটলিস্টেড কিনা চেক করা
        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)

        if response.status_code == 200 and response.json() is not None:
            db_data = response.json()
            if db_data.get("status") == "active":
                # প্যানেলের রিকোয়েস্ট করা সেই হুবহু রেসপন্স ফরম্যাট
                return Response("168.144.97.15:1905", status=200, mimetype='text/plain')

        # হোয়াইটলিস্টেড না থাকলে খালি রেসপন্স বা এরর দেওয়া
        return Response("Unauthorized UID", status=403, mimetype='text/plain')

    except Exception as e:
        return Response(str(e), status=500, mimetype='text/plain')


# ২. সার্টিফিকেট রেসপন্স এন্ডপয়েন্ট (image_e320dd.png অনুযায়ী হুবহু PEM রেসপন্স)
@app.route('/api/certificate', methods=['GET', 'POST'])
async def get_certificate():
    cert_data = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIDNTCCAh2gAwIBAgIUd51MdSXNEYJ5hcaHqvZI2RzSHQYWDQYJKoZIhvcNAQEL\n"
        "BQAwKDESMBAGA1UEAwwJbW1oXbYb3h5MRIwEAYDVQQKDAl0aXtHjveHkwHhcN\n"
        "MjYwNDI0MTAwMjQWhcNMzYwNDI1MTAwMjAoMRIwEAYDVQQKDAl0aXtHjveHj\n"
        "eHkxEjAQBgNVBAMMC1pwdG1w94etTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCC\n"
        "AQoCggEBALZwx hZmEODKBNK5+4HseWqH8VAEbRzy3D5LB0iqFMoLOmHj/PzcHy0\n"
        "ilcg+xZ+yxaeqiYjdHfgC0z/XnVBi5h8xqJZc395DSskaFTOcuSH77XxWPuKIe2z\n"
        "NcWQMjIZ75SkX3QqnnwwxyigolehoQl3bTSscOpqZVqXOVPIvev9g8SRT+GG4+Qx\n"
        "7FtxPOF1Hw1kQt+PMW4yc8tHFSnGbLTfxOrmrW4Fvka1JFuV7gBd1pqnXMlFREG/\n"
        "ZNudP/qXv6LLjRvcgKL0Kmr55kwAn2atyr50VjNnJdlUBv6tFGYQiMs1Bgt3rTT0\n"
        "p+lTAjaZHrfcsoDIwn/nortvNJ4VcjMCAwEAAaNXMFUwDwYDVR0TAQH/BAUwAwEB\n"
        "/zATBgNVHSUEDDAKBggrBgEFBQcDATAOBgNVHQ8BAf8EBAMCAQYwHQYDVR0OBBYE\n"
        "FMnVuvmLj86XBNIEvowpXAqurv7bMA0GCSqGSIb3DQEBCwUAA4IBAQA0nJDV2h1O\n"
        "/Mq0QdDEcxzPC+8mhnoBLs0uZtML09/K16c/FhC10JAyldLTbJAgXTYmteYRFsR\n"
        "TtKLHxJ83rgXMXBmN1vT+Ls61LPk5WI8EOFKFYOMdj05Q9kztCynaqwL98xcVmka\n"
        "RjaZjBr/wJ3lurTMjCCFy9i8BkraspQJbSnfDPdNANHpZNXfSv8/IWJQ/pt9Q+j\n"
        "q+YmggaU3LWsZ5ZH1z/NcPDTndwEa/sUs4xkFOPA+DLXH3uKALLTorEaY8WNNLya\n"
        "3BUXFQzW7jqkQ/GSjZ3OFyceYzyXLKK386J81vzR92QSoesQFZWyUiSR4MWhNLRf\n"
        "Yghj7x8ARJup\n"
        "-----END CERTIFICATE-----\n"
    )
    return Response(cert_data, status=200, mimetype='text/plain')


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
