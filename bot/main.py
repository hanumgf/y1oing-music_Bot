# --- English ---
# This file contains the main function to initialize and run the bot.
# It handles loading environment variables, instantiating the bot client,
# and ensuring graceful shutdown of background processes.

# --- 日本語 ---
# ボットを初期化して実行する main 関数を格納するファイルです。
# 環境変数の読み込み、ボットクライアントのインスタンス化、
# バックグラウンドプロセスの正常なシャットダウンを管理します。

import os
from pathlib import Path
from dotenv import load_dotenv
from .client import Y1oingBot
from utils.audio_handler import executor

BASE_DIR = Path(__file__).resolve().parent.parent
os.chdir(BASE_DIR)


def main():
    # Load environment variables from the .env file.
    load_dotenv()

    #    bot = Y1oingBot()
    #    try:
    #        bot.run(os.getenv("DISCORD_TOKEN"))
    #    except KeyboardInterrupt:

    bot = Y1oingBot()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("=" * 50)
        print("!!! ERROR: DISCORD_TOKEN is not set in the environment variables. !!!")
        print("=" * 50)
        return

    try:
        bot.run(token)

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Bot is shutting down...")

    finally:
        print("Shutting down process pool...")
        executor.shutdown(wait=True)
        print("Process pool shut down. Goodbye!")
