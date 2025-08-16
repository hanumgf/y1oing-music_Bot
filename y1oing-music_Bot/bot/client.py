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
import os


# --- Bot Configuration ---

# For faster testing, specify a server (guild) ID to sync commands instantly.
# To deploy commands globally for production, comment out or remove this line.
# テストを高速化するため、コマンドを即時同期させるサーバー（ギルド）IDを指定します。
# 本番環境でコマンドをグローバルにデプロイする場合は、この行をコメントアウトまたは削除してください。
TEST_GUILD = discord.Object(id=1364192771404992542) # <- Your test server ID (numeric) goes here



# --- Main Bot Class ---

class Y1oingBot(commands.Bot):
    """The main bot class for y1oing BOT."""

    def __init__(self):
        # Initialize the bot with all intents enabled for full functionality.
        # `command_prefix` is not needed for slash commands.
        # 全ての機能を利用するため、全てのIntentsを有効にしてボットを初期化します。
        # スラッシュコマンドでは `command_prefix` は不要です。
        intents = discord.Intents.all()
        super().__init__(command_prefix="?", intents=intents)

        # Set up the global error handler for all application commands.
        # This is the standard way to assign an error handler within a class.
        # 全てのアプリケーションコマンドに対するグローバルエラーハンドラを設定します。
        # これはクラス内でエラーハンドラを割り当てる標準的な方法です。
        self.tree.on_error = self.on_app_command_error


    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """
        Global error handler for all application (slash) commands.
        Catches and handles various types of command errors.
        
        全てのアプリケーション（スラッシュ）コマンドのグローバルエラーハンドラ。
        様々な種類のコマンドエラーを捕捉し、処理します。
        """
        # Handle command cooldown errors.
        # コマンドがクールダウン中のエラーを処理します。
        if isinstance(error, app_commands.errors.CommandOnCooldown):
            cooldown_time = round(error.retry_after, 2)
            await interaction.response.send_message(
                f"⏳ This command is on cooldown. Please try again in **{cooldown_time} seconds**.",
                ephemeral=True
            )
            return
            
        # Handle missing permissions errors.
        # 実行に必要な権限が不足しているエラーを処理します。
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                f"❌ You need the following permissions to run this command: `{'`, `'.join(error.missing_permissions)}`",
                ephemeral=True
            )
            return

        # Handle other generic check failures.
        # その他の汎用的なチェック失敗を処理します。
        if isinstance(error, app_commands.errors.CheckFailure):
            await interaction.response.send_message("❌ You do not meet the conditions to run this command.", ephemeral=True)
            return

        # Handle unexpected errors and log them.
        # A generic message is sent to the user to avoid exposing implementation details.
        # 予期しないエラーを処理し、コンソールにログを出力します。
        # 実装の詳細を隠すため、ユーザーには汎用的なメッセージを送信します。
        original_error = getattr(error, 'original', error)
        print(f"Unhandled error in command '{interaction.command.name}': {original_error}")
        
        error_message = "An unexpected error occurred while executing the command. Please report this to the developer."
        
        # Try to send a response or a followup message.
        # This handles cases where the interaction might have already been responded to.
        # レスポンスまたはフォローアップメッセージの送信を試みます。
        # これにより、インタラクションが既に応答済みの場合にも対応できます。
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
        # ボットのプレゼンス（ステータスとアクティビティ）を設定します。
        activity = discord.Activity(type=discord.ActivityType.listening, name="PLAY | Sound Perfected")
        await self.change_presence(status=discord.Status.online, activity=activity)
        
        print(f"Presence set to: Listening to {activity.name}")
        print("y1oing BOT is ready!")
        print("--------------------")