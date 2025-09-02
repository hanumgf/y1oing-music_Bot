# --- English ---
# This Cog provides utility features for the bot, primarily an interactive help command.
# It uses a centralized data structure (`HELP_DATA`) for easy management
# and UI components (`discord.ui`) for a user-friendly experience.

# --- 日本語 ---
# このCogは、主にインタラクティブなヘルプコマンドなど、ボットの補助機能を提供します。
# 管理を容易にするための中央集権的なデータ構造（`HELP_DATA`）と、
# ユーザーフレンドリーな体験のためのUIコンポーネント（`discord.ui`）を使用します。

from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta


# --- Help Command Data Store ---
# Centralizes all help information for easy updates and management.
# 全てのヘルプ情報を一元管理し、更新と保守を容易にします。
HELP_DATA = {
    "home": {
        "title": "y1oing Music BOT Help Menu",
        "description": (
            "Hello! Welcome to the ultimate music experience.\n"
            "Please select a command category from the menu below."
        ),
        "color": discord.Color.gold()
    },
    "categories": {
        "basic": {
            "label": "🎵 Basic",
            "emoji": "🎵",
            "description": "Basic commands for music playback.",
            "commands": {
                "/play `query`": "Plays or adds a song to the queue. The most popular track will be played.",
                "/search `query`": "Interactively search for a song and choose from a list.",
                "/join": "Joins a voice channel.",
                "/leave": "Leaves the voice channel.",
            }
        },
        "control": {
            "label": "⏯️ Playback Control",
            "emoji": "⏯️",
            "description": "Commands to control the currently playing music.",
            "commands": {
                "/pause": "Pauses playback.",
                "/resume": "Resumes playback.",
                "/stop": "Stops playback and clears the queue.",
                "/skip": "Skips the current song.",
                "/previous": "Returns to the previous song.",
                "/nowplaying": "Reshows the current Now Playing panel.",
            }
        },
        "queue": {
            "label": "📋 Queue",
            "emoji": "📋",
            "description": "Commands related to the music queue.",
            "commands": {
                "/queue": "Displays the song queue.",
                "/remove `number`": "Removes a song from the queue by its number.",
            }
        },
        "playlist": {
            "label": "👤 Personal Playlist",
            "emoji": "👤",
            "description": "Manage your personal playlists.",
            "commands": {
                "/playlist_show `[name]`": "Shows a list of your playlists or the contents of one.",
                "/playlist_create `name`": "Creates a new playlist.",
                "/playlist_add `playlist_name` `query`": "Adds a song to a playlist.",
                "/playlist_play `name`": "Plays a playlist.",
            }
        },
        "server_playlist": {
            "label": "🌐 Server Playlist",
            "emoji": "🌐",
            "description": "Manage playlists shared across the server.",
            "commands": {
                "/serverplaylist_show `[name]`": "Shows a list of shared playlists or the contents of one.",
                "/serverplaylist_create `name`": "[Admin] Creates a new shared playlist.",
                "/serverplaylist_lock `name`": "[Owner] Locks/unlocks a playlist.",
            }
        },
        "settings": {
            "label": "⚙️ Settings & More",
            "emoji": "⚙️",
            "description": "Commands for bot settings and profiles.",
            "commands": {
                "/volume `percent`": "Changes volume and saves to your profile.",
                "/loop `mode`": "Sets the loop mode (Off, Track, Queue).",
                "/profile show": "Shows your current profile settings.",
                "/profile save": "Saves the current volume to your profile.",
            }
        }
    }
}





# --- UI Components for Help Command ---

class HelpSelect(discord.ui.Select):
    """A dropdown menu for selecting a help category."""
    def __init__(self):
        options = [
            discord.SelectOption(
                label=details["label"],
                description=details["description"],
                value=key,
                emoji=details.get("emoji")
            ) for key, details in HELP_DATA["categories"].items()
        ]
        super().__init__(placeholder="Select a help category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # When a category is selected, edit the message to show the commands in that category.
        # カテゴリが選択されたら、メッセージを編集してそのカテゴリのコマンド一覧を表示します。
        category_key = self.values[0]
        category_info = HELP_DATA["categories"][category_key]
        
        embed = discord.Embed(
            title=f"{category_info['label']} Commands",
            color=interaction.client.user.color or discord.Color.blue()
        )
        for name, value in category_info["commands"].items():
            embed.add_field(name=name, value=value, inline=False)
        
        embed.set_footer(text="<> denotes required arguments, [] denotes optional arguments.")
        await interaction.response.edit_message(embed=embed)


class GoHomeButton(discord.ui.Button):
    """A button to return to the initial help screen."""
    def __init__(self):
        super().__init__(label="Go Home", emoji="🏠", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        # Edit the message to display the initial home embed.
        # メッセージを編集して、最初のホーム画面の埋め込みを表示します。
        home_info = HELP_DATA["home"]
        embed = discord.Embed(
            title=home_info["title"],
            description=home_info["description"].format(user_mention=interaction.user.mention),
            color=home_info["color"]
        )
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    """The main view for the help command, containing the select menu and home button."""
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(HelpSelect())
        self.add_item(GoHomeButton())



# --- Cog Definition ---

class UtilityCog(commands.Cog):
    """Cog for utility commands like /help."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 1. Get the absolute path to this file (__file__)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 2. Constructs an absolute path to `config.json`, located three levels above (`..`)
        self.config_path = os.path.join(script_dir, '..', '..', '..', 'config.json')

    # --- Load and Save Config Methods ---
    def load_config(self) -> dict:
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {} # ファイルが存在しない場合は空の辞書を返す

    def save_config(self, data: dict):
        """設定ファイルに書き込む"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)


    @app_commands.command(name="help", description="Shows how to use y1oing Music BOT.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def help(self, interaction: discord.Interaction):
        # Creates and sends the initial help message with the category selection view.
        # カテゴリ選択ビューを含む、初期ヘルプメッセージを作成して送信します。
        home_info = HELP_DATA["home"]
        embed = discord.Embed(
            title=home_info["title"],
            description=home_info["description"].format(user_mention=interaction.user.mention),
            color=home_info["color"]
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"{self.bot.user.name} - Sound Perfected.")
        
        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)


    @app_commands.command(name="feedback", description="Send feedback or report a bug to the developer.")
    @app_commands.describe(message="Your feedback message.")
    @app_commands.checks.cooldown(4, 86400.0, key=lambda i: i.user.id)
    async def feedback(self, interaction: discord.Interaction, message: str):
        
        config = self.load_config()
        recipient_id_str = config.get("feedback_recipient_id")

        # --- [追加] 実行時チェック ---
        # 1. IDが設定されているか、かつデフォルトのままではないか
        if not recipient_id_str or not recipient_id_str.isdigit() or "Your_User_ID_Here" in recipient_id_str:
            print(f"--- FEEDBACK ERROR ---")
            print(f"Feedback from {interaction.user} failed.")
            print(f"Reason: feedback_recipient_id is not configured correctly in config.json.")
            print(f"Current value: {recipient_id_str}")
            print(f"----------------------")
            await interaction.response.send_message("❌ Sorry, the feedback feature is currently unavailable. The developer has been notified.", ephemeral=True)
            return

        try:
            # 2. IDが、実在するDiscordユーザーのものか
            recipient_id = int(recipient_id_str)
            recipient = await self.bot.fetch_user(recipient_id)
        except (discord.NotFound, ValueError):
            print(f"--- FEEDBACK ERROR ---")
            print(f"Feedback from {interaction.user} failed.")
            print(f"Reason: The user ID '{recipient_id_str}' set as feedback_recipient_id could not be found.")
            print(f"----------------------")
            await interaction.response.send_message("❌ Sorry, the feedback feature is currently unavailable. The developer has been notified.", ephemeral=True)
            return

        # 開発者に送信するDMのEmbedを作成
        embed = discord.Embed(
            title="📬 New Feedback Received",
            description=message,
            color=discord.Color.orange(),
            timestamp=interaction.created_at
        )
        embed.set_author(
            name=f"From: {interaction.user.display_name} ({interaction.user.id})",
            icon_url=interaction.user.display_avatar.url
        )
        if interaction.guild:
            embed.add_field(name="Sent From Server", value=f"{interaction.guild.name} ({interaction.guild.id})")

        try:
            # DMを送信
            await recipient.send(embed=embed)
            
            # 送信成功をユーザーに通知
            await interaction.response.send_message("✅ Thank you! Your feedback has been sent successfully.", ephemeral=True)
        except discord.Forbidden:
            # 開発者がDMをブロックしているなどの理由で送信失敗
            await interaction.response.send_message("❌ Sorry, I couldn't deliver your message to the developer.", ephemeral=True)


    @app_commands.command(name="set_feedback_recipient", description="[Owner Only] Set the user who receives feedback.")
    @app_commands.describe(user="The user who will receive feedback DMs.")
    @app_commands.check(commands.is_owner()) # Botのオーナーだけが実行できる
    async def set_feedback_recipient(self, interaction: discord.Interaction, user: discord.User):
        
        config = self.load_config()
        config["feedback_recipient_id"] = str(user.id)
        self.save_config(config)

        await interaction.response.send_message(f"✅ Feedback will now be sent to **{user.display_name}**.", ephemeral=True)

    # Botオーナーチェックに失敗した時のエラーメッセージ
    @set_feedback_recipient.error
    async def on_set_feedback_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)



async def setup(bot: commands.T):
    """Adds the UtilityCog to the bot."""
    await bot.add_cog(UtilityCog(bot))
