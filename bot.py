import os
import json
import requests
import discord
from discord.ext import commands

# ⚙️ কনফিগারেশন এবং ডাটাবেজ লিংক
# তোমার স্ক্রিনশট অনুযায়ী মেইন Firebase URL এটি
FIREBASE_BASE_URL = 'https://uid-whitelist-default-rtdb.firebaseio.com'

# ডিসকর্ড বটের ইন্টেন্ট (Intents) সেটআপ করা
intents = discord.Intents.default()
intents.message_content = True  # মেসেজ রিড করার পারমিশন (বাধ্যতামূলক)

# বটের প্রিফিক্স সেট করা (যেমন: !free)
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print("==============================================")
    print(f"Logged in successfully as: {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print("Firebase Realtime Database Connect করা হয়েছে মামা!")
    print("==============================================")


@bot.command(name='free')
async def free_whitelist(ctx, uid: str = None):
    """ইউজারদের UID ফ্রিতে হোয়াইটলিস্ট করার মেইন কমান্ড"""
    
    # ১. ইউজার যদি শুধু !free লিখে কোনো UID না দেয়
    if uid is None:
        embed_error = discord.Embed(
            title="❌ ভুল ফরম্যাট!",
            description="দয়া করে কমান্ডটির সাথে আপনার সঠিক UID দিন মামা।\n\n**সঠিক নিয়ম:**\n`!free <আপনার_UID>`\n\n*উদাহরণ:* `!free 8378790602`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_error)
        return

    # ২. UID ভ্যালিডেশন চেক (শুধুমাত্র সংখ্যা হতে হবে এবং দৈর্ঘ্য ৮ থেকে ১২ ডিজিট)
    if not uid.isdigit() or len(uid) < 8 or len(uid) > 12:
        embed_invalid = discord.Embed(
            title="❌ অবৈধ UID!",
            description="আপনার দেওয়া UID-টি সঠিক নয়। Free Fire UID শুধুমাত্র সংখ্যায় ৮ থেকে ১২ ডিজিটের হয়ে থাকে।",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed_invalid)
        return

    # প্রসেসিং মেসেজ পাঠানো
    status_msg = await ctx.send("⏳ *ডাটাবেজ চেক করা হচ্ছে, দয়া করে একটু অপেক্ষা করুন...*")

    try:
        # ৩. চেক করা—এই UID টি অলরেডি ডাটাবেজে রেজিস্টার্ড আছে কিনা
        check_url = f"{FIREBASE_BASE_URL}/whitelisted_uids/{uid}.json"
        response = requests.get(check_url)
        
        if response.status_code == 200 and response.json() is not None:
            await status_msg.delete()  # আগের ওয়েটিং মেসেজটি ডিলিট করা
            
            embed_exist = discord.Embed(
                title="⚠️ অলরেডি রেজিস্টার্ড!",
                description=f"**UID {uid}** অলরেডি আমাদের ডাটাবেজে হোয়াইটলিস্ট করা আছে মামা! আপনি সরাসরি প্যানেলে লগইন করতে পারবেন।",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed_exist)
            return

        # ৪. নতুন ডাটা ফরম্যাট রেডি করা (ডিসকর্ড ট্র্যাকিং সহ)
        user_data = {
            "discord_name": f"{ctx.author.name}#{ctx.author.discriminator}" if ctx.author.discriminator != "0" else ctx.author.name,
            "discord_id": str(ctx.author.id),
            "status": "active"
        }
        
        # ৫. Firebase Database-এ নির্দিষ্ট UID কি (Key) হিসেবে ডাটা পুশ (PUT রিকোয়েস্ট) করা
        save_response = requests.put(check_url, data=json.dumps(user_data))

        # আগের ওয়েটিং মেসেজ ডিলিট
        await status_msg.delete()

        if save_response.status_code == 200:
            # সফলভাবে হোয়াইটলিস্ট হলে সুন্দর একটি এম্বেড মেসেজ পাঠানো
            embed_success = discord.Embed(
                title="✅ Whitelist Successful!",
                description="আপনার UID সফলভাবে প্যানেলের ডাটাবেজে যুক্ত করা হয়েছে।",
                color=discord.Color.green()
            )
            embed_success.add_field(name="Registered UID", value=f"`{uid}`", inline=False)
            embed_success.add_field(name="Authorized By", value=ctx.author.mention, inline=False)
            embed_success.add_field(name="Status", value="🟢 Active (Free Access)", inline=False)
            embed_success.set_thumbnail(url=ctx.author.display_avatar.url)
            embed_success.set_footer(text="NHE Premium Bypass • Powered by Firebase")
            
            await ctx.send(embed=embed_success)
        else:
            await ctx.send(f"❌ ডাটাবেজ এরর: সার্ভার কোড {save_response.status_code} দিয়েছে। ওনারের সাথে যোগাযোগ করুন।")

    except requests.exceptions.RequestException as e:
        print(f"Network Error: {e}")
        try: await status_msg.delete()
        except: pass
        await ctx.send("❌ ডাটাবেজ সার্ভারের সাথে কানেক্ট করা যাচ্ছে না। দয়া করে কিছুক্ষণ পর চেষ্টা করুন।")
    except Exception as e:
        print(f"Internal System Error: {e}")
        try: await status_msg.delete()
        except: pass
        await ctx.send("❌ কোনো একটি ইন্টারনাল সিস্টেম এরর হয়েছে। বটের কনসোল চেক করুন।")


# ========================================================
# 🚀 বটের রান করার মেইন লজিক (তোমার এনভায়রনমেন্ট ভেরিয়েবল মেথড)
# ========================================================
if __name__ == "__main__":
    TOKEN = os.environ.get('DISCORD_TOKEN')

    if TOKEN:
        bot.run(TOKEN)
    else:
        print("\n❌ ERROR: DISCORD_TOKEN missing!")
        print("দয়া করে আপনার অপারেটিং সিস্টেম বা হোস্টিং প্যানেলে 'DISCORD_TOKEN' এনভায়রনমেন্ট ভেরিয়েবলটি সেট করুন।")
        print("লোকাল পিসিতে টেস্ট করার জন্য সাময়িকভাবে নিচের লাইনটি ব্যবহার করতে পারেন:")
        print("bot.run('YOUR_ACTUAL_BOT_TOKEN_HERE')\n")
