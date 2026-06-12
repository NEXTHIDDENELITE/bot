import os
import json
import requests
import re
import secrets
from flask import Flask, request, Response, render_template_string, jsonify, redirect, url_for

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ⚙️ Firebase Realtime Database URL
FIREBASE_BASE_URL = 'https://uid-whitelist-default-rtdb.firebaseio.com'

# ==========================================
# 🌐 ১. ড্যাশবোর্ড এবং ফ্রন্ট-এন্ড (HTML UI)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SENSI-X Premium UID Control</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
        body { background: #0a0813; color: #fff; padding: 30px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 900px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid #1f1a3a; padding-bottom: 15px; }
        h1 { color: #00ffcc; font-size: 28px; text-transform: uppercase; letter-spacing: 2px; }
        .card { background: #120e2b; padding: 25px; border-radius: 12px; border: 1px solid #251f4f; margin-bottom: 25px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        h2 { color: #0099ff; font-size: 18px; margin-bottom: 15px; text-transform: uppercase; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .form-group { display: flex; flex-direction: column; margin-bottom: 15px; }
        label { font-size: 12px; color: #aaa; margin-bottom: 5px; text-transform: uppercase; font-weight: bold; }
        input, select { padding: 12px; background: #1a153a; border: 1px solid #362e6e; border-radius: 6px; color: #fff; font-size: 15px; }
        input:focus { border-color: #00ffcc; outline: none; }
        .btn { padding: 12px 20px; background: linear-gradient(45deg, #00ffcc, #0099ff); border: none; border-radius: 6px; color: #000; font-weight: bold; cursor: pointer; text-transform: uppercase; transition: 0.3s; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,255,204,0.3); }
        .btn-danger { background: linear-gradient(45deg, #ff0055, #ff5500); color: #fff; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #251f4f; }
        th { background: #1a153a; color: #00ffcc; font-size: 13px; text-transform: uppercase; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-active { background: rgba(0, 255, 100, 0.2); color: #00ff64; border: 1px solid #00ff64; }
        .api-key { font-family: monospace; color: #ffcc00; background: #1a153a; padding: 2px 6px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SENSI-X API Control</h1>
            <div><span style="color:#aaa;">Role:</span> <span class="badge badge-active">ADMIN PANEL</span></div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Create New Reseller</h2>
                <form action="/admin/create-reseller" method="POST">
                    <div class="form-group">
                        <label>Reseller Username</label>
                        <input type="text" name="username" placeholder="e.g. nirob" required>
                    </div>
                    <div class="form-group">
                        <label>UID Limit</label>
                        <input type="number" name="limit" placeholder="e.g. 1000" required>
                    </div>
                    <button type="submit" class="btn">Generate Reseller 🚀</button>
                </form>
            </div>

            <div class="card">
                <h2>Direct UID Whitelist</h2>
                <form action="/admin/whitelist" method="POST">
                    <div class="form-group">
                        <label>Player UID</label>
                        <input type="text" name="uid" placeholder="e.g. 1596041192" required>
                    </div>
                    <div class="form-group">
                        <label>Assign to Reseller</label>
                        <select name="reseller">
                            <option value="Admin">Admin (Direct)</option>
                            {% for r_name in resellers_list %}
                                <option value="{{ r_name }}">{{ r_name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" class="btn">Add Player 🟢</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h2>Reseller & API Management</h2>
            <table>
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>API Key</th>
                        <th>UID Limit</th>
                        <th>Used</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for name, data in resellers.items() %}
                    <tr>
                        <td><strong>{{ name }}</strong></td>
                        <td><span class="api-key">{{ data.api_key }}</span></td>
                        <td>{{ data.uid_limit }}</td>
                        <td>{{ data.used }}</td>
                        <td><span class="badge badge-active">Active</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# ⚙️ ২. রাউটার এবং ব্যাকএন্ড লজিক
# ==========================================

@app.route('/')
def admin_dashboard():
    # ফায়ারবেস থেকে রিসেলারদের ডাটা নিয়ে আসা
    resellers = {}
    try:
        r = requests.get(f"{FIREBASE_BASE_URL}/resellers.json")
        if r.status_code == 200 and r.json():
            resellers = r.json()
    except:
        pass
    
    return render_template_string(HTML_TEMPLATE, resellers=resellers, resellers_list=resellers.keys())

# রিসেলার ক্রিয়েট করার এন্ডপয়েন্ট
@app.route('/admin/create-reseller', methods=['POST'])
def create_reseller():
    username = request.form.get('username').strip().lower()
    limit = int(request.form.get('limit', 0))
    
    if username:
        # একটি কাস্টম এবং সিকিউর API Key জেনারেট করা
        api_key = f"sensi_x_{secrets.token_hex(6)}"
        reseller_data = {
            "api_key": api_key,
            "uid_limit": limit,
            "used": 0,
            "status": "active"
        }
        # ফায়ারবেসে সেভ করা
        requests.put(f"{FIREBASE_BASE_URL}/resellers/{username}.json", data=json.dumps(reseller_data))
        
    return redirect(url_for('admin_dashboard'))

# অ্যাডমিন প্যানেল থেকে সরাসরি হোয়াইটলিস্ট করা
@app.route('/admin/whitelist', methods=['POST'])
def admin_whitelist():
    uid = request.form.get('uid').strip()
    reseller = request.form.get('reseller', 'Admin')
    
    if uid.isdigit():
        uid_data = {
            "status": "active",
            "added_by": reseller
        }
        requests.put(f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json", data=json.dumps(uid_data))
        
        # যদি রিসেলারের আন্ডারে এড হয় তবে তার 'used' কাউন্ট বাড়ানো
        if reseller != 'Admin':
            r = requests.get(f"{FIREBASE_BASE_URL}/resellers/{reseller}/used.json")
            current_used = r.json() if r.status_code == 200 and r.json() else 0
            requests.put(f"{FIREBASE_BASE_URL}/resellers/{reseller}/used.json", data=str(current_used + 1))
            
    return redirect(url_for('admin_dashboard'))

# ==========================================
# 🔌 ৩. থার্ড পার্টি এপিআই (রিসেলারদের ব্যবহারের জন্য)
# ==========================================
@app.route('/api/v1/add_uid', methods=['POST'])
def api_add_uid():
    data = request.get_json(silent=True) or request.form
    api_key = data.get('api_key')
    uid = str(data.get('uid', '')).strip()
    
    if not api_key or not uid:
        return jsonify({"status": "error", "message": "Missing API Key or UID"}), 400
        
    # ১. এপিআই কি ভেরিফাই করা এবং রিসেলার খুঁজে বের করা
    resellers_r = requests.get(f"{FIREBASE_BASE_URL}/resellers.json").json()
    target_reseller = None
    
    if resellers_r:
        for name, r_data in resellers_r.items():
            if r_data.get('api_key') == api_key:
                target_reseller = name
                reseller_info = r_data
                break
                
    if not target_reseller:
        return jsonify({"status": "error", "message": "Invalid API Key"}), 403
        
    # ২. লিমিট চেক করা
    if reseller_info['used'] >= reseller_info['uid_limit']:
        return jsonify({"status": "error", "message": "Reseller limit reached!"}), 400
        
    # ৩. হোয়াইটলিস্টে অ্যাড করা
    uid_data = {"status": "active", "added_by": target_reseller}
    requests.put(f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json", data=json.dumps(uid_data))
    
    # ৪. কাউন্টার আপডেট
    requests.put(f"{FIREBASE_BASE_URL}/resellers/{target_reseller}/used.json", data=str(reseller_info['used'] + 1))
    
    return jsonify({"status": "success", "message": f"UID {uid} successfully whitelisted by {target_reseller}"}), 200

# ==========================================
# 🖥️ ৪. C# প্যানেল হ্যান্ডলার (গেম লগইন চেক)
# ==========================================
@app.route('/api/uidipport', methods=['GET', 'POST'])
def uid_ip_port():
    try:
        uid = request.args.get('uid') or request.form.get('uid')
        if not uid and request.is_json:
            uid = request.get_json(silent=True).get('uid')
            
        if not uid and request.data:
            raw_body = request.data.decode('utf-8', errors='ignore').strip()
            match = re.search(r'\b\d{8,12}\b', raw_body)
            if match: uid = match.group(0)

        if not uid: 
            return Response("UID missing", status=400, mimetype='text/plain')

        # ফায়ারবেস থেকে ভেরিফাই করা
        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)

        if response.status_code == 200 and response.json() is not None:
            if response.json().get("status") == "active":
                # তোমার গেমিং বাইপাস আইপি ও পোর্ট
                return Response("168.144.97.15:1905", status=200, mimetype='text/plain')

        return Response("Unauthorized UID", status=403, mimetype='text/plain')
    except Exception as e: 
        return Response(str(e), status=500, mimetype='text/plain')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
