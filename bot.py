import os
import json
import requests
import discord
from discord.ext import commands
from flask import Flask, request, Response
from threading import Thread

# ⚙️ Firebase Realtime Database URL
FIREBASE_BASE_URL = 'https://uid-whitelist-default-rtdb.firebaseio.com'

# ডিসকর্ড বট সেটিংস
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ফ্লাস্ক ওয়েব সার্ভার সেটিংস
app = Flask(__name__)

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

@app.route('/')
def home():
    return "Server is Running Active!", 200

# ১. আইপি এবং পোর্ট রেসপন্স এন্ডপয়েন্ট
@app.route('/api/uidipport', methods=['GET', 'POST'])
def uid_ip_port():
    try:
        uid = request.args.get('uid')
        if not uid and request.method == 'POST':
            if request.is_json:
                uid = request.get_json(silent=True).get('uid')
            else:
                uid = request.form.get('uid')

        if not uid:
            return Response("UID missing", status=400, mimetype='text/plain')

        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)

        if response.status_code == 200 and response.json() is not None:
            db_data = response.json()
            if db_data.get("status") == "active":
                return Response("168.144.97.15:1905", status=200, mimetype='text/plain')

        return Response("Unauthorized UID", status=403, mimetype='text/plain')

    except Exception as e:
        return Response(str(e), status=500, mimetype='text/plain')

# ২. নতুন সার্টিফিকেট রেসপন্স এন্ডপয়েন্ট (তোমার দেওয়া নতুন মিটএমপ্রক্সি সার্টিফিকেট)
@app.route('/api/certificate', methods=['GET', 'POST'])
def get_certificate():
    cert_data = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIDNTCCAh2gAwIBAgIUX2m1TmLS4GfVMHdzMQgwmScgpdIwDQYJKoZIhvcNAQEL\n"
        "BQAwKDESMBAGA1UEAwwJbWl0bXByb3h5MRIwEAYDVQQKDAltaXRtcHJveHkwHhcN\n"
        "MjYwMTAyMDgwOTE2WhcNMzYwMTAyMDgwOTE2WjAoMRIwEAYDVQQDDAltaXRtcHJv\n"
        "eHkxEjAQBgNVBAoMCW1pdG1wcm94eTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCC\n"
        "AQoCggEBALSE/CFt4FOmr4RvvdgdzbP5cVT4m1rDDcHLRYUweDIIaLIHfT15xPVA\n"
        "9uShdE14J4c9jethHY9UVqypTkEBL0+Yxui0bzflrPRqU42fRtXcDS3Z9tx9kotO\n"
        "bD+kLLqZam7xCCCOawsEXx5V0vicxo7ar8Tj/nC/8Yfnswu5idJi35Ycbx9vnUER\n"
        "2t1n7Jol1Rea0Oat+JljMqJVEh4GJWh7tWR23r99UXYJH/ya4PFMZHnP92F5SUCs\n"
        "AdDWYgbYeZl2ww9iwKPcd+BQO/w/2ePjwN6jfS7QkDyV1DG6e8QtOoBONJx50WQR/\n"
        "Vstr+bkvTUwfBIpdrjVO6a8J555HiacCAwEAAaNXMFUwDwYDVR0TAQH/BAUwAwEB\n"
        "/zATBgNVHSUEDDAKBggrBgEFBQcDATAOBgNVHQ8BAf8EBAMCAQYwHQYDVR0OBBYE\n"
        "FCFEVpgJGAJPk0Hr69NGn602BW4SMA0GCSqGSIb3DQEBCwUAA4IBAQCZBAA7Yz/l\n"
        "G0SqJ9uAoQk4HFNpY+ymrELX2B6PObDZTJZL7MfafbLpr572o1xvYf1ghQZiy3SF\n"
        "Qo0CzlUvMAOtjqqocvM8NLMHnxQJRADQm8r/t7fov//+aeansi9hqw/STrvHs83j\n"
        "GRNKF4CaoAXoIJ5XJfv7OH4+mqJ1oBKquPVbNUasVCHFhXER+EC+kB0GCOjdodQo\n"
        "wzafnjnwjOps6iw+rqcIGCM2Qkv4mgT6TtxTcUEgFl+bKG3MuVBpJmVixJjQVHbs\n"
        "NFu4fgpa9HuoK6xr4f1il4yMBF6KmBYEnt98dMgVKpSt/APSE3tG7HoLglJP0ahS\n"
        "39WjEIjbNVo8\n"
        "-----END CERTIFICATE-----\n"
    )
    return Response(cert_data, status=200, mimetype='text/plain')

# ==========================================
# 🚀 সার্ভার এবং বট রান করার থ্রেড ফাংশন
# ==========================================
def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    TOKEN = os.environ.get('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing!")
    else:
        # ব্যাকগ্রাউন্ড থ্রেডে ফ্লাস্ক ওয়েব সার্ভার স্টার্ট করা
        server_thread = Thread(target=run_web_server)
        server_thread.daemon = True
        server_thread.start()
        
        # মেইন থ্রেডে ডিসকর্ড বট রান করা
        bot.run(TOKEN)
