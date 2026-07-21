# --- English ---
# This module handles all interactions with external audio sources like YouTube.
# It uses `yt-dlp` to fetch track information and search for music.
# To prevent blocking the bot's event loop, all network-intensive operations
# are run in a separate process using `concurrent.futures.ThreadPoolExecutor`.

# --- 日本語 ---
# このモジュールは、YouTubeなどの外部音源とのすべてのやり取りを処理します。
# `yt-dlp`を使用して曲情報の取得や音楽の検索を行います。
# ボットのイベントループをブロックしないように、すべてのネットワーク負荷が高い操作は
# `concurrent.futures.ThreadPoolExecutor` を用いて別プロセスで実行されます。

import yt_dlp
import discord
from concurrent.futures import ThreadPoolExecutor
import asyncio
import re

executor = ThreadPoolExecutor(max_workers=10)

# --- Synchronous Functions (for Process Pool) ---
# These functions are designed to be run in a separate process via the executor.

def get_track_info_sync(query: str, allow_playlist: bool = False):
    """
    [Sync Function] The core yt-dlp process for fetching track info. Runs in a separate process.
    Optimized to always force single track streaming for maximum stability and speed.

    [同期機能] トラック情報を取得するためのyt-dlpのコアプロセスです。別プロセスとして実行されます。
    安定性と速度を最大限に高めるため、常にシングルトラックストリーミングを強制するように最適化されています。
    """
    # Force disable playlist loading to prevent timeouts and heavy data traffic.
    # We want a single video stream regardless of what URL was passed.
    YDL_OPTIONS = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
        'noplaylist': True  # Always tell yt-dlp to focus strictly on a single track.
    }

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(query, download=False)

        if not info:
            return None, "No data found."

        # Safety Fallback: If yt-dlp still returns a list structure for some reason,
        # safely extract the very first entry to get the video data.
        if 'entries' in info:
            if info['entries']:
                entry = info['entries'][0]
            else:
                return None, "The provided link contains no playable videos."
        else:
            entry = info

        # Thoroughly search for a playable stream URL within the complex format list.
        stream_url = entry.get('url')
        
        if not stream_url:
            best_audio_format = None
            for f in entry.get('formats', []):
                # Ideal format is audio-only ('vcodec'=='none') and has a valid URL.
                if f.get('vcodec') == 'none' and f.get('url'):
                    # Prefer formats with a higher audio bitrate (abr).
                    if best_audio_format is None or f.get('abr', 0) > best_audio_format.get('abr', 0):
                        best_audio_format = f
            
            if best_audio_format:
                stream_url = best_audio_format.get('url')

        # Last resort fallback if everything else fails.
        if not stream_url:
            stream_url = entry.get('url')

        return {
            'id': entry.get('id'), 
            'title': entry.get('title', 'Unknown'),
            'webpage_url': entry.get('webpage_url') or (f"https://youtube.com{entry.get('id')}" if entry.get('id') else None), 
            'thumbnail': entry.get('thumbnail'),
            'uploader': entry.get('uploader', 'Unknown'), 
            'uploader_url': entry.get('uploader_url'),
            'duration': entry.get('duration', 0),
            'url': stream_url
        }, None
    
    except Exception as e:
        return None, str(e)


def search_youtube_sync(query: str, max_results: int = 10):
    """
    [Sync Function] Searches YouTube and returns a list of results. Runs in a separate process.
    Strictly filters out any playlist data from text-based searches.

    [同期機能] YouTubeを検索し、検索結果のリストを返します。別プロセスで実行されます。
    テキスト検索からプレイリストのデータを厳密に除外します。
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
            
            # Clean up results: ensure no Mixlists or custom Playlists contaminate the search result.
            filtered_entries = []
            for entry in entries:
                if not entry:
                    continue
                
                url = entry.get('url', '')
                _type = entry.get('_type', 'video')
                
                if 'list=' in url or _type == 'playlist' or 'playlist' in entry.get('id', ''):
                    continue
                
                filtered_entries.append(entry)
                
            return filtered_entries, None
    except Exception as e:
        return None, str(e)


# --- Asynchronous Handler Class ---

class AudioHandler:
    """Provides an async interface to the synchronous yt-dlp functions."""

    def is_youtube_url(self, query: str) -> bool:
        """Checks if the provided query string is a valid YouTube URL."""
        youtube_regex = (
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|shorts/|playlist\?|.+\?v=)?([a-zA-Z0-9_-]+)'
        )
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
            'before_options': (
                '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
                '-rw_timeout 5000000 -thread_queue_size 4096'
            ),
            'options': (
                '-vn -loglevel error -af "'
                'aresample=48000:resampler=swr:precision=24:dither_method=shibata,'
                'anequalizer=c0 f=60 w=15 g=1.5|c1 f=60 w=15 g=1.5,'
                'compand=attacks=0.02:decays=0.1:points=-80/-80|-35/-35|0/-5,'
                'loudnorm=I=-18:LRA=10:TP=-2.0"'
            )
        }

        # [Mode 2: Hi-Fi] - For high-quality headphones (高品質ヘッドホン向け)
        FFMPEG_OPTIONS_HIFI = {
            'before_options': (
                '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 '
                '-rw_timeout 15000000 -thread_queue_size 16384 '
                '-analyzeduration 10M -probesize 10M -fflags +nobuffer+genpts'
            ),
            'options': (
                '-vn -loglevel error '
                '-af "aresample=48000:resampler=swr:precision=33:dither_method=shibata,'
                'anequalizer=c0 f=55 w=15 g=2|c1 f=55 w=15 g=2|c0 f=1000 w=200 g=1.5|c1 f=1000 w=200 g=1.5,'
                'asubboost=cutoff=70:feedback=0.2,'
                'extrastereo=m=1.1,'
                'aecho=0.8:0.3:20:0.02,'
                'compand=attacks=0.005:decays=0.1:points=-80/-80|-30/-20|-10/-8|0/-5,'
                'loudnorm=I=-14:LRA=11:TP=-1.0"'
            )
        }

        # Determine which options to use based on the eq_mode argument
        if eq_mode == "hifi":
            final_options = FFMPEG_OPTIONS_HIFI
            print("INFO: Using Hi-Fi EQ mode.")
        else:
            final_options = FFMPEG_OPTIONS_BALANCED
            print("INFO: Using Balanced EQ mode.")


        # 3. Generating the audio source (using the selected options)
        try:
            source = discord.FFmpegPCMAudio(audio_url, **final_options)
            return discord.PCMVolumeTransformer(source, volume=volume)
        except Exception as e:
            print(f"FATAL: FFmpegPCMAudio failed to create source: {e}")
            return None
