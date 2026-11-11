import os
import threading

import discord
from discord.ext import commands
from flask import Flask, jsonify, request


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")

web = Flask(__name__)


@web.get("/")
def health_check():
    return jsonify({"status": "ok", "service": "Kultagolem"}), 200


@web.post("/boot_request")
def boot_request():
    data = request.get_json(silent=True) or {}
    number = data.get("number")

    if not isinstance(number, int) or number < 1:
        return jsonify({"error": "A positive request number is required."}), 400

    message = f"#boot_request nro.{number}"
    print(message, flush=True)
    return jsonify({"status": "received", "message": message}), 200


def run_web_server():
    port = int(os.getenv("PORT", "10000"))
    web.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Kultagolem is online as {bot.user} (ID: {bot.user.id})", flush=True)


@bot.event
async def on_disconnect():
    print("Disconnected from Discord; discord.py will attempt to reconnect.", flush=True)


if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN, log_handler=None)
