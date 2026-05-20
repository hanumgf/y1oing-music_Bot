# --- English ---
# This module defines the `Player` class, which is the heart of the music bot's
# functionality for a single server (guild). It acts as a state machine that manages:
# - The music queue and playback history (`deque`).
# - The connection to a voice channel (`voice_client`).
# - A persistent main loop (`player_loop`) that runs in the background.
# - State flags and `asyncio.Event`s to control the loop's behavior.
# - A public API for Cogs to interact with (e.g., `add_to_queue`, `skip`, `pause`).

# --- 日本語 ---
# このモジュールは、単一サーバー（ギルド）における音楽ボット機能の心臓部である`Player`クラスを定義します。
# 以下の要素を管理するステートマシンとして機能します:
# - 音楽キューと再生履歴（`deque`）。
# - ボイスチャンネルへの接続（`voice_client`）。
# - バックグラウンドで動作し続ける永続的なメインループ（`player_loop`）。
# - ループの動作を制御するための状態フラグと`asyncio.Event`。
# - Cogが対話するための公開API（例: `add_to_queue`, `skip`, `pause`）。

import asyncio
import discord
from .audio_handler import AudioHandler
from collections import deque
import time



class Player:
    """Manages the entire playback lifecycle for a single guild."""
    def __init__(self, bot, guild_id: int):
        # --- Core Attributes ---
        self.bot = bot
        self.guild_id = guild_id
        self.audio_handler = AudioHandler()
        
        # --- Discord Objects ---
        self.voice_client = None
        self.text_channel = None
        self.now_playing_message = None

        # --- Playback State ---
        self.queue = deque()
        self.history = deque(maxlen=50)
        self.current_track = None
        self.is_playing = False
        self.loop_mode = "off"  # "off", "track", or "queue"
        self.volume = 1.0  # Represents 100%
        self.eq_mode = "balanced"  # Default equalizer mode

        # --- State Flags for Loop Control ---
        self.stop_requested = False
        self.skip_requested = False
        self.is_previous_request = False
        self.is_cleaning_up = False
        self.was_stopped = False

        # --- Synchronization & Timing ---
        self.song_finished = asyncio.Event()
        self.queue_added = asyncio.Event()
        self.expected_end_time = 0
        self.playback_start_time = 0
        self.paused_time = 0
        self.paused_duration = 0

        # --- Background Tasks ---
        self.player_task = self.bot.loop.create_task(self.player_loop())
        self.panel_update_task = None
        self.add_tracks_task = None
        self.autoleave_task = None
        self.empty_channel_leavetask = None


    # --- Core Player Engine ---

    async def player_loop(self):
        """
        The main event loop for the player. It continuously processes the queue.
        This loop is designed to run for the entire lifetime of the Player instance.
        The `try...finally` block ensures that cleanup is always performed, preventing resource leaks.
        
        プレイヤーのメインイベントループ。継続的にキューを処理します。
        このループはPlayerインスタンスの生存期間中、常に実行されるように設計されています。
        `try...finally`ブロックにより、リソースリークを防ぐためのクリーンアップが常に保証されます。
        """
        await self.bot.wait_until_ready()
        
        try:
            while not self.bot.is_closed():
                self.song_finished.clear()
                self.queue_added.clear()
                
                # [Post-Playback Phase] Handle the previously finished track based on state flags.
                if self.current_track:
                    if self.is_previous_request:
                        self.queue.appendleft(self.current_track)
                        if self.history:
                            self.queue.appendleft(self.history.pop())
                    elif self.skip_requested:
                        self.history.append(self.current_track)
                    else: # Natural song end
                        if self.loop_mode == 'track': 
                            self.queue.appendleft(self.current_track)
                        else:
                            self.history.append(self.current_track)

                self.skip_requested = False
                self.is_previous_request = False

                # [Next Track Fetching Phase] Try to get the next track from the queue.
                try:
                    self.current_track = self.queue.popleft()
                except IndexError:
                    # --- Idle State: Queue is empty ---
                    # --- 待機状態: キューが空です ---

                    # The queue is empty. First, check if we should loop the entire history.
                    if self.loop_mode == 'queue' and self.history:
                        print(f"INFO: Queue ended in guild {self.guild_id}. Looping back from history.")

                        # Refill the queue from the history.
                        self.queue.extend(self.history)
                        self.history.clear()

                        self.current_track = None

                        # A small, user-friendly message.
                        if self.text_channel:
                            try:
                                await self.text_channel.send("🔁 Reached the end of the queue, looping back to the start.")
                            except discord.HTTPException:
                                pass # Failsafe
                        
                        # Restart the loop immediately to play the first track of the new queue.
                        continue

                    # If not looping, proceed to the normal idle state logic that you already have.
                    self.is_playing = False
                    
                    self.current_track = None
                    
                    if self.history:
                        await self.send_or_edit_panel(
                            embed=self.create_now_playing_embed(finished=True),
                            view=self.get_current_view(finished=True)
                        )
                    
                    if self.text_channel:
                        if self.autoleave_task: self.autoleave_task.cancel()
                        self.autoleave_task = self.bot.loop.create_task(self.autoleave_timer())

                    # I'll wait here until a new song is added.
                    await self.queue_added.wait()
                    
                    # Return from waiting.This means starting a new session, so it clears the old state.
                    self.now_playing_message = None 
                    self.history.clear() # ◀◀◀ This is the most important thing!
                    self.loop_mode = "off"
                    
                    continue # Restart the loop to process the new track.

                # [Playback Preparation Phase] A track is available.
                if self.autoleave_task: self.autoleave_task.cancel(); self.autoleave_task = None
                
                source = await self.audio_handler.create_source(self.current_track, volume=self.volume, eq_mode=self.eq_mode)
                if not source:
                    if self.text_channel: await self.text_channel.send(f"❌ Failed to play '{self.current_track.get('title', 'Unknown')}'.")
                    self.current_track = None
                    continue

                # [Playback Execution Phase] Play the audio source.
                if self.voice_client and self.voice_client.is_connected():
                    self.is_playing = True
                    self.playback_start_time = time.time(); self.paused_time = 0; self.paused_duration = 0
                    track_duration = self.current_track.get('duration', 0)
                    self.expected_end_time = self.playback_start_time + track_duration if track_duration else 0
                    
                    await self.send_or_edit_panel(embed=self.create_now_playing_embed(), view=self.get_current_view())
                    if self.panel_update_task: self.panel_update_task.cancel()
                    self.panel_update_task = self.bot.loop.create_task(self.panel_updater())
                    
                    def after_playback(error):
                        if error: print(f'Playback error in guild {self.guild_id}: {error}')
                        self.bot.loop.create_task(self.check_playback_finished())

                    try:
                        self.voice_client.play(source, after=after_playback)
                    except Exception as e:
                        print(f"ERROR: Failed to start playback in guild {self.guild_id}: {e}")
                        if self.text_channel:
                            await self.text_channel.send(f"❌ Playback error: Skipping `{self.current_track.get('title', 'Unknown')}`.")
                        self.song_finished.set()  # 強制的に待機を解除して次の曲へ

                    # Wait here until the song finishes or is stopped/skipped.
                    await self.song_finished.wait()
                    
                    # Song has finished. The VERY FIRST thing to do is to kill the updater for this track.
                    # This prevents zombie tasks when switching tracks quickly.
                    if self.panel_update_task and not self.panel_update_task.done():
                        self.panel_update_task.cancel()
                        self.panel_update_task = None
                    
                    # Now it is safe to declare that playback has stopped.
                    self.is_playing = False
                        
        except asyncio.CancelledError:
            print(f"Player loop for guild {self.guild_id} was cancelled.")
        finally:
            await self.cleanup()


    async def check_playback_finished(self):
        """
        Intelligently determines if the `after` callback was legitimate or a premature firing.
        This handles cases where network issues cause streams to drop early.
        
        `after`コールバックが正当なものか、早すぎる誤作動かを賢く判断します。
        これにより、ネットワーク問題でストリームが早期に途切れるケースに対応します。
        """
        if self.skip_requested:
            if not self.song_finished.is_set(): self.song_finished.set()
            return
        
        if self.expected_end_time == 0: # Live stream
            if not self.song_finished.is_set(): self.song_finished.set()
            return

        time_until_expected_end = self.expected_end_time - time.time()
        
        # If there are more than 5 seconds left, it was likely an error. Ignore it.
        if time_until_expected_end > 5:
            print(f"INFO: after_playback called prematurely in guild {self.guild_id}. Ignoring.")
            await self.ensure_voice_client_alive()
            return

        # Otherwise, the song finished normally.
        if not self.song_finished.is_set(): self.song_finished.set()


    async def ensure_voice_client_alive(self):
        """
        Checks if the VoiceClient is still connected. If not, attempts to gracefully
        end the current song instead of a full cleanup.
        """
        await asyncio.sleep(2)
        if self.is_playing and (not self.voice_client or not self.voice_client.is_connected()):
            print(f"ERROR: VoiceClient disconnected during playback in guild {self.guild_id}. Ending current song.")
            # Notify the end of the current song, not the full cleanup
            if not self.song_finished.is_set():
                self.song_finished.set()


    # --- State and Connection Management ---

    async def connect(self, interaction: discord.Interaction):
        """Connects to the user's voice channel with a timeout and error handling."""
        if not interaction.user.voice:
            message = "You must be in a voice channel first."
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)
            except discord.errors.NotFound:
                pass 
            return False, "..."
        
        channel = interaction.user.voice.channel
        self.text_channel = interaction.channel
        
        try:
            if self.voice_client:
                await self.voice_client.move_to(channel, timeout=10.0)
            else:
                self.voice_client = await channel.connect(timeout=10.0, reconnect=True)

            if not hasattr(self, '_profile_applied'): # Flags to apply only once
                await self.apply_profile_settings(interaction.user.id)
                self._profile_applied = True

            return True, f"Connected to `{channel.name}`."
            
        except asyncio.TimeoutError:
            message = "Failed to connect to the voice channel in time. Please try again."
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)
            except discord.errors.NotFound:
                pass
            await self.cleanup()
            return False, "..."
            
        except Exception as e:
            print(f"An unexpected error occurred during connect: {e}")
            message = "An unknown error occurred while trying to connect."
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)
            except discord.errors.NotFound:
                pass
            await self.cleanup()
            return False, "..."


    async def disconnect(self):
        """A wrapper for `cleanup` to be called by user commands."""
        if self.voice_client:
            message = "Disconnected from the voice channel."
            await self.cleanup()
            return message
        return "The bot is not in a voice channel."


    async def autoleave_timer(self):
        """Waits for a period of inactivity, then triggers cleanup."""
        for _ in range(600):
            await asyncio.sleep(1)
            if self.is_playing:
                return

            if not self.voice_client or not self.voice_client.is_connected():
                break

        if not self.is_cleaning_up:
            await self.cleanup()


    async def cleanup(self):
        """
        The final cleanup method. Stops all tasks, disconnects from voice,
        sends a final message if appropriate, and ensures the instance is torn down.
        最終的なクリーンアップメソッド。全タスクを停止し、VCから切断し、
        適切な場合は最終メッセージを送信し、インスタンスが完全に解体されることを保証します。
        """
        if self.is_cleaning_up: return
        self.is_cleaning_up = True
        
        print(f"Cleaning up Player for guild {self.guild_id}...")
        self.is_playing = False

        # Edit existing panels, and do nothing if they don't (do not send new messages)
        if self.now_playing_message:
            try:
                embed = discord.Embed(title="👋 See you!", description="Thanks for using the bot.", color=discord.Color.dark_grey())
                await self.now_playing_message.edit(embed=embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass #

        self.now_playing_message = None

        tasks_to_cancel = [self.panel_update_task, self.add_tracks_task, self.autoleave_task, self.empty_channel_leavetask, self.player_task]
        for task in tasks_to_cancel:
            if task and not task.done(): task.cancel()
        
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect(force=True) # force=Trueを追加して確実性を上げる
        self.voice_client = None


    # --- Public API for Playback Control ---

    async def pause(self):
        """Signals the intent to pause playback."""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.paused_time = time.time()
            await self.update_now_playing_panel()
            return "⏸️ Paused."
        return "There is nothing to pause."


    async def resume(self):
        """Signals the intent to resume playback."""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            if self.paused_time > 0:
                self.paused_duration += time.time() - self.paused_time
                self.paused_time = 0
            await self.update_now_playing_panel()
            return "▶️ Resumed."
        return "There is no paused track to resume."


    async def stop(self):
        """
        Stops playback by clearing the queue and history, then gracefully ending
        the current track using the same logic as the skip command.
        """
        if not self.is_playing and not self.queue:
            return "There is nothing to stop."
            
        print(f"Stop command received for guild {self.guild_id}. Clearing data and stopping current track.")
        
        self.queue.clear()
        self.history.clear()
        
        self.loop_mode = 'off'
        
        self.skip_requested = True
        if self.voice_client and self.is_playing:
            self.voice_client.stop()
        else:
            self.queue_added.set()

        # message to return after cleanup
        return "⏹️ Stopped playback and cleared the queue."


    def skip(self):
        """Signals the intent to skip the current track."""
        if not self.is_playing or not self.current_track:
            return "There is nothing to skip."
            
        self.skip_requested = True
        self.voice_client.stop() # This triggers the `after` callback, waking the loop.
        return "⏭️ Skipped."


    def previous(self):
        """Signals the intent to play the previous track from history."""
        if not self.history:
            return "There is no playback history."

        self.skip_requested = True
        self.is_previous_request = True # Special flag for 'previous' logic.
        
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        else:
            # If idle, the player_loop is waiting at `queue_added.wait()`.
            # We must set `queue_added` to wake it up.
            self.queue_added.set()

        return "⏮️ Returning to the previous track..."


    def toggle_loop(self) -> str:
        """Cycles through loop modes: Off -> Track -> Queue -> Off."""
        if self.loop_mode == "off": self.loop_mode = "track"
        elif self.loop_mode == "track": self.loop_mode = "queue"
        else: self.loop_mode = "off"
        return self.loop_mode


    async def set_volume(self, volume_percent: int) -> str:
        """Sets the internal volume and applies it to the current source if playing."""
        if not (0 <= volume_percent <= 200):
            return "❌ Volume must be between 0 and 200."
        self.volume = volume_percent / 100.0
        if self.voice_client and self.voice_client.is_playing() and self.voice_client.source:
            self.voice_client.source.volume = self.volume
        return f"🔊 Volume set to **{volume_percent}%**."


    # --- Public API for Queue Management ---

    async def add_to_queue(self, interaction, query, allow_playlist: bool = False):
        """
        Public entry point for adding a track. Returns an immediate message to the user
        while offloading the actual fetching and queuing to a background task.
        
        曲追加の公開エントリーポイント。実際の取得とキュー追加はバックグラウンドタスクに任せ、
        ユーザーには即座にメッセージを返します。
        """
        self.text_channel = interaction.channel
        self.bot.loop.create_task(self._add_to_queue_background(interaction, query, allow_playlist))
        return f"🔄 Searching for `{query}`..."


    async def _add_to_queue_background(self, interaction, query, allow_playlist: bool):
        """[Background Task] Fetches track info and adds it to the queue."""
        track_info, error_msg = await self.audio_handler.get_track_info(query, allow_playlist=allow_playlist)

        if error_msg or not track_info:
            error_message = error_msg or "Failed to retrieve track."
            display_error = (error_message[:1800] + '...') if len(error_message) > 1800 else error_message
            if self.text_channel:
                await self.text_channel.send(f"❌ Failed to add `{query}`:\n```\n{display_error}\n```")
            return
        
        # track_info['requested_by'] = interaction.user.mention
        # was_empty = not self.queue and not self.current_track
        # self.queue.append(track_info)

        track_info['requested_by'] = interaction.user.mention
        track_info['requester_name'] = interaction.user.display_name
        was_empty = not self.queue and not self.current_track
        self.queue.append(track_info)

        if was_empty:
            self.queue_added.set() # Wake up the player_loop if it was idle.

        if self.text_channel:
            await self.text_channel.send(f"✅ Added **{track_info.get('title', 'Unknown')}** to the queue.")


    async def add_tracks(self, interaction, tracks: list[dict]):
        """Public entry point for adding multiple tracks (e.g., from a playlist)."""
        self.text_channel = interaction.channel
        if self.add_tracks_task and not self.add_tracks_task.done():
            return -1 # Already processing a playlist.
        self.add_tracks_task = self.bot.loop.create_task(self._add_tracks_background(interaction, tracks))
        return len(tracks)


    async def _add_tracks_background(self, interaction, tracks: list[dict]):
        """[Background Task] Iteratively fetches full info for each track and adds to queue."""
        initial_queue_empty = not self.queue and not self.current_track
        count = 0
        for i, track in enumerate(tracks):
            query = track.get('webpage_url') or track.get('title', '')
            if not query: continue

            #new_track_info, error = await self.audio_handler.get_track_info(query)
            #if new_track_info:
            #    new_track_info['requested_by'] = interaction.user.mention
            #    self.queue.append(new_track_info)

            new_track_info, error = await self.audio_handler.get_track_info(query)
            if new_track_info:
                new_track_info['requested_by'] = interaction.user.mention
                new_track_info['requester_name'] = interaction.user.display_name
                self.queue.append(new_track_info)

                count += 1
                if i == 0 and initial_queue_empty:
                    self.queue_added.set() # Start playback with the first available track.
            else:
                print(f"Failed to refresh track info: {track.get('title')}")
            await asyncio.sleep(0.1) # Small delay to prevent rate-limiting.

        if self.text_channel and count > 0:
            await self.text_channel.send(f"✅ Finished processing and added {count} tracks from the playlist.")


    def get_queue_info(self):
        """Formats the current queue and Now Playing track into a string."""
        if not self.queue and not self.current_track: return "The queue is empty."
        info = f"🎵 **Now Playing:** {self.current_track['title'] if self.current_track else 'None'}\n\n"
        if self.queue:
            queue_list = [f"{i+1}. **{track['title']}**" for i, track in enumerate(self.queue)]
            info += "📋 **Up Next:**\n" + "\n".join(queue_list)
        return info


    def remove_from_queue(self, index: int):
        """Removes a track from the queue by its 1-based index."""
        actual_index = index - 1
        if 0 <= actual_index < len(self.queue):
            removed_track = self.queue[actual_index]
            del self.queue[actual_index]
            return f"🗑️ Removed **{removed_track['title']}** from the queue."
        else:
            return "❌ Invalid number."


    # --- UI and Formatting Helpers ---

    async def update_now_playing_panel(self):
        """Convenience method to update the panel with the current state."""
        embed = self.create_now_playing_embed()
        await self.send_or_edit_panel(embed=embed, view=self.get_current_view())
        

    async def send_or_edit_panel(self, embed: discord.Embed, view: discord.ui.View = None):
        """Sends a new Now Playing panel or edits the existing one."""
        if not self.text_channel: return
        try:
            # If now_playing_message exists and is within the last hour, attempt to edit it.
            if self.now_playing_message and (discord.utils.utcnow() - self.now_playing_message.created_at).total_seconds() < 3600:
                await self.now_playing_message.edit(embed=embed, view=view)
            else:
                # If it does not exist or is too old, send a new message.
                if self.now_playing_message:
                    # Remove buttons from old messages
                    try: await self.now_playing_message.edit(view=None)
                    except (discord.NotFound, discord.HTTPException): pass
                
                self.now_playing_message = await self.text_channel.send(embed=embed, view=view)
        except discord.NotFound: 
            self.now_playing_message = await self.text_channel.send(embed=embed, view=view)
        except Exception as e:
            print(f"Panel send/edit error: {e}"); self.now_playing_message = None


    async def panel_updater(self):
        """[Background Task] Periodically updates the progress bar on the Now Playing panel."""
        # Counter for consecutive network errors.
        consecutive_errors = 0
        
        while self.is_playing:
            if self.now_playing_message and self.voice_client and self.voice_client.is_connected():
                try:
                    # Attempt to edit the panel.
                    await self.now_playing_message.edit(embed=self.create_now_playing_embed())
                    
                    # If successful, reset the error counter.
                    consecutive_errors = 0
                    
                except discord.HTTPException as e:
                    # Handle HTTP-related errors (like 503 Service Unavailable).
                    print(f"Panel updater warning (HTTPException): {e.status} {e.text}")
                    consecutive_errors += 1
                    
                    # If errors persist (e.g., 3 times in a row), assume the message is lost.
                    if consecutive_errors >= 3:
                        print("Panel updater failed multiple times. Assuming message is lost.")
                        self.now_playing_message = None
                        break # Exit the loop.
                        
                except discord.NotFound:
                    # The message was deleted by a user. Stop trying to edit it.
                    print("Panel updater stopped: Message was not found.")
                    self.now_playing_message = None
                    break # Exit the loop.
                    
                except Exception as e:
                    # Handle other unexpected errors.
                    print(f"Panel updater encountered an unexpected error: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        self.now_playing_message = None
                        break
            else:
                # Player is no longer in a state to update the panel.
                break

            # Wait for the next update cycle.
            await asyncio.sleep(5)


    def create_now_playing_embed(self, finished=False):
        """Builds the rich embed for the Now Playing panel."""
        if finished or not self.current_track:
            return discord.Embed(title="⏹️ Playback Finished", description="Thanks for listening!", color=discord.Color.dark_grey())
        
        track = self.current_track
        status_icon = "⏸️ Paused" if self.voice_client and self.voice_client.is_paused() else "▶️ Playing"
        url_text = f"[[Link to YouTube]]({track.get('webpage_url', 'https://youtube.com')})"

        embed = discord.Embed(title="Now playing music:", color=discord.Color.green())
        if track.get('thumbnail'): embed.set_thumbnail(url=track.get('thumbnail'))
        embed.description = (f"**By:** {track.get('uploader', 'Unknown Artist')}\n\u200b\n"
                            f"{status_icon}:\n**{track.get('title', 'Unknown Title')}**\n{url_text}")

        current_time_sec = self.get_current_playback_time()
        total_time_sec = track.get('duration', 0)
        progress = min(current_time_sec / total_time_sec, 1.0) if total_time_sec > 0 else 0
        bar_length = 20; filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '─' * (bar_length - filled_length)
        progress_display = (f"\u200b\n`{self.format_time(current_time_sec)}`"
                            f"\u200b`   {bar}   `\u200b`{self.format_time(total_time_sec)}`")
        embed.add_field(name="", value=progress_display, inline=False)
        
        current_pos = len(self.history) + 1
        total_tracks = len(self.history) + 1 + len(self.queue)
        queue_status = f"Queue: {current_pos}/{total_tracks}"
        display_name = track.get('requester_name', 'Unknown')

        volume_status = f"Volume: {int(self.volume * 100)}%"
        embed.set_footer(text=f"Requested by: {display_name} | 🎶 {queue_status} | 🔊 {volume_status}")
        return embed


    def get_current_view(self, finished=False):
        """Creates and returns the appropriate control panel view for the current state."""
        from utils.views import ControlPanelView
        view = ControlPanelView(self)
        if finished:
            for item in view.children: item.disabled = True
        else:
            view.update_all_buttons()
        return view


    def get_current_playback_time(self) -> float:
        """Calculates the current playback time in seconds, accounting for pauses."""
        if not self.is_playing or self.playback_start_time == 0: return 0
        if self.voice_client.is_paused() and self.paused_time > 0:
            return self.paused_time - self.playback_start_time - self.paused_duration
        return time.time() - self.playback_start_time - self.paused_duration


    def format_time(self, seconds: float) -> str:
        """Formats seconds into a mm:ss string."""
        if seconds < 0: seconds = 0
        minutes, sec = divmod(int(seconds), 60)
        return f"{minutes:02d}:{sec:02d}"

    
    async def apply_profile_settings(self, user_id: int):
        """Applies a user's saved profile settings (e.g., volume) to the player."""
        profile_cog = self.bot.get_cog("ProfileCog")
        if profile_cog:
            profile_data = profile_cog.profile_manager.load_profile(user_id)
            volume_percent = profile_data.get('volume', 100)
            self.volume = volume_percent / 100.0
            self.eq_mode = profile_data.get('eq_mode', 'balanced')
            
            print(f"Applied profile for {user_id}: Volume set to {volume_percent}%, EQ Mode set to {self.eq_mode}")
