import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = False  # you don't need message content here
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")

valid_stats = {
    "Kills": "kills",
    "Deaths": "deaths",
    "Score": "score",
    "Crystals": "earnedcrystals",
    "Gold Boxes": "caughtgolds",
    "Time Played": "timeplayed"
}

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
        response = requests.get(f"https://tankibot.com/api/top?type={self.stat_value}")
        if response.status_code != 200:
            await interaction.response.edit_message(content="Error fetching leaderboard.", view=None)
            return

        data = response.json()
        start = self.page * 10
        end = start + 10
        current_data = data[start:end]

        if not current_data:
            await interaction.response.edit_message(content="No data for this page.", view=self)
            return

        embed = discord.Embed(
            title=f"🏆 Top {self.stat_key} (#{start+1}–{end})",
            color=discord.Color.blurple()
        )
        for i, player in enumerate(current_data, start=start + 1):
            embed.add_field(name=f"#{i} {player['name']}", value=f"{self.stat_key}: {player['score']}", inline=False)

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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    # Sync commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="top", description="Show interactive leaderboard")
async def top(interaction: discord.Interaction):
    default_stat_key = "Kills"
    default_stat_value = valid_stats[default_stat_key]
    view = LeaderboardView(default_stat_key, default_stat_value, page=0)

    response = requests.get(f"https://tankibot.com/api/top?type={default_stat_value}")
    if response.status_code != 200:
        await interaction.response.send_message("Failed to fetch leaderboard.")
        return

    data = response.json()
    page_data = data[0:10]

    embed = discord.Embed(title=f"🏆 Top {default_stat_key} (#1–10)", color=discord.Color.blurple())
    for i, player in enumerate(page_data, start=1):
        embed.add_field(name=f"#{i} {player['name']}", value=f"{default_stat_key}: {player['score']}", inline=False)

    await interaction.response.send_message(embed=embed, view=view)

keep_alive()
bot.run(TOKEN)
