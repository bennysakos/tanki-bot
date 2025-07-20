import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
from keep_alive import keep_alive

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# This syncs slash commands to your guild or globally
# Replace with your guild ID for faster development (optional)
GUILD_ID = None  # or discord.Object(id=your_guild_id)

valid_stats = {
    "Kills": "kills",
    "Deaths": "deaths",
    "Score": "score",
    "Crystals": "earnedcrystals",
    "Gold Boxes": "caughtgolds",
    "Time Played": "timeplayed"
}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    # Sync commands globally (slow) or to a specific guild (fast)
    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced commands to guild {GUILD_ID}")
    else:
        await bot.tree.sync()
        print("Synced commands globally")

@bot.tree.command(name="top", description="Show leaderboard for a stat")
@app_commands.describe(stat="Stat to show leaderboard for")
async def top(interaction: discord.Interaction, stat: str = "Kills"):
    stat_key = None
    stat_value = None
    for k, v in valid_stats.items():
        if stat.lower() == k.lower():
            stat_key = k
            stat_value = v
            break
    if stat_value is None:
        valid_keys = ", ".join(valid_stats.keys())
        await interaction.response.send_message(f"Invalid stat. Valid stats: {valid_keys}", ephemeral=True)
        return

    try:
        response = requests.get(f"https://tankibot.com/api/top?type={stat_value}")
        response.raise_for_status()
        data = response.json()
    except Exception:
        await interaction.response.send_message("Failed to fetch leaderboard.", ephemeral=True)
        return

    embed = discord.Embed(title=f"🏆 Top {stat_key} (Top 10)", color=discord.Color.blurple())
    for i, player in enumerate(data[:10], start=1):
        embed.add_field(name=f"#{i} {player['name']}", value=f"{stat_key}: {player['score']}", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="user", description="Show stats for a user")
@app_commands.describe(username="Username to fetch stats for")
async def user(interaction: discord.Interaction, username: str):
    try:
        response = requests.get(f"https://tankibot.com/api/user?name={username}")
        response.raise_for_status()
        data = response.json()
    except Exception:
        await interaction.response.send_message(f"Failed to fetch stats for {username}.", ephemeral=True)
        return

    if not data or "name" not in data:
        await interaction.response.send_message(f"No data found for user '{username}'.", ephemeral=True)
        return

    embed = discord.Embed(title=f"Stats for {data['name']}", color=discord.Color.green())
    embed.add_field(name="Kills", value=data.get("kills", "N/A"), inline=True)
    embed.add_field(name="Deaths", value=data.get("deaths", "N/A"), inline=True)
    embed.add_field(name="Score", value=data.get("score", "N/A"), inline=True)
    embed.add_field(name="Crystals", value=data.get("earnedcrystals", "N/A"), inline=True)
    embed.add_field(name="Gold Boxes", value=data.get("caughtgolds", "N/A"), inline=True)
    embed.add_field(name="Time Played", value=data.get("timeplayed", "N/A"), inline=True)

    await interaction.response.send_message(embed=embed)

keep_alive()
bot.run(TOKEN)
