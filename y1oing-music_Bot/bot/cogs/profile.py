# --- English ---
# This Cog handles user-specific profile management commands.
# It allows users to manage their personal settings, such as default volume,
# which are automatically loaded when they use the bot.

# --- 日本語 ---
# ユーザー固有のプロフィール管理コマンドを扱うCogです。
# デフォルト音量などの個人設定を管理し、ボット使用時に自動的に読み込まれます。

import discord
from discord import app_commands
from discord.ext import commands
from utils.profile_manager import ProfileManager



class ProfileCog(commands.Cog):
    """Cog for managing user profiles."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.profile_manager = ProfileManager()


    # --- Profile Commands ---

    @app_commands.command(name="volume", description="Changes playback volume and saves it to your profile.")
    @app_commands.describe(percent="The volume percentage to set (0-200).")
    async def volume(self, interaction: discord.Interaction, percent: app_commands.Range[int, 0, 200]):
        # Get the player instance from the PlaybackCog.
        # PlaybackCogからプレイヤーインスタンスを取得します。
        playback_cog = self.bot.get_cog("PlaybackCog")
        if not playback_cog:
            await interaction.response.send_message("Error: Playback feature is currently unavailable.", ephemeral=True)
            return

        player = playback_cog.get_player(interaction)
        if not player or not player.voice_client:
            await interaction.response.send_message("This command can only be used while the bot is in a voice channel.", ephemeral=True)
            return
        
        # Set the player's volume and save the setting to the user's profile.
        # プレイヤーの音量を設定し、その値をユーザーのプロフィールに保存します。
        message = await player.set_volume(percent)
        
        profile_data = self.profile_manager.load_profile(interaction.user.id)
        profile_data['volume'] = percent
        self.profile_manager.save_profile(interaction.user.id, profile_data)
        
        await interaction.response.send_message(f"{message}\nAlso saved to your profile.")


    # --- Profile Command Group ---
    profile_group = app_commands.Group(name="profile", description="Manage user settings.")


    @profile_group.command(name="save", description="Saves the current volume setting to your profile.")
    async def save(self, interaction: discord.Interaction):
        # Determine the current volume and save it to the user's profile.
        # 現在の音量を取得し、ユーザーのプロフィールに保存します。
        playback_cog = self.bot.get_cog("PlaybackCog")
        player = playback_cog.get_player(interaction)
        current_volume_percent = int(player.volume * 100) if player else 100

        profile_data = self.profile_manager.load_profile(interaction.user.id)
        profile_data['volume'] = current_volume_percent
        self.profile_manager.save_profile(interaction.user.id, profile_data)
        
        await interaction.response.send_message(
            f"✅ Saved current volume ({current_volume_percent}%) to your profile.",
            ephemeral=True
        )


    @profile_group.command(name="show", description="Displays your current profile settings.")
    async def show(self, interaction: discord.Interaction):
        # Load and display the user's profile settings in an embed.
        # ユーザーのプロフィール設定を読み込み、埋め込みメッセージで表示します。
        profile = self.profile_manager.load_profile(interaction.user.id)
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Profile",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🔊 Default Volume", value=f"**{profile.get('volume', 100)}%**")
        await interaction.response.send_message(embed=embed, ephemeral=True)



async def setup(bot: commands.Bot):
    """Adds the ProfileCog to the bot."""
    await bot.add_cog(ProfileCog(bot))