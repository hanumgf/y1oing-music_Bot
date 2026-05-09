# --- English ---
# This module defines reusable UI components (`discord.ui.View`) for the bot.
# These views provide interactive elements like buttons and dropdown menus for:
# - The main playback control panel (`ControlPanelView`).
# - A paginator for long lists like playlists (`PaginatorView`).
# - An interactive search result selector (`SearchView`).

# --- 日本語 ---
# このモジュールは、ボットで再利用可能なUIコンポーネント（`discord.ui.View`）を定義します。
# これらのビューは、以下のようなボタンやドロップダウンメニューなどの対話的な要素を提供します:
# - メインの再生コントロールパネル（`ControlPanelView`）。
# - プレイリストなどの長いリストを表示するためのページネーター（`PaginatorView`）。
# - 対話的な検索結果セレクター（`SearchView`）。

import discord
import time
from utils.player import Player


# --- Main Playback Control Panel ---

class ControlPanelView(discord.ui.View):
    """
    An interactive control panel for music playback, featuring buttons for play/pause,
    skip, volume control, loop modes, and stopping playback.
    
    再生/一時停止、スキップ、音量調整、ループモード、再生停止のボタンを備えた、
    音楽再生用のインタラクティブなコントロールパネルです。
    """
    def __init__(self, player):
        super().__init__(timeout=None)
        self.player = player
        self.cooldowns = {} # Tracks the last usage time for each button to enforce cooldowns.


    def is_on_cooldown(self, button_id: str, duration: float) -> float | None:
        """
        Checks if a button is on cooldown.
        Returns the remaining cooldown time in seconds, or None if it's ready.
        
        ボタンがクールダウン中か確認します。
        クールダウン中であれば残り時間（秒）を、そうでなければNoneを返します。
        """
        last_used = self.cooldowns.get(button_id, 0)
        elapsed = time.time() - last_used
        
        if elapsed < duration:
            return duration - elapsed
        
        self.cooldowns[button_id] = time.time()
        return None


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures the bot is in a voice channel before processing any button press."""
        if not self.player or not self.player.voice_client or not self.player.voice_client.is_connected():
            await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)
            return False
        return True


    # --- Button Definitions ---


    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="previous_button", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Defer immediately to acknowledge the interaction.
        await interaction.response.defer()
        
        # 2. Perform all checks.
        if not self.player.history:
            await interaction.followup.send("No previous tracks in history.", ephemeral=True)
            return
        if remaining := self.is_on_cooldown("previous", 4.0):
            await interaction.followup.send(f"⏳ Please wait {round(remaining, 1)}s.", ephemeral=True)
            return

        # 3. Execute the main action.
        self.player.previous()


    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="pause_resume_button", row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Defer immediately.
        await interaction.response.defer()

        # 2. Check cooldown.
        if remaining := self.is_on_cooldown("pause_resume", 2.0):
            await interaction.followup.send(f"⏳ Please wait {round(remaining, 1)}s.", ephemeral=True)
            return
        
        # 3. Execute the main action. These methods update the panel internally.
        if self.player.voice_client and self.player.voice_client.is_paused():
            await self.player.resume()
        else:
            await self.player.pause()


    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="skip_button", row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Defer immediately.
        await interaction.response.defer()
        
        # 2. Perform all checks.
        if not self.player.is_playing:
            await interaction.followup.send("Nothing to skip.", ephemeral=True)
            return
        if remaining := self.is_on_cooldown("skip", 2.0):
            await interaction.followup.send(f"⏳ Please wait {round(remaining, 1)}s.", ephemeral=True)
            return
            
        # 3. Execute the main action.
        self.player.skip()


    @discord.ui.button(label="➖", style=discord.ButtonStyle.secondary, custom_id="volume_down_button", row=1)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if remaining := self.is_on_cooldown("volume", 1.0):
            await interaction.followup.send(f"⏳ Please wait {round(remaining, 1)}s.", ephemeral=True)
            return
        current_volume = int(self.player.volume * 100)
        new_volume = max(0, current_volume - 10)
        await self.handle_volume_change(interaction, new_volume)


    @discord.ui.button(label="🔊 100%", style=discord.ButtonStyle.grey, disabled=True, custom_id="volume_display_button", row=1)
    async def volume_display(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass # This button is for display purposes only.


    @discord.ui.button(label="➕", style=discord.ButtonStyle.secondary, custom_id="volume_up_button", row=1)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if remaining := self.is_on_cooldown("volume", 1.0): # Shares cooldown with volume_down.
            await interaction.followup.send(f"⏳ Please wait {round(remaining, 1)}s.", ephemeral=True)
            return
        current_volume = int(self.player.volume * 100)
        new_volume = min(200, current_volume + 10)
        await self.handle_volume_change(interaction, new_volume)


    @discord.ui.button(emoji="🔄", label="Off", style=discord.ButtonStyle.secondary, custom_id="loop_button", row=2)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if remaining := self.is_on_cooldown("loop", 2.0):
            await interaction.followup.send(f"⏳ Please wait {round(remaining, 1)}s.", ephemeral=True)
            return
        
        new_mode_name = self.player.toggle_loop()
        self.update_all_buttons()
        await interaction.edit_original_response(view=self) # Use edit_original_response after defer.
        await interaction.followup.send(f"Loop mode set to **{new_mode_name}**.", ephemeral=True)


    @discord.ui.button(emoji="⏹️", label="Stop", style=discord.ButtonStyle.danger, custom_id="stop_button", row=2)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if not self.player.is_playing:
            await interaction.followup.send("Nothing is playing.", ephemeral=True)
            return
        if remaining := self.is_on_cooldown("stop", 4.0):
            await interaction.followup.send(f"⏳ Please wait {round(remaining, 1)}s.", ephemeral=True)
            return
        await self.player.stop()
    

    # --- Helper Methods ---

    async def handle_volume_change(self, interaction: discord.Interaction, new_volume_percent: int):
        """
        A helper to unify volume change logic. It sets the player volume,
        saves it to the user's profile, and updates the view.
        
        音量変更ロジックを統一するヘルパー。プレイヤーの音量を設定し、
        ユーザーのプロフィールに保存して、ビューを更新します。
        """
        await self.player.set_volume(new_volume_percent)
        profile_cog = self.player.bot.get_cog("ProfileCog")
        if profile_cog:
            profile_data = profile_cog.profile_manager.load_profile(interaction.user.id)
            profile_data['volume'] = new_volume_percent
            profile_cog.profile_manager.save_profile(interaction.user.id, profile_data)
        self.update_all_buttons()
        await interaction.edit_original_response(view=self)


    def update_all_buttons(self):
        """Updates the visual state of all buttons to match the current player state."""
        self.update_loop_button()
        self.update_pause_resume_button()
        self.update_volume_buttons()


    def update_loop_button(self):
        """Updates the loop button's style, emoji, and label based on the current loop mode."""
        loop_button = discord.utils.get(self.children, custom_id="loop_button")
        if not loop_button: return
        mode = self.player.loop_mode
        if mode == "off": loop_button.style=discord.ButtonStyle.secondary; loop_button.emoji="🔄"; loop_button.label="Off"
        elif mode == "track": loop_button.style=discord.ButtonStyle.success; loop_button.emoji="🔂"; loop_button.label="Track"
        elif mode == "queue": loop_button.style=discord.ButtonStyle.success; loop_button.emoji="🔁"; loop_button.label="Queue"


    def update_pause_resume_button(self):
        """Updates the pause/resume button's emoji based on the player's paused state."""
        pause_button = discord.utils.get(self.children, custom_id="pause_resume_button")
        if not pause_button: return
        if self.player.voice_client and self.player.voice_client.is_paused():
            pause_button.emoji = "▶️"
        else:
            pause_button.emoji = "⏯️"


    def update_volume_buttons(self):
        """Updates the volume display and enables/disables the control buttons."""
        display_button = discord.utils.get(self.children, custom_id="volume_display_button")
        if not display_button: return
        current_volume = int(self.player.volume * 100)
        display_button.label = f"🔊 {current_volume}%"
        down_button = discord.utils.get(self.children, custom_id="volume_down_button")
        up_button = discord.utils.get(self.children, custom_id="volume_up_button")
        if down_button: down_button.disabled = current_volume == 0
        if up_button: up_button.disabled = current_volume == 200



# --- Generic Paginator View ---

class PaginatorView(discord.ui.View):
    """
    A generic paginator view that can be used to display any list of items in pages.
    
    あらゆるアイテムのリストをページ単位で表示するために使用できる汎用的なページネータービューです。
    """
    def __init__(self, embed_creator, total_pages: int, timeout=180):
        super().__init__(timeout=timeout)
        self.embed_creator = embed_creator # A function that creates an embed for a given page number.
        self.current_page = 1
        self.total_pages = total_pages
        self.update_buttons()


    def update_buttons(self):
        """Enables/disables navigation buttons based on the current page."""
        self.children[0].disabled = self.current_page == 1
        self.children[1].disabled = self.current_page == self.total_pages
        self.children[2].label = f"Page {self.current_page}/{self.total_pages}"


    @discord.ui.button(label="⏪", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 1:
            self.current_page -= 1
            embed = self.embed_creator(self.current_page)
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(label="⏩", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages:
            self.current_page += 1
            embed = self.embed_creator(self.current_page)
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.grey, disabled=True)
    async def page_display(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass # This button is for display only.



# --- YouTube Search Result View ---

class SearchView(discord.ui.View):
    """
    A view specifically for displaying YouTube search results. It includes a dropdown
    menu to select a track and buttons to navigate through pages of results.
    
    YouTubeの検索結果を表示するための専用ビュー。トラックを選択するためのドロップダウンメニューと、
    結果のページを移動するためのボタンが含まれています。
    """
    def __init__(self, interaction: discord.Interaction, tracks: list, player: 'Player'):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.tracks = tracks
        self.player = player
        self.current_page = 0
        self.items_per_page = 10
        self.update_components()


    def update_components(self):
        """Clears and rebuilds the view's components for the current page."""
        self.clear_items()
        self.add_item(self.create_select())
        # 修正: 要素数がピッタリ10個などの時に空のページが生成されないよう計算式を修正
        max_page = max(0, (len(self.tracks) - 1) // self.items_per_page)
        self.add_item(PageButton(label="⏪ Previous", direction=-1, current_page=self.current_page))
        self.add_item(PageButton(label="Next ⏩", direction=1, current_page=self.current_page, max_page=max_page))

    def create_select(self) -> discord.ui.Select:
        """Creates the dropdown select menu for the current page of tracks."""
        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        options = []
        for i, track in enumerate(self.tracks[start_index:end_index], start=start_index):
            options.append(discord.SelectOption(
                label=f"{i+1}. {track.get('title', 'Unknown Title')[:80]}",
                description=f"👤 {track.get('uploader', 'Unknown')} | 🕒 {time.strftime('%M:%S', time.gmtime(track.get('duration', 0)))}",
                value=str(i)
            ))
        return TrackSelect(options=options)



class PageButton(discord.ui.Button):
    """A button for navigating pages in the SearchView."""
    def __init__(self, label: str, direction: int, current_page: int = 0, max_page: int = 99):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.direction = direction
        if direction == -1 and current_page == 0:
            self.disabled = True
        if direction == 1 and current_page >= max_page:
            self.disabled = True

    async def callback(self, interaction: discord.Interaction):
        view: SearchView = self.view
        view.current_page += self.direction
        view.update_components()
        await interaction.response.edit_message(view=view)

class TrackSelect(discord.ui.Select):
    """The dropdown menu for selecting a track from search results."""
    def __init__(self, options):
        super().__init__(placeholder="Select a track to play...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view: SearchView = self.view
        track_index = int(self.values[0])
        selected_track_metadata = view.tracks[track_index]
        
        # Connect to VC if not already connected.
        success, _ = await view.player.connect(interaction)
        if not success:
            try:
                await interaction.followup.send("Failed to connect to the voice channel.", ephemeral=True)
            except discord.errors.InteractionResponded:
                pass
            return
            
        # Add the selected track to the queue via the official player method.
        video_url = selected_track_metadata.get('url') or selected_track_metadata.get('webpage_url')
        if not video_url:
            await interaction.followup.send("❌ Could not find the URL for the selected track.", ephemeral=True)
            return

        reception_message = await view.player.add_to_queue(interaction, video_url)
        
        # Display the result and remove the search panel.
        #await view.interaction.edit_original_response(content=reception_message, view=None, embed=None)
        await interaction.edit_original_response(content=reception_message, view=None, embed=None)
