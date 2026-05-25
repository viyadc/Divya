import discord
from discord.ext import commands
import asyncio
import random
import time
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

bot = commands.Bot(command_prefix="!", self_bot=True, help_command=None)

ai_enabled = True
user_memories = {}
active_sessions = {}
message_queue = {}
SESSION_TIMEOUT = 300

# OWO Bot ID
OWO_BOT_ID = 408785106942164992
POKETWO_BOT_ID = 716390085896962058

# Per-user unique personality profiles
user_profiles = {}

def get_user_profile(user_id):
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "tone": random.choice(["sarcastic", "friendly", "shy", "playful", "chill"]),
            "typo_rate": random.uniform(0.05, 0.18),
            "reply_chance": random.uniform(0.75, 1.0),  # kuch users ko thoda kam reply
            "nickname": None,
        }
    return user_profiles[user_id]

def add_typos(text, rate=0.1):
    """Realistic human typos add karo"""
    words = text.split()
    result = []
    for word in words:
        r = random.random()
        if r < rate and len(word) > 3:
            choice = random.randint(0, 2)
            if choice == 0:
                # swap adjacent letters
                i = random.randint(0, len(word) - 2)
                w = list(word)
                w[i], w[i+1] = w[i+1], w[i]
                result.append("".join(w))
            elif choice == 1:
                # double a letter
                i = random.randint(0, len(word) - 1)
                result.append(word[:i] + word[i] + word[i:])
            else:
                # miss a letter
                i = random.randint(1, len(word) - 1)
                result.append(word[:i] + word[i+1:])
        else:
            result.append(word)
    return " ".join(result)

def human_lowercase(text):
    """Kabhi kabhi capital letter reh jaata hai humans mein"""
    words = text.split()
    result = []
    for word in words:
        if random.random() < 0.03:  # 3% chance word capital ho
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)

def split_message_naturally(text):
    """Kabhi kabhi 2 parts mein bhejti hai - real lagta hai"""
    if len(text) > 40 and random.random() < 0.2:
        mid = len(text) // 2
        split_at = text.rfind(' ', 0, mid)
        if split_at > 0:
            return [text[:split_at], text[split_at+1:]]
    return [text]

@bot.event
async def on_ready():
    print(f'Divya online! 🔥')

@bot.event
async def on_message(message):
    global ai_enabled

    if message.author.bot:
        # OWO / Poketwo k saath interact karo
        if message.author.id == OWO_BOT_ID and random.random() < 0.35:
            await asyncio.sleep(random.uniform(2.0, 6.0))
            owo_replies = ["owo", "omg", "lucky lol", "ye mera tha 😤", "nice catch", "bruh", "haha"]
            await message.channel.send(random.choice(owo_replies))
        elif message.author.id == POKETWO_BOT_ID and random.random() < 0.25:
            await asyncio.sleep(random.uniform(3.0, 7.0))
            poke_replies = ["catch kar", "ye rare hai kya", "mujhe bhi chahiye tha", "ugh missed"]
            await message.channel.send(random.choice(poke_replies))
        return

    if message.mention_everyone: return
    if len(message.content) < 2: return
    if message.content.startswith(('!', '.', '?', '/', '$', '@')): return
    if "http" in message.content.lower() or "discord.gg" in message.content.lower(): return

    if message.author.id == bot.user.id:
        await bot.process_commands(message)
        if message.channel.id in message_queue:
            message_queue[message.channel.id] = []
        return

    channel_id = message.channel.id
    current_time = time.time()
    user_id = message.author.id
    profile = get_user_profile(user_id)

    is_triggered = bot.user.mentioned_in(message) or (
        channel_id in active_sessions and
        (current_time - active_sessions[channel_id]) < SESSION_TIMEOUT
    )

    if not (ai_enabled and is_triggered):
        return

    # Kabhi kabhi ignore karo (human behavior) - except mentions
    if not bot.user.mentioned_in(message):
        if random.random() > profile["reply_chance"]:
            # Sirf react karo, reply nahi
            if random.random() < 0.3:
                await asyncio.sleep(random.uniform(1.0, 3.0))
                reactions = ["😭", "💀", "😭", "lol", "fr", "💀"]
                try:
                    await message.add_reaction(random.choice(["😭", "💀", "😂", "👀"]))
                except:
                    pass
            return

    active_sessions[channel_id] = current_time

    if channel_id not in message_queue:
        message_queue[channel_id] = []
    message_queue[channel_id].append(message.content)

    await asyncio.sleep(6)

    if len(message_queue[channel_id]) == 0:
        return

    full_user_input = " ".join(message_queue[channel_id])
    message_queue[channel_id] = []

    if user_id not in user_memories:
        user_memories[user_id] = []

    tone_map = {
        "sarcastic": "thodi sarcastic, witty replies deti hai",
        "friendly": "bahut friendly aur warm rehti hai",
        "shy": "thodi hesitant, kam words mein bolti hai",
        "playful": "playful aur teasing style hai",
        "chill": "super chill, kuch bhi zyada nahi karti",
    }
    tone_desc = tone_map.get(profile["tone"], "friendly")

    instruction = f"""You are Divya, a 21 year old Indian girl on a Discord server.
1. Language: Natural Hinglish (Hindi+English mix). No forced slangs.
2. Style: {tone_desc}. 1-2 lines max. No formal closings.
3. Persona: Smart but casual. Serious sawaal ka seedha jawab. No "As an AI" ever.
4. Emojis: 0-1 max. No sparkles or bot-like emojis.
5. No proactive help. Don't offer assistance randomly.
6. If only a number is typed, type the next number.
7. Never sound like a bot or assistant."""

    messages_to_send = [{"role": "system", "content": instruction}]
    for hist in user_memories[user_id][-3:]:
        messages_to_send.append(hist)
    messages_to_send.append({"role": "user", "content": full_user_input})

    try:
        # Human-like thinking pause (message length pe based)
        base_delay = len(full_user_input) * random.uniform(0.04, 0.12)
        think_time = min(max(base_delay, 2.0), 10.0)
        await asyncio.sleep(think_time)

        chat_completion = groq_client.chat.completions.create(
            messages=messages_to_send,
            model="llama-3.3-70b-versatile",
            max_tokens=50,
            temperature=0.85,
            presence_penalty=0.8,
            frequency_penalty=0.5
        )
        raw_reply = chat_completion.choices[0].message.content

        # Clean up
        clean_reply = re.sub(r'[.,!/\\;:]', '', raw_reply)

        # Human typos + lowercase
        typo_reply = add_typos(clean_reply, rate=profile["typo_rate"])
        final_reply = human_lowercase(typo_reply).strip()

        # Natural message split (kabhi kabhi)
        parts = split_message_naturally(final_reply)

        async with message.channel.typing():
            typing_time = len(final_reply) * random.uniform(0.08, 0.15)
            await asyncio.sleep(min(typing_time, 8.0))

        for i, part in enumerate(parts):
            if i > 0:
                await asyncio.sleep(random.uniform(1.0, 2.5))
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(1.0, 3.0))
            await message.channel.send(part)

        user_memories[user_id].append({"role": "user", "content": full_user_input})
        user_memories[user_id].append({"role": "assistant", "content": final_reply})

        # Memory cap
        if len(user_memories[user_id]) > 20:
            user_memories[user_id] = user_memories[user_id][-20:]

    except Exception as e:
        print(f"Error: {e}")

keep_alive()
bot.run(USER_TOKEN)
