import os
import json
import requests
import discord
from discord.ext import commands

# ⚙️ Firebase Realtime Database URL
FIREBASE_BASE_URL = 'https://uid-whitelist-default-rtdb.firebaseio.com'

# ডিসকর্ড বটের ইন্টেন্ট সেটিংস
intents = discord.Intents.default()
intents.message_content = True

# বটের কমান্ড প্রিফিক্স সেট করা
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print("==============================================")
    print(f"Logged in successfully as: {bot.user.name}")
    print("Firebase Realtime Database Connected!")
    print("==============================================")


@bot.command(name='free')
async def free_whitelist(ctx, uid: str = None):
    """ইউজারদের UID ফ্রিতে হোয়াইটলিস্ট করার কমান্ড"""
    
    # ১. UID মিসিং থাকলে এরর
    if uid is None:
        embed_error = discord.Embed(
            title="❌ ভুল ফরম্যাট!",
            description="দয়া করে কমান্ডটির সাথে আপনার সঠিক UID দিন।\n\n**সঠিক নিয়ম:**\n`!free <আপনার_UID>`\n\n*উদাহরণ:* `!free 8378790602`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_error)
        return

    # ২. UID ভ্যালিডেশন চেক (৮ থেকে ১২ ডিজিটের সংখ্যা)
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
        # ৩. ডাটাবেজে অলরেডি এই UID আছে কিনা চেক
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

        # ৪. নতুন ইউজারের ডাটা রেডি করা
        user_data = {
            "discord_name": str(ctx.author.name),
            "discord_id": str(ctx.author.id),
            "status": "active"
        }
        
        # ৫. Firebase-এ ডেটা সেভ করা
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
        await ctx.send("❌ সিস্টেমের কোনো একটি সমস্যা হয়েছে। দয়া করে ওনারের সাথে যোগাযোগ করুন।")


# 🚀 বটের রান করার মেইন লজিক
if __name__ == "__main__":
    TOKEN = os.environ.get('DISCORD_TOKEN')
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: DISCORD_TOKEN missing!")
