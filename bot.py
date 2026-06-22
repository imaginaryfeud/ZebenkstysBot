import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import a2s
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
DAYZ_SERVER_IP = os.getenv("DAYZ_SERVER_IP")
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID", "0"))

if not TOKEN:
    raise ValueError("TOKEN is not set")
if not SERVER_IP:
    raise ValueError("SERVER_IP is not set")
if not DAYZ_SERVER_IP:
    raise ValueError("DAYZ_SERVER_IP is not set")


def parse_host_port(value: str):
    """Splits 'host:port' into (host, port). DayZ query port has no
    universal default, so the env var must include it explicitly."""
    if ":" not in value:
        raise ValueError(
            f"Expected 'host:port' format, got '{value}'. "
            "DayZ's query port isn't standardized, so it must be included."
        )
    host, port = value.rsplit(":", 1)
    return host, int(port)


DAYZ_HOST, DAYZ_PORT = parse_host_port(DAYZ_SERVER_IP)

# ── Trigger phrases ────────────────────────────────────────────────────────────
TRIGGERS = {
    "under attack": "🚨 Mažučiai, jus reidina (◕‿◕) | Base is being raided ",
    "10%":          "Pakeiskit akumą | Change the battery",
    "connection lost": "Bazė nebestebima | Base is no longer being monitored",
}

SILENT_TRIGGERS = {"10%"}  # these won't ping @everyone

RAID_ALARM_NAME = "RAID ALARM"

# ── Shared trigger handler ─────────────────────────────────────────────────────
async def handle_triggers(text, channel, mention, original_content):
    for phrase, response in TRIGGERS.items():
        if phrase in text.lower():
            if phrase in SILENT_TRIGGERS:
                await channel.send(response)
            elif phrase == "under attack":
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

# ── Server status loop (Minecraft + DayZ) ──────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    update_status.start()

@tasks.loop(seconds=30)
async def update_status():
    print("Updating presence...")

    # Try Minecraft first
    try:
        server = JavaServer.lookup(SERVER_IP)
        status = await bot.loop.run_in_executor(None, server.status)
        players = f"{status.players.online}/{status.players.max}"
        version = status.version.name
        activity_text = f"🟩 MC {players} | {version}"
        await bot.change_presence(activity=discord.Game(name=activity_text[:128]))
        return
    except Exception as e:
        print(f"Minecraft offline: {e}")

    # Minecraft didn't respond — try DayZ
    try:
        info = await bot.loop.run_in_executor(
            None, a2s.info, (DAYZ_HOST, DAYZ_PORT)
        )
        players = f"{info.player_count}/{info.max_players}"
        activity_text = f"🟦 DayZ {players} | {info.map_name}"
        await bot.change_presence(activity=discord.Game(name=activity_text[:128]))
        return
    except Exception as e:
        print(f"DayZ offline: {e}")

    # Neither server responded
    await bot.change_presence(
        activity=discord.Game(name="🔴⊹ ࣪ ˖ ")
    )

@update_status.before_loop
async def before_update():
    await bot.wait_until_ready()

bot.run(TOKEN)
