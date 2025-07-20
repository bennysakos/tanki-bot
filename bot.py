import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
from keep_alive import keep_alive

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

valid_stats = {
    "Kills": "kills",
    "Deaths": "deaths",
    "Score": "score",
    "Crystals": "earnedcrystals",
    "Gold Boxes": "caughtgolds",
    "Time Played": "timeplayed"
}

# ---------- Leaderboard View & UI ----------

class LeaderboardView(discord.ui.View):
    def __init__(self, stat_key, stat_value, page=0):
        super().__init__(timeout=60)
        self.stat_key = stat_key
        self.stat_value = stat_value
        self.page = page
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(StatSelector(default=self.stat_key))
        self.add_item(PrevButton())
        self.add_item(NextButton())

    async def send_page(self, interaction: discord.Interaction):
        url = f"https://tankibot.com/api/top?type={self.stat_value}"
        response = requests.get(url)
        if response.status_code != 200:
            await interaction.response.edit_message(content="Error fetching leaderboard.", view=None)
            return

        data = response.json()
        # Fix: get players list safely
        players = data.get("players") or data.get("data") or data  # fallback if structure unknown

        if not isinstance(players, list):
            # If not list, try if data is list itself
            players = []

        start = self.page * 10
        end = start + 10
        current_data = players[start:end]

        if not current_data:
            await interaction.response.edit_message(content="No data for this page.", view=self)
            return

        embed = discord.Embed(
            title=f"🏆 Top {self.stat_key} (#{start + 1}–{end})",
            color=discord.Color.blurple()
        )
        for i, player in enumerate(current_data, start=start + 1):
            score = player.get("score") or player.get(self.stat_value) or "N/A"
            embed.add_field(name=f"#{i} {player.get('name', 'Unknown')}", value=f"{self.stat_key}: {score}", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)


class StatSelector(discord.ui.Select):
    def __init__(self, default=None):
        options = [
            discord.SelectOption(label=key, value=value, default=(key == default))
            for key, value in valid_stats.items()
        ]
        super().__init__(placeholder="Choose a stat...", options=options)

    async def callback(self, interaction: discord.Interaction):
        view: LeaderboardView = self.view
        view.stat_key = [k for k, v in valid_stats.items() if v == self.values[0]][0]
        view.stat_value = self.values[0]
        view.page = 0
        view.update_buttons()
        await view.send_page(interaction)


class PrevButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="<", row=1)

    async def callback(self, interaction: discord.Interaction):
        view: LeaderboardView = self.view
        if view.page > 0:
            view.page -= 1
        await view.send_page(interaction)


class NextButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label=">", row=1)

    async def callback(self, interaction: discord.Interaction):
        view: LeaderboardView = self.view
        view.page += 1
        await view.send_page(interaction)


# ---------- Slash Commands ----------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.tree.command(name="top", description="Show interactive leaderboard")
async def top(interaction: discord.Interaction):
    default_stat_key = "Kills"
    default_stat_value = valid_stats[default_stat_key]

    url = f"https://tankibot.com/api/top?type={default_stat_value}"
    response = requests.get(url)
    if response.status_code != 200:
        await interaction.response.send_message("Failed to fetch leaderboard.", ephemeral=True)
        return

    data = response.json()
    players = data.get("players") or data.get("data") or data
    if not isinstance(players, list):
        players = []

    page_data = players[0:10]

    if not page_data:
        await interaction.response.send_message("No leaderboard data available.", ephemeral=True)
        return

    embed = discord.Embed(title=f"🏆 Top {default_stat_key} (#1–10)", color=discord.Color.blurple())
    for i, player in enumerate(page_data, start=1):
        score = player.get("score") or player.get(default_stat_value) or "N/A"
        embed.add_field(name=f"#{i} {player.get('name', 'Unknown')}", value=f"{default_stat_key}: {score}", inline=False)

    view = LeaderboardView(default_stat_key, default_stat_value, page=0)

    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="user", description="Get player stats by name")
@app_commands.describe(name="Player's in-game name")
async def user(interaction: discord.Interaction, name: str):
    url = f"https://tankibot.com/api/user?name={name}"
    response = requests.get(url)
    if response.status_code != 200:
        await interaction.response.send_message(f"Player '{name}' not found.", ephemeral=True)
        return

    data = response.json()

    # Example fields, adjust to match actual API response
    player_name = data.get("name") or name
    kills = data.get("kills", "N/A")
    deaths = data.get("deaths", "N/A")
    score = data.get("score", "N/A")
    crystals = data.get("earnedcrystals", "N/A")
    gold_boxes = data.get("caughtgolds", "N/A")
    time_played = data.get("timeplayed", "N/A")

    embed = discord.Embed(title=f"Stats for {player_name}", color=discord.Color.green())
    embed.add_field(name="Kills", value=str(kills), inline=True)
    embed.add_field(name="Deaths", value=str(deaths), inline=True)
    embed.add_field(name="Score", value=str(score), inline=True)
    embed.add_field(name="Crystals", value=str(crystals), inline=True)
    embed.add_field(name="Gold Boxes", value=str(gold_boxes), inline=True)
    embed.add_field(name="Time Played", value=str(time_played), inline=True)

    await interaction.response.send_message(embed=embed)


# ---------- Keep bot alive & run ----------

keep_alive()
bot.run(TOKEN)
