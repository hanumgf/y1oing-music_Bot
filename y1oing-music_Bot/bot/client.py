# --- English ---
# This file defines the main bot client class, `Y1oingBot`.
# It inherits from `commands.Bot` and sets up core functionalities such as:
# - Cogs loading
# - Global application command error handling
# - Bot-ready event handling (e.g., setting presence)
# - Command synchronization with Discord.

# --- 日本語 ---
# メインのボットクライアントクラス `Y1oingBot` を定義するファイルです。
# `commands.Bot` を継承し、以下のコア機能を設定します:
# - Cog の読み込み
# - グローバルなアプリケーションコマンドのエラーハンドリング
# - ボットの準備完了イベント処理（プレゼンス設定など）
# - Discordとのコマンド同期

import discord
from discord.ext import commands
from discord import app_commands
import json
import os


# --- Bot Configuration ---

# For faster testing, specify a server (guild) ID to sync commands instantly.
# To deploy commands globally for production, comment out or remove this line.
# テストを高速化するため、コマンドを即時同期させるサーバー（ギルド）IDを指定します。
# 本番環境でコマンドをグローバルにデプロイする場合は、この行をコメントアウトまたは削除してください。
TEST_GUILD = discord.Object(id=0000) # <- Your test server ID (numeric) goes here



# --- Main Bot Class ---

class Y1oingBot(commands.Bot):
    """The main bot class for y1oing Music BOT."""

    def __init__(self):
        
        intents = discord.Intents.all()
        owner_ids = []
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, '..', 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                owner_ids_str = config.get("owner_ids", [])
                if not owner_ids_str or "Your_User_ID_Here" in owner_ids_str:
                    print("="*50)
                    print("!!! WARNING: Bot owner ID is not set in config.json! !!!")
                    print("="*50)
                else:
                    owner_ids = [int(id_str) for id_str in owner_ids_str if id_str.isdigit()]
                    if not owner_ids:
                        print("="*50)
                        print("!!! WARNING: owner_ids in config.json contains invalid values! !!!")
                        print("="*50)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print("="*50)
            print(f"!!! ERROR: Could not load config.json: {e} !!!")
            print("="*50)

        # --- ★変更点3: 材料が全て揃ったので、最後に、一度だけ、Botを「組み立てる」 ---
        super().__init__(
            command_prefix="!y1oing_unused_prefix!", # プレフィックスは使わないので、何でも良い
            intents=intents,
            owner_ids=set(owner_ids) # configから読み込んだowner_idsを、ここで渡す
        )

        self.tree.on_error = self.on_app_command_error


    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """
        Global error handler for all application (slash) commands.
        Catches and handles various types of command errors.
        
        全てのアプリケーション（スラッシュ）コマンドのグローバルエラーハンドラ。
        様々な種類のコマンドエラーを捕捉し、処理します。
        """
        # Handle command cooldown errors.
        if isinstance(error, app_commands.errors.CommandOnCooldown):
            cooldown_time = round(error.retry_after, 2)
            await interaction.response.send_message(
                f"⏳ This command is on cooldown. Please try again in **{cooldown_time} seconds**.",
                ephemeral=True
            )
            return
            
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                f"❌ You need the following permissions to run this command: `{'`, `'.join(error.missing_permissions)}`",
                ephemeral=True
            )
            return

        if isinstance(error, app_commands.errors.CheckFailure):
            await interaction.response.send_message("❌ You do not meet the conditions to run this command.", ephemeral=True)
            return

        original_error = getattr(error, 'original', error)
        print(f"Unhandled error in command '{interaction.command.name}': {original_error}")
        
        error_message = "An unexpected error occurred while executing the command. Please report this to the developer."
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(error_message, ephemeral=True)


    async def setup_hook(self):
        """
        This method is called once when the bot logs in.
        It's used to load cogs and synchronize the command tree.
        
        このメソッドはボットがログインする際に一度だけ呼び出されます。
        Cogの読み込みとコマンドツリーの同期に使用されます。
        """
        # Load all cogs from the 'bot/cogs' directory.
        # 'bot/cogs' ディレクトリから全てのCogを読み込みます。
        print("--- Cogs Loading ---")
        for filename in os.listdir("./bot/cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_extension(f"bot.cogs.{filename[:-3]}")
                    print(f"Loaded: {filename}")
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")
        print("--------------------")

        # Synchronize the application commands with Discord.
        # For production, use `await self.tree.sync()`.
        # アプリケーションコマンドをDiscordと同期します。
        # 本番環境では `await self.tree.sync()` を使用します。
        # self.tree.copy_global_to(guild=TEST_GUILD)
        # await self.tree.sync(guild=TEST_GUILD)
        await self.tree.sync()


    async def on_ready(self):
        """
        This event is triggered when the bot is fully connected and ready.
        It prints login information and sets the bot's presence.
        
        このイベントは、ボットが完全に接続され準備が完了したときにトリガーされます。
        ログイン情報を表示し、ボットのプレゼンスを設定します。
        """
        print("--------------------")
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        
        # Set the bot's presence (status and activity).
        activity = discord.Activity(type=discord.ActivityType.listening, name="PLAY | Sound Perfected")
        await self.change_presence(status=discord.Status.online, activity=activity)
        
        print(f"Presence set to: Listening to {activity.name}")
        print("y1oing Music BOT is ready!")
        print("--------------------")
