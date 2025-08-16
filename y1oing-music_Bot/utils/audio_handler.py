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
        # [JP] もし結果がプレイリスト（'entries'を持つ）なら、info辞書をそのまま返す。
        # [JP] そうでなければ、これまで通り単一の曲オブジェクトに整形して返す。
        if 'entries' in info:
            return info, None # Return the full playlist data
        else:
            entry = info
            
            # Ensure the stream URL is included for single tracks
            stream_url = None
            for f in info.get('formats', []):
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    stream_url = f.get('url')
                    break
            if not stream_url:
                stream_url = info.get('url')

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
        'format': 'bestaudio/best',
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


    async def create_source(self, track_info: dict, volume: float = 1.0):
        """
        Creates a `discord.FFmpegPCMAudio` source for playback.
        It uses the stream URL from `track_info` and applies FFmpeg options for normalization.
        
        再生用の `discord.FFmpegPCMAudio` ソースを作成します。
        `track_info` のストリームURLを使用し、音量正規化のためのFFmpegオプションを適用します。
        """
        audio_url = track_info.get('url')
        
        # Fallback: If the URL is missing, try to refresh the track info once.
        # フォールバック: URLが見つからない場合、一度だけ曲情報の再取得を試みます。
        if not audio_url:
            print(f"Stream URL missing in initial info for {track_info.get('title')}. Retrying once...")
            track_info_fresh, error = await self.get_track_info(track_info['webpage_url'])
            if error:
                print(f"Error refreshing track info: {error}")
                return None
            audio_url = track_info_fresh.get('url')

        if not audio_url:
            print(f"FATAL: Could not get a stream URL for {track_info.get('title')}")
            return None

        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': (
                '-vn '
                '-af "aresample=resampler=soxr:precision=28:out_sample_rate=48000" ' # Filter 1
                '-af "superequalizer=1b=2:f=80:t=q:w=1.2|2b=2:f=8000:t=q:w=1.2" '  # Filter 2
                '-af "loudnorm=I=-18:LRA=7:TP=-2.0"'                               # Filter 3
            )
        }
        
        try:
            source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            return discord.PCMVolumeTransformer(source, volume=volume)
        except Exception as e:
            print(f"FATAL: FFmpegPCMAudio failed to create source: {e}")
            return None