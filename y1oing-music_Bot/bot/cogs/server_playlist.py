# --- English ---
# This Cog manages commands for server-wide (shared) playlists.
# It includes functionality for creating, managing, and playing playlists that
# are accessible to members of a server, with a permission system that
# distinguishes between general users, playlist owners, and server administrators.

# --- 日本語 ---
# このCogは、サーバー全体で共有されるプレイリストのコマンドを管理します。
# サーバーのメンバーがアクセス可能なプレイリストの作成、管理、再生機能が含まれており、
# 一般ユーザー、プレイリストのオーナー、サーバー管理者で区別された権限システムを持っています。

import discord
from discord import app_commands
from discord.ext import commands
from utils.playlist_manager import PlaylistManager
from utils.audio_handler import AudioHandler
from utils.views import PaginatorView
import math
from discord.app_commands import checks


# --- Custom Permission Checks ---

def is_admin():
    """
    A custom check to verify if the interacting user has administrator permissions.
    This is used as a decorator for admin-only commands.
    
    コマンド実行者が管理者権限を持っているかを確認するカスタムチェックです。
    管理者専用コマンドのデコレータとして使用します。
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        return interaction.user.guild_permissions.administrator
    
    return app_commands.check(predicate)



class ServerPlaylistCog(commands.Cog):
    """Cog for server-wide (shared) playlist commands."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.playlist_manager = PlaylistManager()
        self.audio_handler = AudioHandler()


    # --- General Playlist Commands (View, Play, Add) ---

    @app_commands.command(name="serverplaylist_show", description="Shows server playlists or the contents of one.")
    @app_commands.describe(name="The name of the playlist to show (optional).")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_show(self, interaction: discord.Interaction, name: str = None):
        guild_id = interaction.guild.id
        
        # Case 1: No name provided -> List all server playlists.
        # ケース1: 名前がない場合 -> サーバーの全プレイリストを一覧表示。
        if name is None:
            all_server_playlists = self.playlist_manager._load_playlists("server", guild_id)
            if not all_server_playlists:
                await interaction.response.send_message("There are no shared playlists on this server yet.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"Shared Playlists in '{interaction.guild.name}'",
                color=discord.Color.orange()
            )
            
            desc = []
            for pl_name, pl_data in all_server_playlists.items():
                owner_id = pl_data.get('owner')
                owner = interaction.guild.get_member(owner_id)
                owner_name = owner.display_name if owner else f"ID: {owner_id}"
                track_count = len(pl_data.get('tracks', []))
                lock_status = "🔐" if pl_data.get('locked', False) else ""
                
                desc.append(f"📁 **{pl_name}** {lock_status}\n> Owner: {owner_name}, Tracks: {track_count}")
            
            embed.description = "\n\n".join(desc) if desc else "No playlists found."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Case 2: Name provided -> Show playlist contents with pagination.
        # ケース2: 名前がある場合 -> プレイリストの内容をページネーションで表示。
        playlist_tracks = self.playlist_manager.get_playlist(scope="server", owner_id=guild_id, name=name)

        if playlist_tracks is None:
            await interaction.response.send_message(f"❌ Shared playlist '{name}' not found.", ephemeral=True)
            return
        if not playlist_tracks:
            embed = discord.Embed(title=f"Server Playlist: {name}", description="This playlist is empty.", color=discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        items_per_page = 10
        total_pages = math.ceil(len(playlist_tracks) / items_per_page)

        def create_embed_for_page(page_num: int):
            start_index = (page_num - 1) * items_per_page
            end_index = start_index + items_per_page
            page_items = playlist_tracks[start_index:end_index]
            track_list = [f"`{start_index + i + 1}.` **{track.get('title', 'Unknown Track')}**" for i, track in enumerate(page_items)]
            description = "\n".join(track_list)
            embed = discord.Embed(title=f"Server Playlist: {name}", description=description, color=discord.Color.orange())
            embed.set_footer(text=f"Total {len(playlist_tracks)} tracks")
            return embed

        initial_embed = create_embed_for_page(1)
        view = PaginatorView(embed_creator=create_embed_for_page, total_pages=total_pages)
        await interaction.response.send_message(embed=initial_embed, view=view, ephemeral=True)


    @app_commands.command(name="serverplaylist_play", description="Plays a shared server playlist.")
    @app_commands.describe(name="The name of the playlist you want to play.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_play(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)

        playback_cog = self.bot.get_cog("PlaybackCog")
        if not playback_cog:
            await interaction.followup.send("Error: Playback feature is unavailable.")
            return
        player = playback_cog.get_or_create_player(interaction)

        success, _ = await player.connect(interaction)
        if not success: return

        server_id = interaction.guild.id
        tracks = self.playlist_manager.get_playlist(scope="server", owner_id=server_id, name=name)

        if tracks is None or not tracks:
            await interaction.followup.send(f"❌ Server playlist '{name}' not found or is empty.")
            return

        added_count = await player.add_tracks(interaction, tracks)
        
        if added_count > 0:
            await interaction.followup.send(f"✅ Started processing {added_count} tracks from the server playlist '{name}'.")
        else:
            await interaction.followup.send(f"❌ Could not process tracks from the playlist.")


    @app_commands.command(name="serverplaylist_add", description="Adds a song or YouTube playlist to a shared playlist.")
    @app_commands.describe(playlist_name="The name of the playlist to add to.", query="Song URL, search term, or YouTube playlist URL.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_add(self, interaction: discord.Interaction, playlist_name: str, query: str):
        await interaction.response.defer(ephemeral=True)

        if 'list=RD' in query:
            await interaction.followup.send("❌ YouTube's auto-generated 'Mix' playlists cannot be added.")
            return

        full_data, error_msg = await self.audio_handler.get_track_info(query, allow_playlist=True)

        if error_msg:
            await interaction.followup.send(error_msg)
            return

        server_id = interaction.guild.id
        
        if 'entries' in full_data:
            # --- Filtration Filter ---
            def extract_core_info(entry):
                return {
                    'title': entry.get('title', 'Unknown Title'),
                    'uploader': entry.get('uploader', 'Unknown Artist'),
                    'duration': entry.get('duration', 0),
                    'webpage_url': entry.get('webpage_url'),
                    'thumbnail': entry.get('thumbnail'),
                }

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
                scope="server", 
                owner_id=server_id, 
                playlist_name=playlist_name, 
                tracks=playlist_tracks, 
                user=interaction.user
            )
        else:
            core_track_info = {
                'title': full_data.get('title', 'Unknown Title'),
                'uploader': full_data.get('uploader', 'Unknown Artist'),
                'duration': full_data.get('duration', 0),
                'webpage_url': full_data.get('webpage_url'),
                'thumbnail': full_data.get('thumbnail'),
            }

            message = self.playlist_manager.add_track(
                scope="server", 
                owner_id=server_id, 
                playlist_name=playlist_name, 
                track_info=core_track_info, 
                user=interaction.user
            )
            
        await interaction.followup.send(message)


    @app_commands.command(name="serverplaylist_remove_track", description="Removes a specific track from a shared playlist.")
    @app_commands.describe(playlist_name="The name of the playlist.", number="The number of the track to remove.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_remove_track(self, interaction: discord.Interaction, playlist_name: str, number: int):
        message = self.playlist_manager.remove_track(
            scope="server", playlist_name=playlist_name, track_index=number, user=interaction.user
        )
        await interaction.response.send_message(message, ephemeral=True)


    # --- Playlist Management (Admin/Owner) ---

    @app_commands.command(name="serverplaylist_create", description="[Admin] Creates a new shared server playlist.")
    @app_commands.describe(name="The name of the new playlist.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    @is_admin()
    async def serverplaylist_create(self, interaction: discord.Interaction, name: str):
        message = self.playlist_manager.create(
            scope="server", name=name, owner_id=interaction.user.id, guild_id=interaction.guild.id
        )
        await interaction.response.send_message(message, ephemeral=True)

    @serverplaylist_create.error
    async def on_create_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        # Handles the error when the `is_admin` check fails.
        # `is_admin` チェックが失敗したときのエラーを処理します。
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ This command can only be used by server administrators.", ephemeral=True)
        else:
            print(error)
            await interaction.response.send_message("An error occurred while executing the command.", ephemeral=True)


    @app_commands.command(name="serverplaylist_delete", description="[Owner/Admin] Deletes a shared playlist.")
    @app_commands.describe(name="The name of the playlist to delete.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_delete(self, interaction: discord.Interaction, name: str):
        message = self.playlist_manager.delete(
            scope="server", playlist_name=name, user=interaction.user
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="serverplaylist_rename", description="[Owner] Renames a shared playlist.")
    @app_commands.describe(playlist_name="The current name of the playlist.", new_name="The new name for the playlist.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_rename(self, interaction: discord.Interaction, playlist_name: str, new_name: str):
        message = self.playlist_manager.rename(
            scope="server", playlist_name=playlist_name, new_name=new_name, user=interaction.user
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="serverplaylist_move", description="[Owner] Moves a track to a new position in a shared playlist.")
    @app_commands.describe(playlist_name="The playlist name.", from_number="Current track number.", to_number="New track number.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_move(self, interaction: discord.Interaction, playlist_name: str, from_number: int, to_number: int):
        message = self.playlist_manager.move_track(
            scope="server", playlist_name=playlist_name, from_index=from_number, to_index=to_number, user=interaction.user
        )
        await interaction.response.send_message(message, ephemeral=True)


    # --- Ownership & Permission Management (Owner-Only) ---

    @app_commands.command(name="serverplaylist_lock", description="[Owner] Toggles the lock on a shared playlist.")
    @app_commands.describe(name="The name of the playlist to lock/unlock.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_lock(self, interaction: discord.Interaction, name: str):
        message = self.playlist_manager.toggle_lock(
            guild_id=interaction.guild.id, playlist_name=name, user_id=interaction.user.id
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="serverplaylist_add_user", description="[Owner] Adds a user as a collaborator to a playlist.")
    @app_commands.describe(name="The playlist name.", user="The user to add as a collaborator.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_add_user(self, interaction: discord.Interaction, name: str, user: discord.User):
        message = self.playlist_manager.add_collaborator_user(
            guild_id=interaction.guild.id, playlist_name=name, owner_id=interaction.user.id, target_user=user
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="serverplaylist_remove_user", description="[Owner] Removes a user collaborator from a playlist.")
    @app_commands.describe(name="The playlist name.", user="The user to remove from collaborators.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_remove_user(self, interaction: discord.Interaction, name: str, user: discord.User):
        message = self.playlist_manager.remove_collaborator_user(
            guild_id=interaction.guild.id, playlist_name=name, owner_id=interaction.user.id, target_user=user
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="serverplaylist_add_role", description="[Owner] Adds a role as a collaborator to a playlist.")
    @app_commands.describe(name="The playlist name.", role="The role to add as a collaborator.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_add_role(self, interaction: discord.Interaction, name: str, role: discord.Role):
        message = self.playlist_manager.add_collaborator_role(
            guild_id=interaction.guild.id, playlist_name=name, owner_id=interaction.user.id, target_role=role
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="serverplaylist_remove_role", description="[Owner] Removes a role collaborator from a playlist.")
    @app_commands.describe(name="The playlist name.", role="The role to remove from collaborators.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_remove_role(self, interaction: discord.Interaction, name: str, role: discord.Role):
        message = self.playlist_manager.remove_collaborator_role(
            guild_id=interaction.guild.id, playlist_name=name, owner_id=interaction.user.id, target_role=role
        )
        await interaction.response.send_message(message, ephemeral=True)


    @app_commands.command(name="serverplaylist_transfer", description="[Owner] Transfers ownership of a playlist to another user.")
    @app_commands.describe(name="The playlist name.", user="The user to become the new owner.")
    @checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def serverplaylist_transfer(self, interaction: discord.Interaction, name: str, user: discord.User):
        if user.bot:
            await interaction.response.send_message("❌ Cannot transfer ownership to a bot.", ephemeral=True)
            return

        message = self.playlist_manager.transfer_ownership(
            guild_id=interaction.guild.id, playlist_name=name, current_owner_id=interaction.user.id, new_owner=user
        )
        await interaction.response.send_message(message, ephemeral=True)



async def setup(bot: commands.Bot):
    """Adds the ServerPlaylistCog to the bot."""
    await bot.add_cog(ServerPlaylistCog(bot))
