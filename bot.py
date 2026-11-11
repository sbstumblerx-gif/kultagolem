import os
import threading

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, jsonify, request


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")

# The rules are always published in this channel.
GUILD_ID = 1569767222765949050
RULES_CHANNEL_ID = 1569769165458374726

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
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, case_insensitive=True)


def create_rules_embed():
    embed = discord.Embed(
        title="📜 Kultagolemin säännöt",
        description=(
            "**1. Kunnioitetaan kaikkia jäseniä.** Kiusaaminen, rasismi ja "
            "haukkuminen johtavat varoitukseen ja myöhemmin mahdollisesti "
            "killasta erottamiseen.\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**2. Apujohtajien ja johtajien sana on laki.**\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**3.** Kaikissa killan sodissa ja muussa killan toiminnassa "
            "noudatetaan myös Realmin omia sääntöjä: "
            "[Säännöt » Realmi](https://share.google/iQnihghegANAma6ww).\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**4.** Apujohtajat on valittu, eikä heitä enää oteta. "
            "Luotetun roolin voi saada, jos osoitat hyvää käytöstä killassa."
        ),
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Kultagolem • Noudata sääntöjä ja kunnioita muita")
    return embed


async def publish_rules():
    channel = bot.get_channel(RULES_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(RULES_CHANNEL_ID)

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        raise RuntimeError("Rules channel is not a text channel.")

    return await channel.send(embed=create_rules_embed())


@bot.event
async def setup_hook():
    # Register the application command directly to this server.
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f"Synced {len(synced)} slash command(s) to guild {GUILD_ID}.", flush=True)


@bot.event
async def on_ready():
    print(f"Kultagolem is online as {bot.user} (ID: {bot.user.id})", flush=True)


@bot.event
async def on_disconnect():
    print("Disconnected from Discord; discord.py will attempt to reconnect.", flush=True)


@bot.command(name="säännöt", aliases=["saannot"])
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def rules_prefix(ctx):
    """Publish the guild rules in the designated rules channel."""
    try:
        message = await publish_rules()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException) as exc:
        await ctx.reply("Sääntöviestin lähettäminen epäonnistui. Tarkista botin kanavaoikeudet.")
        print(f"Could not publish rules: {exc}", flush=True)
        return

    await ctx.reply(f"Säännöt julkaistu: {message.jump_url}", mention_author=False)


@bot.tree.command(name="saannot", description="Julkaise killan säännöt sääntökanavalle.")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def rules_slash(interaction: discord.Interaction):
    try:
        message = await publish_rules()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException) as exc:
        await interaction.response.send_message(
            "Sääntöviestin lähettäminen epäonnistui. Tarkista botin kanavaoikeudet.",
            ephemeral=True,
        )
        print(f"Could not publish rules: {exc}", flush=True)
        return

    await interaction.response.send_message(
        f"Säännöt julkaistu: {message.jump_url}",
        ephemeral=True,
    )


if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN, log_handler=None)
