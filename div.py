import discord
from discord.ext import commands
import asyncio
import random
import time
import aiohttp
import json
import os
import re
from groq import Groq
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

def log(msg):
    print(msg, flush=True)

load_dotenv()
USER_TOKEN = os.getenv('USER_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
groq_client = Groq(api_key=GROQ_API_KEY)

# ─── PERSISTENT BUMP CHANNELS ─────────────────────────────────────────────────

BUMP_FILE = "bump_channels.json"

def load_bump_channels():
    if os.path.exists(BUMP_FILE):
        with open(BUMP_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_bump_channels():
    with open(BUMP_FILE, "w") as f:
        json.dump(list(bump_channels), f)
    log(f"[Bump] Saved {len(bump_channels)} channel(s) to file.")

bump_channels = load_bump_channels()
log(f"[Bump] Loaded {len(bump_channels)} channel(s) from file: {bump_channels}")

# ─────────────────────────────────────────────────────────────────────────────

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

async def fetch_bump_command(guild_id):
    headers = {
        "Authorization": USER_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    url = f"https://discord.com/api/v10/guilds/{guild_id}/application-command-index"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                for app in data.get("application_commands", []):
                    if app.get("application_id") == DISBOARD_BOT_ID and app.get("name") == "bump":
                        log(f"[Bump] Found command -> id={app['id']} version={app.get('version')}")
                        return app["id"], app.get("version", app["id"])
            else:
                text = await resp.text()
                log(f"[Bump] fetch_bump_command failed {resp.status}: {text[:200]}")
    return None, None

async def bump_channel(channel):
    log(f"[Bump] Trying #{channel.name} ({channel.guild.name})...")
    cmd_id, cmd_version = await fetch_bump_command(str(channel.guild.id))
    if not cmd_id:
        log(f"[Bump] /bump command nahi mila — kya Disboard is server mein hai?")
        return False

    nonce = str(int(time.time() * 1000))
    payload = {
        "type": 2,
        "application_id": DISBOARD_BOT_ID,
        "guild_id": str(channel.guild.id),
        "channel_id": str(channel.id),
        "session_id": bot._connection.session_id or "abcdef1234567890",
        "data": {
            "version": cmd_version,
            "id": cmd_id,
            "name": "bump",
            "type": 1,
            "options": [],
            "application_command": {
                "id": cmd_id,
                "application_id": DISBOARD_BOT_ID,
                "name": "bump",
                "description": "Bump your server on DISBOARD!",
                "version": cmd_version,
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

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://discord.com/api/v10/interactions",
                json=payload,
                headers=headers
            ) as resp:
                status = resp.status
                text = await resp.text()
                if status == 204:
                    log(f"[Bump] SUCCESS -> #{channel.name} ({channel.guild.name})")
                    return True
                else:
                    log(f"[Bump] FAILED {status} -> {text[:300]}")
                    return False
    except Exception as e:
        log(f"[Bump] EXCEPTION: {type(e).__name__}: {e}")
        return False

async def do_bump_all():
    """Sabhi registered channels mein bump karta hai."""
    if not bump_channels:
        log("[Bump] Koi channel registered nahi hai.")
        return
    log(f"[Bump] Bumping {len(bump_channels)} channel(s)...")
    for ch_id in list(bump_channels):
        try:
            channel = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
            await bump_channel(channel)
            await asyncio.sleep(3)
        except Exception as e:
            log(f"[Bump] Error getting channel {ch_id}: {type(e).__name__}: {e}")

async def auto_bump():
    await bot.wait_until_ready()
    log(f"[Bump] Auto-bump loop shuru — {len(bump_channels)} channel(s) loaded.")
    while not bot.is_closed():
        await do_bump_all()
        log("[Bump] Next bump 2 ghante baad...")
        await asyncio.sleep(7200)

# ─── BUMP COMMANDS ────────────────────────────────────────────────────────────

@bot.command(name="addbump")
async def add_bump(ctx, channel_id: int = None):
    if channel_id is None:
        await ctx.send("usage: !addbump <channel_id>")
        return
    bump_channels.add(channel_id)
    save_bump_channels()
    await ctx.send(f"✅ Channel {channel_id} add ho gaya! Abhi bump kar raha hoon...")
    log(f"[Bump] Added & saved channel: {channel_id}")
    # Turant bump karo naye channel mein
    try:
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        success = await bump_channel(channel)
        if success:
            await ctx.send(f"✅ #{channel.name} bump ho gaya!")
        else:
            await ctx.send(f"❌ Bump fail hua — console dekho")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command(name="removebump")
async def remove_bump(ctx, channel_id: int = None):
    if channel_id is None:
        await ctx.send("usage: !removebump <channel_id>")
        return
    if channel_id in bump_channels:
        bump_channels.discard(channel_id)
        save_bump_channels()
        await ctx.send(f"🗑️ Channel {channel_id} remove ho gaya.")
    else:
        await ctx.send("❌ Yeh channel list mein tha hi nahi.")

@bot.command(name="listbumps")
async def list_bumps(ctx):
    if not bump_channels:
        await ctx.send("📋 Koi bump channel registered nahi hai.")
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
    await ctx.send(f"🔄 {len(bump_channels)} channel(s) bump ho raha hai...")
    for ch_id in list(bump_channels):
        try:
            channel = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
            success = await bump_channel(channel)
            if success:
                await ctx.send(f"✅ Bumped #{channel.name} ({channel.guild.name})")
            else:
                await ctx.send(f"❌ #{channel.name} fail — console dekho")
            await asyncio.sleep(3)
        except Exception as e:
            log(f"[Bump] bumpnow exception: {e}")
            await ctx.send(f"❌ Error: {e}")

# ─────────────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    log(f'Divya online!')
    bot.loop.create_task(auto_bump())

@bot.event
async def on_message(message):
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
        log(f"Error: {e}")

keep_alive()
bot.run(USER_TOKEN)
