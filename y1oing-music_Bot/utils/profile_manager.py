# --- English ---
# This module provides the `ProfileManager` class, which handles the persistence
# of user-specific settings. It saves and loads user profiles as JSON files,
# allowing data like custom volume settings to be retained between sessions.

# --- 日本語 ---
# このモジュールは、ユーザー固有の設定の永続化を担う `ProfileManager` クラスを提供します。
# ユーザープロフィールをJSONファイルとして保存・読み込みすることで、
# カスタム音量設定などのデータがセッション間で保持されるようにします。

import json
from pathlib import Path
import discord



class ProfileManager:
    """Manages loading and saving user profile data to/from JSON files."""
    def __init__(self, data_path: str = "data/profiles"):
        # Ensure the directory for storing profiles exists.
        # プロフィールを保存するディレクトリが存在することを確認します。
        self.profiles_path = Path(data_path)
        self.profiles_path.mkdir(parents=True, exist_ok=True)


    def _get_profile_file(self, user_id: int) -> Path:
        """Constructs the file path for a user's profile."""
        return self.profiles_path / f"{user_id}.json"


    def _get_default_profile(self) -> dict:
        """
        Returns a dictionary containing the default profile settings.
        This is used for new users or when a profile file is corrupted.
        
        デフォルトのプロフィール設定を含む辞書を返します。
        新規ユーザーやプロフィールファイルが破損している場合に使用されます。
        """
        return {
            "volume": 100,
            "eq_mode": "balanced", # default equalizer mode
            # "equalizer": "flat"  // Future feature placeholder
        }


    def load_profile(self, user_id: int) -> dict:
        """
        Loads a user's profile from a JSON file.
        If the file doesn't exist or is invalid, returns the default profile.
        
        ユーザーのプロフィールをJSONファイルから読み込みます。
        ファイルが存在しないか無効な場合、デフォルトのプロフィールを返します。
        """
        file_path = self._get_profile_file(user_id)
        if not file_path.exists():
            return self._get_default_profile()
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Start with default settings and overwrite with saved values.
                # デフォルト設定を基に、保存された値で上書きします。
                profile_data = self._get_default_profile()
                profile_data.update(json.load(f))
                return profile_data
        except (json.JSONDecodeError, TypeError):
            # In case of file corruption, return default settings to prevent crashes.
            # ファイルが破損している場合、クラッシュを防ぐためにデフォルト設定を返します。
            return self._get_default_profile()


    def save_profile(self, user_id: int, profile_data: dict):
        """
        Saves a user's profile data to a JSON file.
        
        ユーザーのプロフィールデータをJSONファイルに保存します。
        """
        file_path = self._get_profile_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=4, ensure_ascii=False)
