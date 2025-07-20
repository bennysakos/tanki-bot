import os
import discord
from discord.ext import commands
import requests
from keep_alive import keep_alive  # your flask keep-alive server

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)

valid_stats = {
    "Kills": "kills",
    "Deaths": "deaths",
    "Score": "score",
    "Crystals": "earnedcrystals",
    "Gold Boxes": "caughtgolds",
    "Time Played": "timeplayed"
}

# ----- UI Components for /top leaderboard ----- #

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


class LeaderboardView(discord.ui.View):
    def __init__(self, stat_key, stat_value, page=0):
        super().__init__(timeout=120)
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

        # Defensive parsing for players list
        if isinstance(data, dict):
            players = data.get("players") or data.get("data") or []
        elif isinstance(data, list):
            players = data
        else:
            players = []

        start = self.page * 10
        end = start + 10
        current_data = players[start:end]

        if not current_data:
            await interaction.response.edit_message(content="No data for this page.", view=self)
            return

        embed = discord.Embed(
            title=f"🏆 Top {self.stat_key} (#{start + 1}–{min(end, len(players))})",
            color=discord.Color.blurple()
        )
        for i, player in enumerate(current_data, start=start + 1):
            score = player.get("score") or player.get(self.stat_value) or "N/A"
            embed.add_field(name=f"#{i} {player.get('name', 'Unknown')}", value=f"{self.stat_key}: {score}", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)


# ----- Commands ----- #

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync()
    print("Commands synced")


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

    if isinstance(data, dict):
        players = data.get("players") or data.get("data") or []
    elif isinstance(data, list):
        players = data
    else:
        players = []

    if not players:
        await interaction.response.send_message("No leaderboard data available.", ephemeral=True)
        return

    page_data = players[0:10]

    embed = discord.Embed(title=f"🏆 Top {default_stat_key} (#1–{min(10,len(players))})", color=discord.Color.blurple())
    for i, player in enumerate(page_data, start=1):
        score = player.get("score") or player.get(default_stat_value) or "N/A"
        embed.add_field(name=f"#{i} {player.get('name', 'Unknown')}", value=f"{default_stat_key}: {score}", inline=False)

    view = LeaderboardView(default_stat_key, default_stat_value, page=0)
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="user", description="Get player stats by name")
@discord.app_commands.describe(name="Player username")
async def user(interaction: discord.Interaction, name: str):
    url = f"https://tankibot.com/api/user?name={name}"
    response = requests.get(url)
    if response.status_code != 200:
        await interaction.response.send_message(f"Player '{name}' not found.", ephemeral=True)
        return

    data = response.json()

    embed = discord.Embed(title=f"Stats for {data.get('name', name)}", color=discord.Color.green())
    for key, api_key in valid_stats.items():
        embed.add_field(name=key, value=str(data.get(api_key, "N/A")), inline=True)

    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
