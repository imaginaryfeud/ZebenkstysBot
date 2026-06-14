import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
from aiohttp import web
import asyncio
import os

# ── Intents setup ─────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ── Environment variables ──────────────────────────────────────────────────────
TOKEN = os.getenv("TOKEN")
SERVER_IP = os.getenv("SERVER_IP")
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID", "0"))  # channel to send @everyone

if not TOKEN:
    raise ValueError("TOKEN is not set")
if not SERVER_IP:
    raise ValueError("SERVER_IP is not set")

# ── Trigger phrases ────────────────────────────────────────────────────────────
TRIGGERS = {
    "under attack": "🚨 Mažučiai, jus reidina (◕‿◕)  {mention}: {content}",
    "10%":          "Pakeiskit akumą",
    "connection lost": "bazė nebestebima",
}

# ── Message listener ───────────────────────────────────────────────────────────
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content_lower = message.content.lower()

    for phrase, response in TRIGGERS.items():
        if phrase in content_lower:
            channel = message.channel
            if channel:
                if phrase == "under attack":
                    await channel.send(
                        f"@everyone " + response.format(
                            mention=message.author.mention,
                            content=message.content
                        )
                    )
                else:
                    await channel.send(f"@everyone, {response}")
            break  # only fire the first matching trigger

    await bot.process_commands(message)

# ── Minecraft status loop ──────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    update_status.start()

@tasks.loop(seconds=30)
async def update_status():
    print("Updating presence...")
    try:
        server = JavaServer.lookup(SERVER_IP)
        status = await bot.loop.run_in_executor(None, server.status)
        players = f"{status.players.online}/{status.players.max}"
        version = status.version.name
        activity_text = f"{players} | {version}"
        await bot.change_presence(
            activity=discord.Game(name=activity_text[:128])
        )
    except Exception as e:
        print(f"Error: {e}")
        await bot.change_presence(
            activity=discord.Game(name="🔴 Server Offline")
        )

@update_status.before_loop
async def before_update():
    await bot.wait_until_ready()

bot.run(TOKEN)
