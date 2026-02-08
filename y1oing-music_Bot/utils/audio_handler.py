# --- English ---
# This module handles all interactions with external audio sources like YouTube.
# It uses `yt-dlp` to fetch track information and search for music.
# To prevent blocking the bot's event loop, all network-intensive operations
# are run in a separate process using `concurrent.futures.ProcessPoolExecutor`.

# --- 日本語 ---
# このモジュールは、YouTubeなどの外部音源とのすべてのやり取りを処理します。
# `yt-dlp`を使用して曲情報の取得や音楽の検索を行います。
# ボットのイベントループをブロックしないように、すべてのネットワーク負荷が高い操作は
# `concurrent.futures.ProcessPoolExecutor` を用いて別プロセスで実行されます。

import yt_dlp
import discord
from concurrent.futures import ProcessPoolExecutor
import asyncio
import re


# A global process pool to run synchronous, blocking I/O operations without freezing the bot.
# 同期的なブロッキングI/O操作をボットをフリーズさせることなく実行するためのグローバルなプロセスプール。
executor = ProcessPoolExecutor(max_workers=2)


# --- Synchronous Functions (for Process Pool) ---
# These functions are designed to be run in a separate process via the executor.

def get_track_info_sync(query: str, allow_playlist: bool = False):
    """
    [Sync Function] The core yt-dlp process for fetching track info. Runs in a separate process.
    It extracts essential metadata and, most importantly, finds a direct stream URL.
    
    【同期関数】曲情報を取得するyt-dlpのコア処理。別プロセスで実行されます。
    必須のメタデータを抽出し、最も重要なダイレクトストリームURLを見つけ出します。
    """
    YDL_OPTIONS = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0'
    }
    
    if not allow_playlist:
        YDL_OPTIONS['noplaylist'] = True
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(query, download=False)
        
        # If the result is a playlist (has 'entries'), return the whole info dict.
        # Otherwise, format it as a single track object as before.
        if 'entries' in info:
            return info, None # Return the full playlist data
        else:
            entry = info
            
            # Thoroughly search for a playable stream URL within the complex format list.
            
            stream_url = None
            
            # Priority 1: Check the top-level 'url' key first.
            if 'url' in entry:
                stream_url = entry['url']
            
            # Priority 2: If not found, search the formats list for the best audio-only stream.
            if not stream_url:
                best_audio_format = None
                for f in entry.get('formats', []):
                    # Ideal format is audio-only ('vcodec'=='none') and has a URL.
                    if f.get('vcodec') == 'none' and f.get('url'):
                        # Prefer formats with a higher audio bitrate (abr).
                        if best_audio_format is None or f.get('abr', 0) > best_audio_format.get('abr', 0):
                            best_audio_format = f
                
                if best_audio_format:
                    stream_url = best_audio_format.get('url')

            # Priority 3: As a last resort, just take the URL from the format yt-dlp pre-selected.
            if not stream_url:
                stream_url = entry.get('url') # This might be the same as the first check, but it's a safe fallback.

            return {
                'id': entry.get('id'), 'title': entry.get('title', 'Unknown'),
                'webpage_url': entry.get('webpage_url'), 'thumbnail': entry.get('thumbnail'),
                'uploader': entry.get('uploader', 'Unknown'), 'uploader_url': entry.get('uploader_url'),
                'duration': entry.get('duration', 0),
                'url': stream_url
            }, None
    
    except Exception as e:
        return None, str(e)


def search_youtube_sync(query: str, max_results: int = 10):
    """
    [Sync Function] Searches YouTube and returns a list of results. Runs in a separate process.
    It filters out auto-generated "Mix" playlists from the results.
    
    【同期関数】YouTubeを検索し、結果のリストを返します。別プロセスで実行されます。
    自動生成される「Mix」プレイリストを結果から除外します。
    """
    YDL_OPTIONS = {
        'format': 'm4a/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': f'ytsearch{max_results}',
        'extract_flat': 'in_playlist',
        'source_address': '0.0.0.0'
    }
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            result = ydl.extract_info(query, download=False)
            entries = result.get('entries', [])
            filtered_entries = [
                entry for entry in entries
                if entry and 'list=RD' not in entry.get('url', '')
            ]
            return filtered_entries, None
    except Exception as e:
        return None, str(e)


# --- Asynchronous Handler Class ---

class AudioHandler:
    """Provides an async interface to the synchronous yt-dlp functions."""

    def is_youtube_url(self, query: str) -> bool:
        """Checks if the provided query string is a valid YouTube URL."""
        youtube_regex = (r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
        return re.search(youtube_regex, query) is not None


    async def get_track_info(self, query: str, allow_playlist: bool = False):
        """
        Asynchronously fetches track info by running `get_track_info_sync` in the process pool.
        
        プロセスプールで `get_track_info_sync` を実行し、非同期に曲情報を取得します。
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, get_track_info_sync, query, allow_playlist)


    async def search_youtube(self, query: str, max_results: int = 10):
        """
        Asynchronously searches YouTube by running `search_youtube_sync` in the process pool.
        
        プロセスプールで `search_youtube_sync` を実行し、非同期にYouTubeを検索します。
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, search_youtube_sync, query, max_results)


    async def create_source(self, track_info: dict, volume: float = 1.0, eq_mode: str = "balanced"):
        """
        Creates a `discord.FFmpegPCMAudio` source for playback.
        It uses the stream URL from `track_info` and applies FFmpeg options for normalization.
        
        再生用の `discord.FFmpegPCMAudio` ソースを作成します。
        `track_info` のストリームURLを使用し、音量正規化のためのFFmpegオプションを適用します。
        """
        audio_url = track_info.get('url')
        
        # If the URL is still missing, it means get_track_info failed to find one.
        # We will not retry here to prevent timeouts.
        if not audio_url:
            print(f"FATAL: A playable stream URL could not be found for {track_info.get('title')}")
            return None

        # 2種類のFFmpegオプションを定義
        
        # [Mode 1: Balanced] - For Bluetooth/Speakers (イヤホン/スピーカー向け)
        FFMPEG_OPTIONS_BALANCED = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': (
                '-vn -loglevel error '
                '-af "aresample=resampler=soxr:precision=20:out_sample_rate=48000,'
                'anequalizer=c0 f=2500 w=100 g=-1.5 t=1|c0 f=6000 w=200 g=1 t=1|c0 f=15000 w=500 g=-2 t=1,'
                'loudnorm=I=-16.5:LRA=7:TP=-1.5"'
            )
        }

        # [Mode 2: Hi-Fi] - For high-quality headphones (高品質ヘッドホン向け)
        FFMPEG_OPTIONS_HIFI = {
            'before_options': (
                '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
                '-rw_timeout 5000000 '
                '-analyzeduration 5M -probesize 5M'
            ),
            'options': (
                '-vn -loglevel error '
                '-af "aresample=resampler=swr:out_sample_rate=48000:dither_method=shibata,'
                'anequalizer=c0 f=60 w=20 g=2 t=1|c0 f=4000 w=200 g=-1.5 t=1|c0 f=8000 w=300 g=1.5 t=1|c0 f=12000 w=500 g=1 t=1,'
                'extrastereo=m=1.1,'
                'aecho=0.8:0.4:30:0.2,'
                'loudnorm=I=-18:LRA=13:TP=-1.0"'
            )
        }
        
        # eq_mode引数に応じて、使用するオプションを決定
        if eq_mode == "hifi":
            final_options = FFMPEG_OPTIONS_HIFI
            print("INFO: Using Hi-Fi EQ mode.")
        else:
            final_options = FFMPEG_OPTIONS_BALANCED
            print("INFO: Using Balanced EQ mode.")
        
        
        # 3. オーディオソースの生成 (決定したオプションを使う)
        try:
            source = discord.FFmpegPCMAudio(audio_url, **final_options)
            return discord.PCMVolumeTransformer(source, volume=volume)
        except Exception as e:
            print(f"FATAL: FFmpegPCMAudio failed to create source: {e}")
            return None
