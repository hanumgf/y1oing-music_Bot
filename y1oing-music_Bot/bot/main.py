# --- English ---
# This file contains the main function to initialize and run the bot.
# It handles loading environment variables, instantiating the bot client,
# and ensuring graceful shutdown of background processes.

# --- 日本語 ---
# ボットを初期化して実行する main 関数を格納するファイルです。
# 環境変数の読み込み、ボットクライアントのインスタンス化、
# バックグラウンドプロセスの正常なシャットダウンを管理します。

import os
from dotenv import load_dotenv
from .client import Y1oingBot
from utils.audio_handler import executor


def main():
    # Load environment variables from the .env file.
    # This makes sensitive data like tokens available to the application.
    # .env ファイルから環境変数を読み込みます。
    # これにより、トークンなどの機密データがアプリケーションで利用可能になります。
    load_dotenv()
    
    # Instantiate the bot client.
    # ボットクライアントをインスタンス化します。
    bot = Y1oingBot()

    try:
        # Run the bot with the token from environment variables.
        # bot.run() is a blocking call that handles the connection to Discord
        # and also manages the SIGINT (Ctrl+C) signal for shutdown.
        # 環境変数から取得したトークンでボットを実行します。
        # bot.run() はブロッキング呼び出しであり、Discordへの接続を処理し、
        # シャットダウンのためのSIGINT (Ctrl+C) シグナルも管理します。
        bot.run(os.getenv("DISCORD_TOKEN"))
        
    except KeyboardInterrupt:
        # This block is unlikely to be reached as bot.run() handles KeyboardInterrupt,
        # but it is kept as a fallback.
        # bot.run()がKeyboardInterruptを処理するため、このブロックに到達する可能性は低いですが、
        # フォールバックとして残しておきます。
        print("\nKeyboardInterrupt received. Bot is shutting down...")
        
    finally:
        # This block is guaranteed to run after the bot has disconnected,
        # ensuring that all cleanup operations are performed.
        # It shuts down the process pool executor gracefully.
        # このブロックはボットが切断された後に実行されることが保証されており、
        # すべてのクリーンアップ処理が確実に行われます。
        # プロセスプール・エグゼキュータを正常にシャットダウンします。
        print("Shutting down process pool...")
        executor.shutdown(wait=True)
        print("Process pool shut down. Goodbye!")
