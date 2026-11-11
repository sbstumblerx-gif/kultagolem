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
RULES_CHANNEL_ID = 1569769165458374726
RULES_CHANNEL_URL = "https://discord.com/channels/1569767222765949050/1569769165458374726"

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
    description = "\n\n".join(
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


async def publish_rules():
    channel = bot.get_channel(RULES_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(RULES_CHANNEL_ID)

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        raise RuntimeError("Rules channel is not a text channel.")

    return await channel.send(embed=create_rules_embed())


async def publish_single_rule(number: int):
    channel = bot.get_channel(RULES_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(RULES_CHANNEL_ID)

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        raise RuntimeError("Rules channel is not a text channel.")

    return await channel.send(
        content=f"[Avaa sääntökanava ja kaikki säännöt]({RULES_CHANNEL_URL})",
        embed=create_single_rule_embed(number),
    )


@bot.event
async def on_ready():
    if not getattr(bot, "commands_synced", False):
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        bot.commands_synced = True
        print(f"Synced {len(synced)} slash command(s) to guild {GUILD_ID}.", flush=True)

    print(f"Kultagolem is online as {bot.user} (ID: {bot.user.id})", flush=True)


@bot.event
async def on_disconnect():
    print("Disconnected from Discord; discord.py will attempt to reconnect.", flush=True)


@bot.command(name="säännöt", aliases=["saannot"])
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def rules_prefix(ctx):
    try:
        message = await publish_rules()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException) as exc:
        await ctx.reply("Sääntöviestin lähettäminen epäonnistui. Tarkista botin kanavaoikeudet.")
        print(f"Could not publish rules: {exc}", flush=True)
        return

    await ctx.reply(f"Säännöt julkaistu: {message.jump_url}", mention_author=False)


@bot.tree.command(name="saannot", description="Julkaise kaikki killan säännöt sääntökanavalle.")
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


@bot.tree.command(name="sääntö", description="Julkaise valittu killan sääntö.")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
@app_commands.describe(numero="Valitse julkaistavan säännön numero (1–4).")
@app_commands.choices(numero=[
    app_commands.Choice(name="1", value=1),
    app_commands.Choice(name="2", value=2),
    app_commands.Choice(name="3", value=3),
    app_commands.Choice(name="4", value=4),
])
async def single_rule_slash(
    interaction: discord.Interaction,
    numero: app_commands.Choice[int],
):
    try:
        message = await publish_single_rule(numero.value)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException) as exc:
        await interaction.response.send_message(
            "Säännön lähettäminen epäonnistui. Tarkista botin kanavaoikeudet.",
            ephemeral=True,
        )
        print(f"Could not publish rule {numero.value}: {exc}", flush=True)
        return

    await interaction.response.send_message(
        f"Sääntö {numero.value} julkaistu: {message.jump_url}",
        ephemeral=True,
    )


def make_rule_prefix_command(number: int):
    async def callback(ctx):
        try:
            message = await publish_single_rule(number)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException) as exc:
            await ctx.reply("Säännön lähettäminen epäonnistui. Tarkista botin kanavaoikeudet.")
            print(f"Could not publish rule {number}: {exc}", flush=True)
            return

        await ctx.reply(
            f"Sääntö {number} julkaistu: {message.jump_url}",
            mention_author=False,
        )

    callback.__name__ = f"rule_{number}_prefix"
    callback.__doc__ = f"Julkaise killan sääntö {number}."
    return callback


for rule_number in range(1, 5):
    bot.command(
        name=f"sääntö{rule_number}",
        help=f"Julkaise killan sääntö {rule_number}.",
    )(make_rule_prefix_command(rule_number))


if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN, log_handler=None)
