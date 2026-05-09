# --- English ---
# This module provides the `PlaylistManager` class, the central logic unit for
# managing both personal (`solo`) and shared (`server`) playlists. It handles:
# - Reading from and writing to JSON files for data persistence.
# - Differentiating between solo and server playlist data structures.
# - Enforcing a complex permission model for server playlists (owner, collaborators, lock status).

# --- 日本語 ---
# このモジュールは、個人用（`solo`）と共有（`server`）の両プレイリストを管理するための
# 中心的なロジックである `PlaylistManager` クラスを提供します。以下の責務を担います:
# - データの永続化のためのJSONファイルの読み書き。
# - soloとserverのプレイリストデータ構造の区別。
# - サーバープレイリストにおける複雑な権限モデル（オーナー、協力者、ロック状態）の強制。

import discord
import json
import os
from pathlib import Path



class PlaylistManager:
    """Handles all backend logic for creating, managing, and accessing playlists."""
    def __init__(self, data_path: str = "data/playlists"):
        self.solo_path = Path(data_path) / "solo"
        self.server_path = Path(data_path) / "server"
        self.solo_path.mkdir(parents=True, exist_ok=True)
        self.server_path.mkdir(parents=True, exist_ok=True)


    # --- Internal Helper Methods (File I/O and Permissions) ---

    def _get_playlist_file(self, scope: str, owner_id: int) -> Path:
        """
        Returns the correct file path based on the scope.
        `owner_id` is a user ID for 'solo' scope, and a guild ID for 'server' scope.
        
        scopeに応じて適切なファイルパスを返します。
        `owner_id`は、'solo'スコープではユーザーID、'server'スコープではギルドIDです。
        """
        if scope == "solo":
            return self.solo_path / f"{owner_id}.json"
        elif scope == "server":
            return self.server_path / f"{owner_id}.json"
        else:
            raise ValueError(f"Invalid scope provided: {scope}")


    def _load_playlists(self, scope: str, owner_id: int) -> dict:
        """Loads all playlists for a given scope and ID from its JSON file."""
        file_path = self._get_playlist_file(scope, owner_id)
        if not file_path.exists():
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}


    def _save_playlists(self, scope: str, owner_id: int, playlists: dict):
        """Saves all playlists for a given scope and ID to its JSON file."""
        file_path = self._get_playlist_file(scope, owner_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(playlists, f, indent=4, ensure_ascii=False)


    def has_permission(self, playlist: dict, user: discord.Member) -> bool:
        """
        Checks if a user has permission to modify a server playlist.
        Permission is granted if the user is the owner, a collaborator user, or has a collaborator role.
        
        ユーザーがサーバープレイリストを変更する権限を持っているかを確認します。
        ユーザーがオーナー、協力者ユーザー、または協力者ロールを持っている場合に権限が付与されます。
        """
        if playlist.get('owner') == user.id:
            return True
        if user.id in playlist.get('collaborator_users', []):
            return True

        user_role_ids = {role.id for role in user.roles}
        collaborator_role_ids = set(playlist.get('collaborator_roles', []))
        if not user_role_ids.isdisjoint(collaborator_role_ids):
            return True
            
        return False


    # --- Public API for Playlist Operations ---
    # These methods are called directly from the Cogs.

    def create(self, scope: str, name: str, owner_id: int, guild_id: int = None) -> str:
        """Creates a new, empty playlist for the specified scope."""
        save_id = guild_id if scope == "server" else owner_id
        playlists = self._load_playlists(scope, save_id)
        
        if name in playlists:
            return f"❌ A playlist named '{name}' already exists."
        
        if scope == "solo":
            playlists[name] = []
        elif scope == "server":
            playlists[name] = {
                "owner": owner_id,
                "collaborator_users": [],
                "collaborator_roles": [],
                "locked": False,
                "tracks": []
            }

        self._save_playlists(scope, save_id, playlists)
        return f"✅ Created playlist '{name}'."


    def add_track(self, scope: str, owner_id: int, playlist_name: str, track_info: dict, user: discord.Member = None) -> str:
        """Adds a single track to a playlist, checking permissions for server playlists."""
        save_id = user.guild.id if scope == "server" else owner_id
        playlists = self._load_playlists(scope, save_id)

        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."
            
        # For server playlists, perform a permission check if it's locked.
        # サーバープレイリストの場合、ロックされていれば権限チェックを行います。
        if scope == "server":
            target_playlist = playlists[playlist_name]
            if target_playlist.get('locked', False) and not self.has_permission(target_playlist, user):
                return "❌ This playlist is locked. Only the owner or collaborators can add tracks."
        
        if scope == "solo":
            playlists[playlist_name].append(track_info)
        else:
            playlists[playlist_name]['tracks'].append(track_info)
        
        self._save_playlists(scope, save_id, playlists)
        title = track_info.get('title', 'Unknown Track')
        return f"✅ Added '{title}' to playlist '{playlist_name}'."


    def add_tracks(self, scope: str, owner_id: int, playlist_name: str, tracks: list[dict], user: discord.Member = None) -> str:
        """Adds multiple tracks to a playlist, checking permissions for server playlists."""
        save_id = user.guild.id if scope == "server" else owner_id
        playlists = self._load_playlists(scope, save_id)

        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."
        
        if scope == "server":
            target_playlist = playlists[playlist_name]
            if target_playlist.get('locked', False) and not self.has_permission(target_playlist, user):
                return "❌ This playlist is locked. Only the owner or collaborators can add tracks."

        if scope == "solo":
            playlists[playlist_name].extend(tracks)
        else:
            playlists[playlist_name]['tracks'].extend(tracks)

        self._save_playlists(scope, save_id, playlists)
        return f"✅ Added {len(tracks)} tracks to playlist '{playlist_name}'."


    def get_playlist(self, scope: str, owner_id: int, name: str) -> list | None:
        """Retrieves the list of tracks from a specified playlist."""
        playlists = self._load_playlists(scope, owner_id)
        playlist_data = playlists.get(name)

        if playlist_data is None:
            return None

        return playlist_data.get('tracks', []) if scope == "server" else playlist_data


    def delete(self, scope: str, playlist_name: str, user: discord.Member) -> str:
        """Deletes a playlist, checking for owner/admin permissions for server playlists."""
        save_id = user.guild.id if scope == "server" else user.id
        playlists = self._load_playlists(scope, save_id)

        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."

        if scope == "server":
            target_playlist = playlists[playlist_name]
            if not (target_playlist.get('owner') == user.id or user.guild_permissions.administrator):
                return "❌ This action can only be performed by the playlist owner or a server administrator."
        
        del playlists[playlist_name]
        self._save_playlists(scope, save_id, playlists)
        return f"✅ Deleted playlist '{playlist_name}'."


    def remove_track(self, scope: str, playlist_name: str, track_index: int, user: discord.Member) -> str:
        """Removes a track from a playlist by its 1-based index."""
        save_id = user.guild.id if scope == "server" else user.id
        playlists = self._load_playlists(scope, save_id)

        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."

        target_playlist_data = playlists[playlist_name]
        
        if scope == "server":
            if target_playlist_data.get('locked', False) and not self.has_permission(target_playlist_data, user):
                return "❌ Cannot remove tracks from a locked playlist."
            playlist_tracks = target_playlist_data.get('tracks', [])
        else:
            playlist_tracks = target_playlist_data

        actual_index = track_index - 1
        if not (0 <= actual_index < len(playlist_tracks)):
            return f"❌ Invalid number. Please specify a number between 1 and {len(playlist_tracks)}."

        removed_track = playlist_tracks.pop(actual_index)
        self._save_playlists(scope, save_id, playlists)
        return f"🗑️ Removed '{removed_track.get('title', 'Unknown Track')}'."


    def move_track(self, scope: str, playlist_name: str, from_index: int, to_index: int, user: discord.Member) -> str:
        """Moves a track within a playlist from one 1-based index to another."""
        save_id = user.guild.id if scope == "server" else user.id
        playlists = self._load_playlists(scope, save_id)

        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."

        target_playlist_data = playlists[playlist_name]
        
        if scope == "server":
            if not self.has_permission(target_playlist_data, user):
                return "❌ This action can only be performed by the owner or a collaborator."
            playlist_tracks = target_playlist_data.get('tracks', [])
        else:
            playlist_tracks = target_playlist_data

        actual_from = from_index - 1
        actual_to = to_index - 1

        if not (0 <= actual_from < len(playlist_tracks) and 0 <= actual_to < len(playlist_tracks)):
            return "❌ Invalid number. Check the 'from' and 'to' positions."

        moved_track = playlist_tracks.pop(actual_from)
        playlist_tracks.insert(actual_to, moved_track)

        self._save_playlists(scope, save_id, playlists)
        return f"✅ Moved '{moved_track.get('title', 'Unknown Track')}' to position {to_index}."


    def rename(self, scope: str, old_name: str, new_name: str, user: discord.Member) -> str:
        """Renames a playlist, checking for owner permissions for server playlists."""
        save_id = user.guild.id if scope == "server" else user.id
        playlists = self._load_playlists(scope, save_id)

        if old_name not in playlists:
            return f"❌ Playlist '{old_name}' not found."
        if new_name in playlists:
            return f"❌ A playlist named '{new_name}' already exists."

        if scope == "server":
            if playlists[old_name].get('owner') != user.id:
                return "❌ This action can only be performed by the playlist owner."
        
        playlists[new_name] = playlists.pop(old_name)
        self._save_playlists(scope, save_id, playlists)
        return f"✅ Renamed playlist from '{old_name}' to '{new_name}'."


    # --- Server Playlist Permission Management (Owner-Only) ---

    def toggle_lock(self, guild_id: int, playlist_name: str, user_id: int) -> str:
        """Toggles the lock on a server playlist. Only the owner can perform this action."""
        playlists = self._load_playlists(scope="server", owner_id=guild_id)
        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."
            
        target_playlist = playlists[playlist_name]
        if target_playlist.get('owner') != user_id:
            return "❌ This action can only be performed by the playlist owner."
            
        current_state = target_playlist.get('locked', False)
        target_playlist['locked'] = not current_state
        self._save_playlists(scope="server", owner_id=guild_id, playlists=playlists)
        
        new_state_text = "locked 🔐" if not current_state else "unlocked 🔓"
        return f"✅ Playlist '{playlist_name}' is now {new_state_text}."


    def add_collaborator_user(self, guild_id: int, playlist_name: str, owner_id: int, target_user: discord.User) -> str:
        """Adds a user as a collaborator to a server playlist. Owner-only."""
        playlists = self._load_playlists(scope="server", owner_id=guild_id)
        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."
        target_playlist = playlists[playlist_name]

        if target_playlist.get('owner') != owner_id:
            return "❌ This action can only be performed by the playlist owner."
        if target_user.id in target_playlist.get('collaborator_users', []):
            return f"ℹ️ {target_user.mention} is already a collaborator."

        target_playlist.setdefault('collaborator_users', []).append(target_user.id)
        self._save_playlists(scope="server", owner_id=guild_id, playlists=playlists)
        return f"✅ Added {target_user.mention} as a collaborator to '{playlist_name}'."


    def remove_collaborator_user(self, guild_id: int, playlist_name: str, owner_id: int, target_user: discord.User) -> str:
        """Removes a user from the collaborator list of a server playlist. Owner-only."""
        playlists = self._load_playlists(scope="server", owner_id=guild_id)
        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."
        target_playlist = playlists[playlist_name]

        if target_playlist.get('owner') != owner_id:
            return "❌ This action can only be performed by the playlist owner."
        if target_user.id not in target_playlist.get('collaborator_users', []):
            return f"ℹ️ {target_user.mention} is not a collaborator."

        target_playlist['collaborator_users'].remove(target_user.id)
        self._save_playlists(scope="server", owner_id=guild_id, playlists=playlists)
        return f"✅ Removed {target_user.mention} from collaborators of '{playlist_name}'."


    def add_collaborator_role(self, guild_id: int, playlist_name: str, owner_id: int, target_role: discord.Role) -> str:
        """Adds a role as a collaborator to a server playlist. Owner-only."""
        playlists = self._load_playlists(scope="server", owner_id=guild_id)
        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."
        target_playlist = playlists[playlist_name]

        if target_playlist.get('owner') != owner_id:
            return "❌ This action can only be performed by the playlist owner."
        if target_role.id in target_playlist.get('collaborator_roles', []):
            return f"ℹ️ The role '{target_role.name}' is already a collaborator."

        target_playlist.setdefault('collaborator_roles', []).append(target_role.id)
        self._save_playlists(scope="server", owner_id=guild_id, playlists=playlists)
        return f"✅ Added the role '{target_role.name}' as a collaborator to '{playlist_name}'."


    def remove_collaborator_role(self, guild_id: int, playlist_name: str, owner_id: int, target_role: discord.Role) -> str:
        """Removes a role from the collaborator list of a server playlist. Owner-only."""
        playlists = self._load_playlists(scope="server", owner_id=guild_id)
        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."
        target_playlist = playlists[playlist_name]

        if target_playlist.get('owner') != owner_id:
            return "❌ This action can only be performed by the playlist owner."
        if target_role.id not in target_playlist.get('collaborator_roles', []):
            return f"ℹ️ The role '{target_role.name}' is not a collaborator."

        target_playlist['collaborator_roles'].remove(target_role.id)
        self._save_playlists(scope="server", owner_id=guild_id, playlists=playlists)
        return f"✅ Removed the role '{target_role.name}' from collaborators of '{playlist_name}'."


    def transfer_ownership(self, guild_id: int, playlist_name: str, current_owner_id: int, new_owner: discord.User) -> str:
        """Transfers ownership of a server playlist to another user. Current owner only."""
        playlists = self._load_playlists(scope="server", owner_id=guild_id)
        if playlist_name not in playlists:
            return f"❌ Playlist '{playlist_name}' not found."
        target_playlist = playlists[playlist_name]
        
        if target_playlist.get('owner') != current_owner_id:
            return "❌ This action can only be performed by the current playlist owner."
        if current_owner_id == new_owner.id:
            return "ℹ️ You cannot transfer ownership to yourself."

        target_playlist['owner'] = new_owner.id
        if new_owner.id in target_playlist.get('collaborator_users', []):
            target_playlist['collaborator_users'].remove(new_owner.id)

        self._save_playlists(scope="server", owner_id=guild_id, playlists=playlists)
        return f"✅ Transferred ownership of playlist '{playlist_name}' to {new_owner.mention}."
