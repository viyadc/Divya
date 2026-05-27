import discord
from discord.ext import commands
import asyncio
import random
import time
import aiohttp
from groq import Groq
import os
import re
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Divya is Awake!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

load_dotenv()
USER_TOKEN = os.getenv('USER_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
groq_client = Groq(api_key=GROQ_API_KEY)

bump_channels = set()

bot = commands.Bot(command_prefix="!", self_bot=True, help_command=None)

user_memories = {}
message_queue = {}
user_profiles = {}

def get_user_profile(user_id):
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "tone": random.choice(["sarcastic", "friendly", "shy", "playful", "chill"]),
            "typo_rate": random.uniform(0.05, 0.15),
        }
    return user_profiles[user_id]

def add_typos(text, rate=0.1):
    words = text.split()
    result = []
    for word in words:
        if random.random() < rate and len(word) > 3:
            choice = random.randint(0, 2)
            if choice == 0:
                i = random.randint(0, len(word) - 2)
                w = list(word)
                w[i], w[i+1] = w[i+1], w[i]
                result.append("".join(w))
            elif choice == 1:
                i = random.randint(0, len(word) - 1)
                result.append(word[:i] + word[i] + word[i:])
            else:
                i = random.randint(1, len(word) - 1)
                result.append(word[:i] + word[i+1:])
        else:
            result.append(word)
    return " ".join(result)

def human_lowercase(text):
    words = text.split()
    result = []
    for word in words:
        if random.random() < 0.03:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)

def split_message_naturally(text):
    if len(text) > 40 and random.random() < 0.2:
        mid = len(text) // 2
        split_at = text.rfind(' ', 0, mid)
        if split_at > 0:
            return [text[:split_at], text[split_at+1:]]
    return [text]

# ─── AUTO BUMP ────────────────────────────────────────────────────────────────

DISBOARD_BOT_ID = "302050872383242240"

async def bump_channel(channel):
    """Direct aiohttp se /bump slash command bhejta hai — 100% self-bot compatible."""
    nonce = str(int(time.time() * 1000))
    payload = {
        "type": 2,
        "application_id": DISBOARD_BOT_ID,
        "guild_id": str(channel.guild.id),
        "channel_id": str(channel.id),
        "session_id": bot._connection.session_id or "deadbeef",
        "data": {
            "version": "947088344167366698",
            "id": "947088344167366698",
            "name": "bump",
            "type": 1,
            "options": [],
            "application_command": {
                "id": "947088344167366698",
                "application_id": DISBOARD_BOT_ID,
                "name": "bump",
                "description": "Bump your server on DISBOARD!",
                "version": "947088344167366698",
                "type": 1,
                "options": []
            },
            "attachments": []
        },
        "nonce": nonce,
        "analytics_location": "slash_ui"
    }

    headers = {
        "Authorization": USER_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIn0=",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://discord.com/api/v10/interactions",
            json=payload,
            headers=headers
        ) as resp:
            if resp.status == 204:
                print(f"[Bump] /bump bheja -> #{channel.name} ({channel.guild.name}) OK")
                return True
            else:
                text = await resp.text()
                print(f"[Bump] Failed {resp.status}: {text}")
                return False

async def auto_bump():
    await bot.wait_until_ready()
    print("[Bump] Auto-bump loop shuru ho gaya.")
    while not bot.is_closed():
        if bump_channels:
            for ch_id in list(bump_channels):
                try:
                    channel = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                    await bump_channel(channel)
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"[Bump] Error channel {ch_id}: {e}")
        else:
            print("[Bump] Koi channel registered nahi hai.")
        await asyncio.sleep(7200)

# ─── BUMP COMMANDS ────────────────────────────────────────────────────────────

@bot.command(name="addbump")
async def add_bump(ctx, channel_id: int = None):
    if channel_id is None:
        await ctx.send("usage: !addbump <channel_id>")
        return
    bump_channels.add(channel_id)
    await ctx.send(f"✅ Channel {channel_id} bump list mein add ho gaya!")
    print(f"[Bump] Added channel: {channel_id}")

@bot.command(name="removebump")
async def remove_bump(ctx, channel_id: int = None):
    if channel_id is None:
        await ctx.send("usage: !removebump <channel_id>")
        return
    if channel_id in bump_channels:
        bump_channels.discard(channel_id)
        await ctx.send(f"🗑️ Channel {channel_id} remove ho gaya.")
    else:
        await ctx.send("❌ Yeh channel list mein tha hi nahi.")

@bot.command(name="listbumps")
async def list_bumps(ctx):
    if not bump_channels:
        await ctx.send("📋 Abhi koi bump channel registered nahi hai.")
        return
    lines = []
    for ch_id in bump_channels:
        ch = bot.get_channel(ch_id)
        if ch:
            lines.append(f"• #{ch.name} — {ch.guild.name} ({ch_id})")
        else:
            lines.append(f"• {ch_id} (fetch nahi hua)")
    await ctx.send("📋 Bump Channels:\n" + "\n".join(lines))

@bot.command(name="bumpnow")
async def bump_now(ctx):
    if not bump_channels:
        await ctx.send("❌ Koi channel nahi hai. Pehle !addbump karo.")
        return
    await ctx.send(f"🔄 {len(bump_channels)} channel(s) mein bump kar raha hoon...")
    for ch_id in list(bump_channels):
        try:
            channel = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
            success = await bump_channel(channel)
            if success:
                await ctx.send(f"✅ Bumped #{channel.name} ({channel.guild.name})")
            else:
                await ctx.send(f"❌ #{channel.name} bump fail hua — console dekho")
            await asyncio.sleep(3)
        except Exception as e:
            await ctx.send(f"❌ Channel {ch_id} error: {e}")

# ─────────────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f'Divya online!')
    bot.loop.create_task(auto_bump())

@bot.event
async def on_message(message):
    # Apne messages — commands process karo
    if message.author.id == bot.user.id:
        await bot.process_commands(message)
        return

    if message.author.bot:
        return
    if message.mention_everyone:
        return
    if len(message.content) < 2: return
    if message.content.startswith(('!', '.', '?', '/', '$', '@')): return
    if "http" in message.content.lower() or "discord.gg" in message.content.lower(): return

    if not bot.user.mentioned_in(message):
        return

    channel_id = message.channel.id
    user_id = message.author.id
    profile = get_user_profile(user_id)

    if channel_id not in message_queue:
        message_queue[channel_id] = []
    message_queue[channel_id].append(message.content)

    await asyncio.sleep(5)

    if len(message_queue[channel_id]) == 0:
        return

    full_user_input = " ".join(message_queue[channel_id])
    message_queue[channel_id] = []

    if user_id not in user_memories:
        user_memories[user_id] = []

    tone_map = {
        "sarcastic": "slightly sarcastic and witty",
        "friendly":  "warm and friendly",
        "shy":       "hesitant, fewer words",
        "playful":   "playful and teasing",
        "chill":     "very chill, unbothered",
    }
    tone_desc = tone_map.get(profile["tone"], "friendly")

    instruction = f"""You are Divya, 21yo Indian girl on Discord.
- Hinglish (Hindi+English), 1-2 lines only
- Tone: {tone_desc}
- No formal closings, no "As an AI", no assistant behavior
- 0-1 emoji max, no sparkles
- If only a number is typed, reply with the next number
- Sound like a real person texting, not a bot"""

    messages_to_send = [{"role": "system", "content": instruction}]
    for hist in user_memories[user_id][-4:]:
        messages_to_send.append(hist)
    messages_to_send.append({"role": "user", "content": full_user_input})

    try:
        base_delay = len(full_user_input) * random.uniform(0.04, 0.1)
        await asyncio.sleep(min(max(base_delay, 2.0), 8.0))

        chat_completion = groq_client.chat.completions.create(
            messages=messages_to_send,
            model="llama-3.3-70b-versatile",
            max_tokens=50,
            temperature=0.85,
            presence_penalty=0.8,
            frequency_penalty=0.5
        )
        raw_reply = chat_completion.choices[0].message.content

        clean_reply = re.sub(r'[.,!/\\;:]', '', raw_reply)
        typo_reply = add_typos(clean_reply, rate=profile["typo_rate"])
        final_reply = human_lowercase(typo_reply).strip()

        parts = split_message_naturally(final_reply)

        async with message.channel.typing():
            typing_time = len(final_reply) * random.uniform(0.08, 0.15)
            await asyncio.sleep(min(typing_time, 7.0))

        for i, part in enumerate(parts):
            if i > 0:
                await asyncio.sleep(random.uniform(1.0, 2.5))
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(1.0, 2.5))
            await message.channel.send(part)

        user_memories[user_id].append({"role": "user", "content": full_user_input})
        user_memories[user_id].append({"role": "assistant", "content": final_reply})

        if len(user_memories[user_id]) > 12:
            user_memories[user_id] = user_memories[user_id][-12:]

    except Exception as e:
        print(f"Error: {e}")

keep_alive()
bot.run(USER_TOKEN)
