import os
import sys

import discord
from discord.ext import commands


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Kultagolem is online as {bot.user} (ID: {bot.user.id})", flush=True)


@bot.event
async def on_disconnect():
    print("Disconnected from Discord; discord.py will attempt to reconnect.", flush=True)


if __name__ == "__main__":
    bot.run(TOKEN, log_handler=None)
