import os
import threading

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, jsonify, request


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")

GUILD_ID = 1569767222765949050
GUILD = discord.Object(id=GUILD_ID)

RULES = {
    1: (
        "Kunnioitetaan kaikkia jäseniä. Kiusaaminen, rasismi ja haukkuminen "
        "johtavat varoitukseen ja myöhemmin mahdollisesti killasta erottamiseen."
    ),
    2: "Apujohtajien ja johtajien sana on laki.",
    3: (
        "Kaikissa killan sodissa ja muussa killan toiminnassa noudatetaan myös "
        "Realmin omia sääntöjä: [Säännöt » Realmi]"
        "(https://share.google/iQnihghegANAma6ww)."
    ),
    4: (
        "Apujohtajat on valittu, eikä heitä enää oteta. Luotetun roolin voi "
        "saada, jos osoitat hyvää käytöstä killassa."
    ),
}

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
    description = "\\n\\n".join(
        f"**{number}.** {rule}" for number, rule in RULES.items()
    )
    embed = discord.Embed(
        title="📜 Kultagolemin säännöt",
        description=description,
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Kultagolem • Noudata sääntöjä ja kunnioita muita")
    return embed


def create_single_rule_embed(number: int):
    embed = discord.Embed(
        title=f"📜 Kultagolemin sääntö {number}",
        description=f"**{number}.** {RULES[number]}",
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Kultagolem • Noudata sääntöjä ja kunnioita muita")
    return embed


async def send_rules(channel):
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        raise RuntimeError("Komento pitää suorittaa tekstikanavalla.")
    return await channel.send(embed=create_rules_embed())


async def send_single_rule(channel, number: int):
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        raise RuntimeError("Komento pitää suorittaa tekstikanavalla.")
    return await channel.send(embed=create_single_rule_embed(number))


@bot.event
async def on_ready():
    if not getattr(bot, "commands_synced", False):
        try:
            # Both application commands are registered directly to this guild.
            synced = await bot.tree.sync(guild=GUILD)
            bot.commands_synced = True
            print(
                f"Synced {len(synced)} guild slash command(s) to guild {GUILD_ID}: "
                f"{', '.join(command.name for command in synced)}",
                flush=True,
            )
        except Exception as exc:
            print(f"Slash command sync failed: {type(exc).__name__}: {exc}", flush=True)

    print(f"Kultagolem is online as {bot.user} (ID: {bot.user.id})", flush=True)


@bot.event
async def on_disconnect():
    print("Disconnected from Discord; discord.py will attempt to reconnect.", flush=True)


@bot.command(name="säännöt", aliases=["saannot"])
@commands.guild_only()
async def rules_prefix(ctx):
    try:
        await send_rules(ctx.channel)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException, RuntimeError) as exc:
        await ctx.reply("Sääntöjen näyttäminen tässä kanavassa epäonnistui. Tarkista botin kanavaoikeudet.")
        print(f"Could not send rules in invoking channel: {exc}", flush=True)


@bot.tree.command(name="saannot", description="Näytä kaikki killan säännöt tässä kanavassa.")
@app_commands.guilds(GUILD)
@app_commands.guild_only()
async def rules_slash(interaction: discord.Interaction):
    try:
        await send_rules(interaction.channel)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException, RuntimeError) as exc:
        await interaction.response.send_message(
            "Sääntöjen näyttäminen tässä kanavassa epäonnistui. Tarkista botin kanavaoikeudet.",
            ephemeral=True,
        )
        print(f"Could not send slash rules in invoking channel: {exc}", flush=True)
        return

    await interaction.response.send_message("Säännöt näytettiin tässä kanavassa.", ephemeral=True)


@bot.tree.command(name="saanto", description="Näytä valittu killan sääntö tässä kanavassa.")
@app_commands.guilds(GUILD)
@app_commands.guild_only()
@app_commands.describe(numero="Valitse säännön numero (1–4).")
@app_commands.choices(
    numero=[
        app_commands.Choice(name="1", value=1),
        app_commands.Choice(name="2", value=2),
        app_commands.Choice(name="3", value=3),
        app_commands.Choice(name="4", value=4),
    ]
)
async def single_rule_slash(
    interaction: discord.Interaction,
    numero: app_commands.Choice[int],
):
    try:
        await send_single_rule(interaction.channel, numero.value)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException, RuntimeError) as exc:
        await interaction.response.send_message(
            "Säännön näyttäminen tässä kanavassa epäonnistui. Tarkista botin kanavaoikeudet.",
            ephemeral=True,
        )
        print(f"Could not send slash rule {numero.value} in invoking channel: {exc}", flush=True)
        return

    await interaction.response.send_message(
        f"Sääntö {numero.value} näytettiin tässä kanavassa.",
        ephemeral=True,
    )


def make_rule_prefix_command(number: int):
    async def callback(ctx):
        try:
            await send_single_rule(ctx.channel, number)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException, RuntimeError) as exc:
            await ctx.reply("Säännön näyttäminen tässä kanavassa epäonnistui. Tarkista botin kanavaoikeudet.")
            print(f"Could not send prefix rule {number} in invoking channel: {exc}", flush=True)

    callback.__name__ = f"rule_{number}_prefix"
    callback.__doc__ = f"Näytä killan sääntö {number} tässä kanavassa."
    return callback


for rule_number in range(1, 5):
    bot.command(
        name=f"sääntö{rule_number}",
        help=f"Näytä killan sääntö {rule_number} tässä kanavassa.",
    )(make_rule_prefix_command(rule_number))


if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN, log_handler=None)
