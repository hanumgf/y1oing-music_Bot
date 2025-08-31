# --- English ---
# This Cog is the core of the music functionality. It manages:
# - Player instances for each server (guild).
# - Voice channel connections and events (e.g., auto-disconnect).
# - All playback-related application commands like /play, /skip, /queue, etc.
# Each server gets its own Player instance to handle its queue and playback state independently.

# --- 日本語 ---
# このCogは音楽機能の中核です。以下を管理します:
# - 各サーバー（ギルド）ごとのPlayerインスタンス。
# - ボイスチャンネルへの接続とイベント（例: 自動退出）。
# - /play, /skip, /queue などの再生関連の全アプリケーションコマンド。
# サーバーごとに独立したPlayerインスタンスが割り当てられ、キューや再生状態を個別に管理します。

from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from utils.player import Player
from discord.app_commands import checks
import asyncio
from utils.audio_handler import AudioHandler
from utils.views import ControlPanelView, SearchView, PaginatorView
import math
import time



class PlaybackCog(commands.Cog):
    """Cog responsible for all music playback functionalities."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}  # Stores Player instances, keyed by guild ID.
        self.audio_handler = AudioHandler()


    # --- Player Management ---

    def get_player(self, source: discord.Interaction | discord.Member | discord.Message) -> 'Player' | None:
        """
        Retrieves the Player instance for a given guild.
        Returns None if no player exists for that guild.
        
        指定されたギルドのPlayerインスタンスを取得します。
        存在しない場合はNoneを返します。
        """
        if not source.guild:
            return None
        return self.players.get(source.guild.id)


    def get_or_create_player(self, interaction: discord.Interaction) -> Player:
        """
        Retrieves the Player for a guild, creating a new one if it doesn't exist.
        Also starts a watcher task to clean up the player after it finishes.
        
        ギルドのPlayerを取得し、なければ新規作成します。
        また、Player終了後にクリーンアップするための監視タスクを開始します。
        """
        guild_id = interaction.guild.id
        
        if guild_id not in self.players:
            player = Player(self.bot, guild_id) 
            self.players[guild_id] = player
            
            # Start a background task to watch for the player's completion.
            self.bot.loop.create_task(self.player_watcher(player))
            print(f"New Player created for guild {guild_id}. Watcher started.")
            
        return self.players[guild_id]


    async def player_watcher(self, player: Player):
        """
        Waits for a Player's main task to complete, then safely removes it from the active players dictionary.
        This ensures resources are cleaned up properly.
        
        Playerのメインタスクが完了するのを待ち、完了後にアクティブなプレイヤー辞書から安全に削除します。
        これにより、リソースが適切にクリーンアップされます。
        """
        await player.player_task
        
        guild_id = player.guild_id
        if guild_id in self.players and self.players[guild_id] is player:
            del self.players[guild_id]
            print(f"Player for guild {guild_id} has finished and been cleaned up from PlaybackCog.")


    # --- Event Listeners ---

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """
        Monitors voice channel state changes to manage auto-disconnection.
        
        ボイスチャンネルの状態変化を監視し、自動退出を管理します。
        """
        # Ignore state changes from the bot itself, unless it was disconnected by an admin.
        if member.bot and member.id == self.bot.user.id:
            if before.channel and not after.channel:
                player = self.get_player(member)
                if player:
                    print(f"Bot was disconnected from VC by an admin in guild {member.guild.id}. Cleaning up.")
                    await player.cleanup()
            return
            
        player = self.players.get(member.guild.id)
        if not player or not player.voice_client or not player.voice_client.is_connected():
            return
            
        bot_channel = player.voice_client.channel
        human_members = [m for m in bot_channel.members if not m.bot]
        
        # Scenario 1: The bot is left alone in the channel.
        if len(human_members) == 0:
            if not player.empty_channel_leavetask or player.empty_channel_leavetask.done():
                if player.text_channel:
                    await player.text_channel.send("Everyone left... I'll leave automatically in 30 seconds.")
                player.empty_channel_leavetask = self.bot.loop.create_task(self.empty_channel_leave_timer(player))

        # Scenario 2: Someone joins the channel where the bot was alone.
        else:
            if player.empty_channel_leavetask and not player.empty_channel_leavetask.done():
                player.empty_channel_leavetask.cancel()
                if player.text_channel:
                    await player.text_channel.send("Welcome back! Canceling auto-leave.")
                player.empty_channel_leavetask = None


    async def empty_channel_leave_timer(self, player: 'Player'):
        """
        Waits for a short period and then disconnects the player if the channel is still empty.
        
        短時間待機し、チャンネルがまだ空であればプレイヤーを切断します。
        """
        await asyncio.sleep(30)
        
        # Double-check if the channel is still empty before leaving.
        if player.voice_client and player.voice_client.is_connected():
            human_members = [m for m in player.voice_client.channel.members if not m.bot]
            if len(human_members) == 0:
                print(f"Leaving empty channel in guild {player.guild_id}.")
                await player.cleanup()


    # --- Voice Connection Commands ---

    @app_commands.command(name="join", description="Makes the bot join your voice channel.")
    @checks.cooldown(1, 4.0, key=lambda i: i.guild.id)
    async def join(self, interaction: discord.Interaction):
        player = self.get_or_create_player(interaction)
        success, message = await player.connect(interaction)
        
        if success:
            try:
                await interaction.response.send_message(message)
            except discord.errors.InteractionResponded:
                # Handled if `player.connect` already sent a response.
                pass


    @app_commands.command(name="leave", description="Makes the bot leave the voice channel.")
    @checks.cooldown(1, 4.0, key=lambda i: i.guild.id)
    async def leave(self, interaction: discord.Interaction):
        player = self.get_player(interaction)
        if player:
            message = await player.disconnect()
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)


    # --- Playback Control Commands ---

    @app_commands.command(name="play", description="Plays a song or adds it to the queue.")
    @app_commands.describe(query="A YouTube URL or a search query.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def play(self, interaction: discord.Interaction, query: str):
        
        # Defer the interaction immediately to handle all possible paths without timeouts.
        await interaction.response.defer(ephemeral=True)
        
        player = self.get_or_create_player(interaction)

        # This is the final alchemy.

        final_query = query # The URL or search term we will ultimately use.
        
        # 1. First, check if the query is a direct URL. If it is, we also check for playlists.
        if self.audio_handler.is_youtube_url(query):
            if 'list=' in query:
                await interaction.followup.send("❌ Playlist URLs are not supported with /play. Use `/playlist_add` instead.", ephemeral=True)
                return
        
        # 2. If it's a search term (not a URL), use the fast `search_youtube` to find the top result.
        else:
            print(f"INFO: /play received a search term '{query}'. Searching for top result...")
            entries, error = await self.audio_handler.search_youtube(query, max_results=1)
            
            if error or not entries:
                await interaction.followup.send(f"❌ Could not find any results for `{query}`.", ephemeral=True)
                return
            
            # 3. Use the URL of the top result as our new, definitive query.
            top_result = entries[0]
            final_query = top_result.get('webpage_url') or top_result.get('url')
            
            if not final_query:
                await interaction.followup.send(f"❌ Found a result for `{query}`, but it has no valid URL.", ephemeral=True)
                return

        # 4. Now, proceed with a guaranteed valid URL.

        # Ensure the bot is connected to a voice channel.
        success, _ = await player.connect(interaction)
        if not success:
            # connect() handles its own response on failure, and we've already deferred.
            return
        
        # Delegate the track adding process to the player.
        # The allow_playlist=False is correctly set here.
        reception_message = await player.add_to_queue(interaction, final_query, allow_playlist=False)
        await interaction.followup.send(reception_message)


    @app_commands.command(name="pause", description="Pauses the current music.")
    @checks.cooldown(1, 4.0, key=lambda i: i.guild.id)
    async def pause(self, interaction: discord.Interaction):
        player = self.get_player(interaction)
        if player:
            message = await player.pause()
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message("There is no music currently playing.", ephemeral=True)


    @app_commands.command(name="resume", description="Resumes the paused music.")
    @checks.cooldown(1, 4.0, key=lambda i: i.guild.id)
    async def resume(self, interaction: discord.Interaction):
        player = self.get_player(interaction)
        if player:
            message = await player.resume()
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message("There is no music currently paused.", ephemeral=True)


    @app_commands.command(name="stop", description="Stops playback and clears the queue.")
    @checks.cooldown(1, 4.0, key=lambda i: i.guild.id)
    async def stop(self, interaction: discord.Interaction):
        player = self.get_player(interaction)
        if player:
            message = player.stop()
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message("There is no music currently playing.", ephemeral=True)


    @app_commands.command(name="skip", description="Skips the current song.")
    @checks.cooldown(1, 4.0, key=lambda i: i.guild.id)
    async def skip(self, interaction: discord.Interaction):
        player = self.get_player(interaction)
        if player:
            message = player.skip()
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message("There is no music currently playing.", ephemeral=True)


    @app_commands.command(name="previous", description="Plays the previous song from history.")
    @checks.cooldown(1, 4.0, key=lambda i: i.guild.id)
    async def previous(self, interaction: discord.Interaction):
        await interaction.response.defer()
        player = self.get_player(interaction)
        if player:
            message = player.previous()
            await interaction.followup.send(message)
        else:
            await interaction.followup.send("There is no playback history.", ephemeral=True)


    # --- Queue and Utility Commands ---

    @app_commands.command(name="queue", description="Displays the current song queue.")
    @checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction)
        
        # If the Player does not exist, or the song and cue are empty during playback
        if not player or (not player.current_track and not player.queue):
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
            return
            
        # --- Pagination Processing ---
        items_per_page = 10
        queue_tracks = list(player.queue)
        total_pages = math.ceil(len(queue_tracks) / items_per_page) if queue_tracks else 1

        def create_embed_for_page(page_num: int):
            """Generates an embed for the specified page number."""
            
            embed = discord.Embed(
                title="🎵 Music Queue",
                color=discord.Color.blue()
            )
            if player.current_track:
                embed.description = f"**Now Playing:**\n[{player.current_track['title']}]({player.current_track['webpage_url']})\n\n**Up Next:**"
            else:
                embed.description = "**Up Next:**"
            
            if not queue_tracks:
                embed.description += "\n*The queue is empty.*"
                return embed

            start_index = (page_num - 1) * items_per_page
            end_index = start_index + items_per_page
            page_items = queue_tracks[start_index:end_index]
            
            track_list_str = "\n".join([
                f"`{start_index + i + 1}.` [{track['title']}]({track['webpage_url']})" 
                for i, track in enumerate(page_items)
            ])
            embed.description += f"\n{track_list_str}"
            
            total_duration_seconds = sum(t.get('duration', 0) for t in queue_tracks)
            total_duration_str = time.strftime('%H:%M:%S', time.gmtime(total_duration_seconds)) if total_duration_seconds > 3600 else time.strftime('%M:%S', time.gmtime(total_duration_seconds))
            
            embed.set_footer(text=f"Page {page_num}/{total_pages}  •  {len(queue_tracks)} songs in queue  •  Total duration: {total_duration_str}")
            return embed

        # Generate PaginatorView and send first page
        initial_embed = create_embed_for_page(1)
        view = PaginatorView(embed_creator=create_embed_for_page, total_pages=total_pages)
        
        await interaction.response.send_message(embed=initial_embed, view=view)


    @app_commands.command(name="queue_remove", description="Removes a song from the queue by its number.")
    @app_commands.describe(number="The number of the song to remove.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def remove(self, interaction: discord.Interaction, number: int):
        player = self.get_player(interaction)
        if player:
            message = player.remove_from_queue(number)
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)


    @app_commands.command(name="search", description="Search for a song on YouTube and choose from the results.")
    @app_commands.describe(query="Keywords to search for.")
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)

        # Use AudioHandler to search for tracks.
        # AudioHandlerを使用して曲を検索します。
        entries, error = await self.audio_handler.search_youtube(query, max_results=20)
        
        if error or not entries:
            await interaction.followup.send(f"❌ An error occurred or no results were found for `{query}`.", ephemeral=True)
            return
            
        player = self.get_or_create_player(interaction)
        
        # Display search results in an interactive view.
        view = SearchView(interaction, entries, player)
        embed = discord.Embed(
            title=f"🔎 Search Results: `{query}`",
            description=f"Found {len(entries)} tracks. Please select one from the menu below.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


    @app_commands.command(name="nowplaying", description="Shows the current song and the control panel.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def nowplaying(self, interaction: discord.Interaction):
        player = self.get_player(interaction)
        if player and player.current_track:
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{player.current_track['title']}**",
                color=discord.Color.green()
            )
            view = ControlPanelView(player)
            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("There is no music currently playing.", ephemeral=True)


    @app_commands.command(name="loop", description="Sets the loop mode for playback.")
    @app_commands.describe(mode="Choose the loop mode.")
    @app_commands.choices(mode=[
        discord.app_commands.Choice(name="Off", value="off"),
        discord.app_commands.Choice(name="Track", value="track"),
        discord.app_commands.Choice(name="Queue", value="queue"),
    ])
    @checks.cooldown(1, 4.0, key=lambda i: i.guild.id)
    async def loop(self, interaction: discord.Interaction, mode: discord.app_commands.Choice[str]):
        player = self.get_player(interaction)
        if player:
            player.loop_mode = mode.value
            await interaction.response.send_message(f"✅ Loop mode set to **{mode.name}**.")
            
            # Update the Now Playing panel to reflect the new loop state.
            await player.update_now_playing_panel()
        else:
            await interaction.response.send_message("Please start playback before setting a loop mode.", ephemeral=True)



async def setup(bot: commands.Bot):
    """Adds the PlaybackCog to the bot."""
    await bot.add_cog(PlaybackCog(bot))
