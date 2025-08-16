# --- English ---
# This Cog manages all commands related to personal playlists.
# It allows users to create, add to, play, view, and manage their own playlists.
# All operations are delegated to the `PlaylistManager` and `AudioHandler` for logic and data retrieval.

# --- 日本語 ---
# このCogは、個人用プレイリストに関連するすべてのコマンドを管理します。
# ユーザーは自身のプレイリストの作成、曲の追加、再生、表示、管理ができます。
# すべての操作は、ロジックとデータ取得のために `PlaylistManager` と `AudioHandler` に委任されます。

import discord
from discord import app_commands
from discord.ext import commands
from utils.playlist_manager import PlaylistManager
from utils.audio_handler import AudioHandler
import math
from utils.views import PaginatorView
from discord.app_commands import checks



class PlaylistCog(commands.Cog):
    """Cog for personal playlist management commands."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.playlist_manager = PlaylistManager()
        self.audio_handler = AudioHandler()


    # --- Playlist Creation and Content Addition ---

    @app_commands.command(name="playlist_create", description="Creates a new personal playlist.")
    @app_commands.describe(name="The name of the new playlist.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def playlist_create(self, interaction: discord.Interaction, name: str):
        user_id = interaction.user.id
        message = self.playlist_manager.create(scope="solo", name=name, owner_id=user_id)
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="playlist_add", description="Adds a song or a YouTube playlist to your playlist.")
    @app_commands.describe(playlist_name="The name of the playlist to add to.", query="A song URL, search term, or YouTube playlist URL.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def playlist_add(self, interaction: discord.Interaction, playlist_name: str, query: str):
        await interaction.response.defer(ephemeral=True)
        
        # This check is good, but filtering by ID ('RD') later is more robust.
        # We can keep this as a quick initial check.
        if 'list=RD' in query:
            await interaction.followup.send("❌ YouTube's auto-generated 'Mix' playlists cannot be added.")
            return
            
        # Fetch track information.
        full_data, error_msg = await self.audio_handler.get_track_info(query, allow_playlist=True)

        if error_msg:
            await interaction.followup.send(error_msg)
            return
            
        user_id = interaction.user.id
        
        # Check if the result is a playlist or a single track.
        if 'entries' in full_data:
            # --- Filtration Filter ---
            # [EN] Helper function to extract only the data we need.
            # [JP] 必要なデータだけを抽出するためのヘルパー関数。
            def extract_core_info(entry):
                return {
                    'title': entry.get('title', 'Unknown Title'),
                    'uploader': entry.get('uploader', 'Unknown Artist'),
                    'duration': entry.get('duration', 0),
                    'webpage_url': entry.get('webpage_url'),
                    'thumbnail': entry.get('thumbnail'),
                }

            # [EN] Apply the filter to each track and also filter out YouTube Mixes.
            # [JP] 各トラックにフィルターを適用し、YouTube Mixも除外します。
            playlist_tracks = [
                extract_core_info(track) for track in full_data['entries']
                if track and not track.get('id', '').startswith('RD')
            ]
            # --- Filtration Ends ---
            
            if not playlist_tracks:
                await interaction.followup.send("❌ No addable tracks found in this playlist.")
                return

            if len(playlist_tracks) > 150:
                await interaction.followup.send(f"❌ You can only add up to 150 tracks at once. (Detected: {len(playlist_tracks)} tracks)")
                return
            
            message = self.playlist_manager.add_tracks(
                scope="solo", 
                owner_id=user_id, 
                playlist_name=playlist_name, 
                tracks=playlist_tracks, # Pass the clean, filtered list
                user=interaction.user
            )
        else:
            # [EN] Even for a single track, filter it to keep data consistent.
            # [JP] 単一の曲でも、データの一貫性を保つためにフィルターをかけます。
            core_track_info = {
                'title': full_data.get('title', 'Unknown Title'),
                'uploader': full_data.get('uploader', 'Unknown Artist'),
                'duration': full_data.get('duration', 0),
                'webpage_url': full_data.get('webpage_url'),
                'thumbnail': full_data.get('thumbnail'),
            }
            
            message = self.playlist_manager.add_track(
                scope="solo", 
                owner_id=user_id, 
                playlist_name=playlist_name, 
                track_info=core_track_info, # Pass the clean, single track info
                user=interaction.user
            )
            
        await interaction.followup.send(message)


    # --- Playlist Playback and Viewing ---

    @app_commands.command(name="playlist_play", description="Plays a specified personal playlist.")
    @app_commands.describe(name="The name of the playlist you want to play.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def playlist_play(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)

        playback_cog = self.bot.get_cog("PlaybackCog")
        if not playback_cog:
            await interaction.followup.send("Error: Playback feature is unavailable.")
            return
        
        player = playback_cog.get_or_create_player(interaction)
        success, _ = await player.connect(interaction)
        if not success: return

        # Retrieve tracks from the specified playlist.
        # 指定されたプレイリストから曲を取得します。
        user_id = interaction.user.id
        tracks = self.playlist_manager.get_playlist(scope="solo", owner_id=user_id, name=name)

        if tracks is None or not tracks:
            await interaction.followup.send(f"❌ Playlist '{name}' not found or is empty.")
            return

        # Delegate adding multiple tracks to the player, which handles it in the background.
        # 複数の曲の追加処理をプレイヤーに委任し、バックグラウンドで処理させます。
        result = await player.add_tracks(interaction, tracks)
        
        if result == -1:
            await interaction.followup.send("⏳ Another playlist is currently being processed. Please wait a moment and try again.")
        else:
            await interaction.followup.send(f"🔄 Started processing {result} tracks from playlist '{name}'. You will be notified when it's ready.")


    @app_commands.command(name="playlist_show", description="Shows your playlists or the contents of one.")
    @app_commands.describe(name="The name of the playlist to show (optional).")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def playlist_show(self, interaction: discord.Interaction, name: str = None):
        user_id = interaction.user.id

        # If no name is provided, list all of the user's playlists.
        # 名前が指定されていない場合、ユーザーの全プレイリストを一覧表示します。
        if name is None:
            all_playlists = self.playlist_manager._load_playlists("solo", user_id)
            if not all_playlists:
                await interaction.response.send_message("You have no personal playlists.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Playlists",
                color=discord.Color.purple()
            )
            desc = [f"📁 **{pl_name}** ({len(tracks)} tracks)" for pl_name, tracks in all_playlists.items()]
            embed.description = "\n".join(desc) if desc else "No playlists found."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # If a name is provided, show the contents of that playlist with pagination.
        # 名前が指定されている場合、そのプレイリストの内容をページネーションで表示します。
        playlist_tracks = self.playlist_manager.get_playlist(scope="solo", owner_id=user_id, name=name)

        if playlist_tracks is None:
            await interaction.response.send_message(f"❌ Playlist '{name}' not found.", ephemeral=True)
            return
        if not playlist_tracks:
            embed = discord.Embed(title=f"Playlist: {name}", description="This playlist is empty.", color=discord.Color.purple())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Paginator setup to display tracks page by page.
        # 曲をページごとに表示するためのページネーター設定。
        items_per_page = 10
        total_pages = math.ceil(len(playlist_tracks) / items_per_page)

        def create_embed_for_page(page_num: int):
            start_index = (page_num - 1) * items_per_page
            end_index = start_index + items_per_page
            page_items = playlist_tracks[start_index:end_index]
            
            track_list = [f"`{start_index + i + 1}.` **{track.get('title', 'Unknown Track')}**" for i, track in enumerate(page_items)]
            description = "\n".join(track_list)

            embed = discord.Embed(title=f"Playlist: {name}", description=description, color=discord.Color.purple())
            embed.set_footer(text=f"Total {len(playlist_tracks)} tracks")
            return embed

        initial_embed = create_embed_for_page(1)
        view = PaginatorView(embed_creator=create_embed_for_page, total_pages=total_pages)
        await interaction.response.send_message(embed=initial_embed, view=view, ephemeral=True)


    # --- Playlist Modification ---

    @app_commands.command(name="playlist_delete", description="Deletes an existing personal playlist.")
    @app_commands.describe(name="The name of the playlist to delete.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def playlist_delete(self, interaction: discord.Interaction, name: str):
        message = self.playlist_manager.delete(
            scope="solo",
            playlist_name=name,
            user=interaction.user
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="playlist_remove_track", description="Removes a specific track from a playlist.")
    @app_commands.describe(playlist_name="The name of the playlist.", number="The number of the track to remove.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def playlist_remove_track(self, interaction: discord.Interaction, playlist_name: str, number: int):
        message = self.playlist_manager.remove_track(
            scope="solo",
            playlist_name=playlist_name,
            track_index=number,
            user=interaction.user
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="playlist_move", description="Moves a track to a new position in a playlist.")
    @app_commands.describe(
        playlist_name="The name of the playlist.",
        from_number="The current number of the track to move.",
        to_number="The new position number for the track."
    )
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def playlist_move(self, interaction: discord.Interaction, playlist_name: str, from_number: int, to_number: int):
        message = self.playlist_manager.move_track(
            scope="solo",
            playlist_name=playlist_name,
            from_index=from_number,
            to_index=to_number,
            user=interaction.user
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="playlist_rename", description="Renames a playlist.")
    @app_commands.describe(old_name="The current name of the playlist.", new_name="The new name for the playlist.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def playlist_rename(self, interaction: discord.Interaction, old_name: str, new_name: str):
        message = self.playlist_manager.rename(
            scope="solo",
            old_name=old_name,
            new_name=new_name,
            user=interaction.user
        )
        await interaction.response.send_message(message, ephemeral=True)



async def setup(bot: commands.Bot):
    """Adds the PlaylistCog to the bot."""
    await bot.add_cog(PlaylistCog(bot))