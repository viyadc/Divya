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
active_servers = set()  # Ab ye sirf un servers ki ID rakhega jahan bot ON hai

@bot.event
async def on_ready():
    print(f'Divya is fixed! Ab sukoon se chat karo. 🔥')

@bot.command()
async def chalu(ctx):
    active_servers.add(ctx.guild.id)
    await ctx.send("Theek hai bhai, is server mein 'Divya' active hai! 🔥")

@bot.command()
async def bas(ctx):
    if ctx.guild.id in active_servers:
        active_servers.remove(ctx.guild.id)
    await ctx.send("Done! Is server mein ab main beech mein nahi padungi. 🤐")

@bot.event
async def on_message(message):
    global ai_enabled
    
    if message.author.bot: return

    # Commands check karne ke liye (important!)
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    if message.author.id == bot.user.id:
        if message.channel.id in message_queue:
            message_queue[message.channel.id] = []
        return

    # --- UPDATE: Trigger check with Server Filter ---
    channel_id = message.channel.id
    current_time = time.time()
    
    # Check ki is server mein tune !chalu kiya hai ya nahi
    is_server_active = message.guild and message.guild.id in active_servers

    if message.mention_everyone:
        return

    is_triggered = bot.user.mentioned_in(message) or (
        channel_id in active_sessions and 
        (current_time - active_sessions[channel_id]) < SESSION_TIMEOUT
    )

    # AI tabhi chalega jab server active ho aur trigger hua ho
    if ai_enabled and is_server_active and is_triggered:
        active_sessions[channel_id] = current_time
        
        if channel_id not in message_queue:
            message_queue[channel_id] = []
        
        message_queue[channel_id].append(message.content)
        
        # --- SMART WAIT (Increased to 6 seconds) ---
        await asyncio.sleep(6) 
        
        if len(message_queue[channel_id]) > 0:
            full_user_input = " ".join(message_queue[channel_id])
            message_queue[channel_id] = [] 
            
            user_id = message.author.id
            if user_id not in user_memories: user_memories[user_id] = []

            instruction = f"""You are Divya, a 21 years old indian girl. 
1. Language: Natural Hinglish (Mix of Hindi/English). No forced slangs.
2. Rule: Give logical, helpful, and sensible answers only, No Proactive Help. 
3. Style: Keep it very short (1 line). Chat like a normal Girl on discord channel, No Formal Closings. Feel the vibe, then reply.
4. Persona: Friendly but not stupid. If a question is serious, answer it simply. 
5. No AI behavior: Don't say "As an AI" or "I'm here to help.
# Emojis: Use rarely (1-2 max), No bot-like sparkles.
# if user type only digit(1,2,3 and so on) then type next digit"""

            messages_to_send = [{"role": "system", "content": instruction}]
            for hist in user_memories[user_id][-5:]:
                messages_to_send.append(hist)
            messages_to_send.append({"role": "user", "content": full_user_input})

            try:
                # --- EXTRA THINKING PAUSE (Before Typing) ---
                await asyncio.sleep(random.uniform(3.0, 5.0))

                chat_completion = groq_client.chat.completions.create(
                    messages=messages_to_send,
                    model="llama-3.3-70b-versatile",
                    max_tokens=80,
                    temperature=0.8,
                    presence_penalty=0.8,
                    frequency_penalty=0.5
                )
                raw_reply = chat_completion.choices[0].message.content

                # --- Final Human Touch: Regex & Lower ---
                clean_reply = re.sub(r'[.,!/\\;:]', '', raw_reply)
                final_reply = clean_reply.lower().strip()

                # Typing Effect
                async with message.channel.typing():
                    wait_time = len(final_reply) * 0.2
                    await asyncio.sleep(min(wait_time, 8.0))
                    await message.channel.send(final_reply)

                user_memories[user_id].append({"role": "user", "content": full_user_input})
                user_memories[user_id].append({"role": "assistant", "content": final_reply})

            except Exception as e:
                print(f"Error: {e}")
keep_alive()
bot.run(USER_TOKEN)
