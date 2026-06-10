import os
import json
import requests
import discord
import re
from discord.ext import commands
from flask import Flask, request, Response, render_template_string
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
# 🌐 ১. ওয়েবসাইট ড্যাশবোর্ড (HTML UI Part)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NHE PREMIUM BYPASS - Whitelist Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: #0f0c20; color: #fff; display: flex; justify-content: center; align-content: center; height: 100vh; padding: 20px; flex-direction: column; align-items: center; }
        .card { background: #151130; padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); border: 1px solid rgba(255, 255, 255, 0.1); width: 100%; max-width: 450px; text-align: center; }
        h1 { color: #00ffcc; font-size: 24px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
        p { color: #aaa; font-size: 14px; margin-bottom: 25px; }
        .input-group { margin-bottom: 20px; text-align: left; }
        label { display: block; margin-bottom: 8px; color: #00ffcc; font-size: 12px; font-weight: bold; text-transform: uppercase; }
        input[type="text"] { width: 100%; padding: 12px 15px; background: #1d183a; border: 1px solid #3d356b; border-radius: 8px; color: #fff; font-size: 16px; transition: 0.3s; text-align: center; letter-spacing: 2px; }
        input[type="text"]:focus { border-color: #00ffcc; outline: none; box-shadow: 0 0 10px rgba(0, 255, 204, 0.2); }
        .btn { width: 100%; padding: 14px; background: linear-gradient(45deg, #00ffcc, #0099ff); border: none; border-radius: 8px; color: #000; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s; text-transform: uppercase; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0, 255, 204, 0.4); }
        .message { margin-top: 20px; padding: 12px; border-radius: 8px; font-size: 14px; display: none; }
        .success { background: rgba(0, 255, 100, 0.15); border: 1px solid #00ff64; color: #00ff64; }
        .error { background: rgba(255, 0, 100, 0.15); border: 1px solid #ff0064; color: #ff0064; }
    </style>
</head>
<body>

    <div class="card">
        <h1>NHE PREMIUM</h1>
        <p>Enter Free Fire UID below to grant access</p>
        
        <form id="whitelistForm">
            <div class="input-group">
                <label for="uidInput">Player UID</label>
                <input type="text" id="uidInput" placeholder="e.g. 1596041192" required maxlength="12">
            </div>
            <button type="submit" class="btn">Add to Whitelist 🟢</button>
        </form>

        <div id="msgBox" class="message"></div>
    </div>

    <script>
        document.getElementById('whitelistForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const uid = document.getElementById('uidInput').value.trim();
            const msgBox = document.getElementById('msgBox');
            
            if(!/^\d{8,12}$/.test(uid)) {
                msgBox.className = "message error";
                msgBox.innerText = "❌ Invalid UID! Must be 8 to 12 digits.";
                msgBox.style.display = "block";
                return;
            }

            msgBox.className = "message";
            msgBox.style.display = "block";
            msgBox.style.background = "rgba(255,255,255,0.1)";
            msgBox.style.color = "#fff";
            msgBox.innerText = "⏳ Processing, please wait...";

            try {
                const response = await fetch('/api/webadd', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uid: uid })
                });
                const resText = await response.text();

                if(response.status === 200) {
                    msgBox.className = "message success";
                    msgBox.innerText = "✅ " + resText;
                } else {
                    msgBox.className = "message error";
                    msgBox.innerText = "❌ " + resText;
                }
            } catch (err) {
                msgBox.className = "message error";
                msgBox.innerText = "❌ Connection failed!";
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

# ওয়েবসাইট থেকে UID অ্যাড করার ব্যাকএন্ড এন্ডপয়েন্ট 🛠️
@app.route('/api/webadd', methods=['POST'])
def web_add_uid():
    try:
        data = request.get_json()
        if not data or 'uid' not in data:
            return "UID Missing", 400
        
        uid = str(data['uid']).strip()
        if not uid.isdigit() or len(uid) < 8 or len(uid) > 12:
            return "Invalid UID Format", 400

        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)
        
        if response.status_code == 200 and response.json() is not None:
            return f"UID {uid} is already whitelisted!", 200

        user_data = {"discord_name": "Web Dashboard", "discord_id": "0000", "status": "active"}
        save_response = requests.put(check_url, data=json.dumps(user_data))

        if save_response.status_code == 200:
            return f"UID {uid} successfully added to database!", 200
        else:
            return "Database insertion error", 500
    except Exception as e:
        return str(e), 500

# ==========================================
# 🤖 ২. ডিসকورد বট পার্ট (Bot Commands)
# ==========================================
@bot.event
async def on_ready():
    print("==============================================")
    print(f"Logged in successfully as: {bot.user.name}")
    print("==============================================")

@bot.command(name='free')
async def free_whitelist(ctx, uid: str = None):
    if uid is None:
        await ctx.send("❌ নিয়ম: `!free <UID>`")
        return
    try:
        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)
        if response.status_code == 200 and response.json() is not None:
            await ctx.send(f"⚠️ **UID {uid}** অলরেডি হোয়াইটলিস্ট করা আছে মামা!")
            return

        user_data = {"discord_name": str(ctx.author.name), "discord_id": str(ctx.author.id), "status": "active"}
        requests.put(check_url, data=json.dumps(user_data))
        await ctx.send(f"✅ **UID `{uid}`** সফলভাবে ডাটাবেজে যুক্ত করা হয়েছে।")
    except:
        await ctx.send("❌ সিস্টেম এরর।")

@bot.command(name='remove')
async def remove_whitelist(ctx, uid: str = None):
    if uid is None: return
    try:
        target_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        requests.delete(target_url)
        await ctx.send(f"🗑️ **UID `{uid}`** সফলভাবে মুছে ফেলা হয়েছে মামা!")
    except:
        await ctx.send("❌ ডিলিট করা যায়নি।")

# =======================================================
# 🌐 ৩. প্যানেল এপিআই পার্ট (C# Panel API Handler)
# =======================================================
@app.route('/api/uidipport', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def uid_ip_port():
    try:
        uid = None
        if request.args.get('uid'): uid = request.args.get('uid')
        elif request.is_json:
            json_data = request.get_json(silent=True)
            if json_data: uid = json_data.get('uid') or json_data.get('UID')
        elif request.form: uid = request.form.get('uid') or request.form.get('UID')
        
        if not uid and request.data:
            try:
                raw_body = request.data.decode('utf-8', errors='ignore').strip()
                if raw_body:
                    match = re.search(r'\b\d{8,12}\b', raw_body)
                    if match: uid = match.group(0)
                    elif '=' in raw_body:
                        potential_uid = raw_body.split('=')[-1].strip()
                        if potential_uid.isdigit(): uid = potential_uid
            except: pass

        if not uid:
            for key, value in request.headers.items():
                if 'uid' in key.lower(): uid = value; break

        if not uid: return Response("UID missing", status=400, mimetype='text/plain')

        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)

        if response.status_code == 200 and response.json() is not None:
            db_data = response.json()
            if db_data.get("status") == "active":
                return Response("168.144.97.15:1905", status=200, mimetype='text/plain')

        return Response("Unauthorized UID", status=403, mimetype='text/plain')
    except Exception as e:
        return Response(str(e), status=500, mimetype='text/plain')

@app.route('/api/certificate', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
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
