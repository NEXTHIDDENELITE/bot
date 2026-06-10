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

# ১. হোয়াইটলিস্টে UID যুক্ত করার কমান্ড
@bot.command(name='free')
async def free_whitelist(ctx, uid: str = None):
    if uid is None:
        embed_error = discord.Embed(
            title="❌ ভুল ফরম্যাট!",
            description="দয়া করে কমান্ডটির সাথে আপনার সঠিক UID দিন।\n\n**সঠিক নিয়ম:**\n`!free <আপনার_UID>`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_error)
        return

    if not uid.isdigit() or len(uid) < 8 or len(uid) > 12:
        embed_invalid = discord.Embed(
            title="❌ অবৈধ UID!",
            description="Free Fire UID শুধুমাত্র সংখ্যায় ৮ থেকে ১২ ডিজিটের হয়ে থাকে।",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_invalid)
        return

    status_msg = await ctx.send("⏳ *ডাটাবেজ চেক করা হচ্ছে...*")

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
                description=f"**UID `{uid}`** সফলভাবে ডাটাবেজে যুক্ত করা হয়েছে।",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed_success)
        else:
            await ctx.send(f"❌ ডাটাবেজ এরর এসেছে মামা।")

    except Exception as e:
        try: await status_msg.delete()
        except: pass
        await ctx.send("❌ সিস্টেমের কোনো একটি সমস্যা হয়েছে।")


# ২. হোয়াইটলিস্ট থেকে UID রিমুভ করার নতুন কমান্ড 🛠️
@bot.command(name='remove')
async def remove_whitelist(ctx, uid: str = None):
    if uid is None:
        embed_error = discord.Embed(
            title="❌ ভুল ফরম্যাট!",
            description="দয়া করে যে UID টি ডিলিট করতে চান সেটি দিন।\n\n**সঠিক নিয়ম:**\n`!remove <আপনার_UID>`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_error)
        return

    status_msg = await ctx.send("⏳ *ডাটাবেজ থেকে রিমুভ করা হচ্ছে...*")

    try:
        target_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        
        # প্রথমে চেক করা এই UID টি ডাটাবেজে আছে কিনা
        check_response = requests.get(target_url)
        
        if check_response.status_code == 200 and check_response.json() is None:
            await status_msg.delete()
            embed_not_found = discord.Embed(
                title="❌ UID পাওয়া যায়নি!",
                description=f"**UID `{uid}`** আমাদের ডাটাবেজে হোয়াইটলিস্ট করা নেই মামা।",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed_not_found)
            return

        # Firebase থেকে ডেটা ডিলিট করার জন্য DELETE রিকোয়েস্ট পাঠানো
        delete_response = requests.delete(target_url)
        await status_msg.delete()

        if delete_response.status_code == 200:
            embed_remove = discord.Embed(
                title="🗑️ Removed Successfully!",
                description=f"**UID `{uid}`** সফলভাবে হোয়াইটলিস্ট থেকে মুছে ফেলা হয়েছে মামা!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed_remove)
        else:
            await ctx.send("❌ ডাটাবেজ থেকে ডিলিট করা যায়নি।")

    except Exception as e:
        try: await status_msg.delete()
        except: pass
        await ctx.send("❌ সিস্টেম এরর! ওনারের সাথে যোগাযোগ করুন।")


# ==========================================
# 🌐 প্যানেল এপিআই পার্ট (C# Panel API Endpoints)
# ==========================================
@app.route('/')
def home():
    return "Server is Running Active!", 200

@app.route('/api/uidipport', methods=['GET', 'POST'])
def uid_ip_port():
    try:
        uid = None
        if request.args.get('uid'):
            uid = request.args.get('uid')
        elif request.is_json:
            json_data = request.get_json(silent=True)
            if json_data: uid = json_data.get('uid') or json_data.get('UID')
        elif request.form:
            uid = request.form.get('uid') or request.form.get('UID')
        if not uid and request.data:
            try:
                raw_data = request.data.decode('utf-8').strip()
                if raw_data.isdigit(): uid = raw_data
                else:
                    json_raw = json.loads(raw_data)
                    uid = json_raw.get('uid') or json_raw.get('UID')
            except: pass

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

def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    TOKEN = os.environ.get('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing!")
    else:
        server_thread = Thread(target=run_web_server)
        server_thread.daemon = True
        server_thread.start()
        bot.run(TOKEN)
