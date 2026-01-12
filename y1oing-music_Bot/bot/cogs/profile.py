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


    # profile_group を先に定義する
    profile_group = app_commands.Group(name="profile", description="Manage user settings.")



    @profile_group.command(name="volume", description="Changes playback volume and saves it to your profile.")
    @app_commands.describe(percent="The volume percentage to set (0-200).")
    async def volume(self, interaction: discord.Interaction, percent: app_commands.Range[int, 0, 200]):
        playback_cog = self.bot.get_cog("PlaybackCog")
        if not playback_cog:
            await interaction.response.send_message("Error: Playback feature is currently unavailable.", ephemeral=True)
            return

        player = playback_cog.get_player(interaction)
        if not player or not player.voice_client:
            await interaction.response.send_message("This command can only be used while the bot is in a voice channel.", ephemeral=True)
            return
        
        message = await player.set_volume(percent)
        
        profile_data = self.profile_manager.load_profile(interaction.user.id)
        profile_data['volume'] = percent
        self.profile_manager.save_profile(interaction.user.id, profile_data)
        
        await interaction.response.send_message(f"{message}\nAlso saved to your profile.")


    @profile_group.command(name="eq", description="Switch sound quality mode")
    @app_commands.describe(mode="Please select the mode that matches your playback environment.")
    @app_commands.choices(mode=[
        discord.app_commands.Choice(name="🎧 High quality (Hi-Fi)", value="hifi"),
        discord.app_commands.Choice(name="🎵 Balanced (Balanced)", value="balanced"),
    ])
    async def eq(self, interaction: discord.Interaction, mode: discord.app_commands.Choice[str]):
        # プロフィールをロード
        profile_data = self.profile_manager.load_profile(interaction.user.id)
        
        # 新しいモードを設定
        new_mode = mode.value
        profile_data['eq_mode'] = new_mode
        
        # プロフィールを保存
        self.profile_manager.save_profile(interaction.user.id, profile_data)
        
        # Playerインスタンスがあれば、即座に設定を反映
        playback_cog = self.bot.get_cog("PlaybackCog")
        if playback_cog:
            player = playback_cog.get_player(interaction)
            if player:
                player.eq_mode = new_mode
                await interaction.response.send_message(
                    f"✅ Sound quality mode has been changed to [{mode.name}]\nApplies to the next track",
                    ephemeral=True
                )
                return

        await interaction.response.send_message(
            f"✅ Sound quality mode has been changed to [{mode.name}]\nThis change will take effect starting with your next playback session.",
            ephemeral=True
        )


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
        profile = self.profile_manager.load_profile(interaction.user.id)
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Profile",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        volume_setting = profile.get('volume', 100)
        
        eq_mode = profile.get('eq_mode', 'balanced')
        mode_display = "🎧 Hi-Fi" if eq_mode == 'hifi' else "🎵 Balanced"
        
        embed.description = (
            f"**🔊 Volume:** {volume_setting}%\n"
            f"**🎚️ EQ Mode:** {mode_display}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)



async def setup(bot: commands.Bot):
    """Adds the ProfileCog to the bot."""
    await bot.add_cog(ProfileCog(bot))
