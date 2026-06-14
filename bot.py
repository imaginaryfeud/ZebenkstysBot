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
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID", "0"))

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

RAID_ALARM_NAME = "RAID ALARM"

# ── Shared trigger handler ─────────────────────────────────────────────────────
async def handle_triggers(text, channel, mention, original_content):
    for phrase, response in TRIGGERS.items():
        if phrase in text.lower():
            if phrase == "under attack":
                await channel.send(
                    "@everyone " + response.format(
                        mention=mention,
                        content=original_content
                    )
                )
            else:
                await channel.send(f"@everyone, {response}")
            break

# ── Message listener ───────────────────────────────────────────────────────────
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.author.bot:
        print(f"Bot message from: '{message.author.display_name}'")
        print(f"Content: '{message.content}'")
        if message.embeds:
            for embed in message.embeds:
                print(f"Embed title: '{embed.title}'")
                print(f"Embed description: '{embed.description}'")
                print(f"Embed fields: {[f.value for f in embed.fields]}")
        else:
            print("No embeds found")

        if message.author.display_name == RAID_ALARM_NAME and message.embeds:
            for embed in message.embeds:
                embed_text = " ".join(filter(None, [
                    embed.title or "",
                    embed.description or "",
                ]))
                await handle_triggers(
                    embed_text,
                    message.channel,
                    message.author.mention,
                    embed.description or ""
                )
        return

    # Regular users — read message content
    await handle_triggers(
        message.content,
        message.channel,
        message.author.mention,
        message.content
    )

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
