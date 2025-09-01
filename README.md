# y1oing BOT

> "Sound Perfected, Experience Redefined."

[![Status](https://img.shields.io/badge/status-released-success.svg)]()
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-v2.x-7289da.svg)](https://github.com/Rapptz/discord.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE.md)

- A responsive and stable Discord music bot with a focus on a quality audio experience.  
- 応答性と安定性を重視して作られた、快適な音楽体験のためのDiscord音楽ボット。

---

## Table of Contents
- [About The Project](#about-the-project)
- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [For Developers: Fast Command Sync](#for-developers-fast-command-sync)
- [Command List](#command-list)
- [License & Credit](#license--credit)

---

## About The Project

このプロジェクトは、応答性と安定した動作を重視して設計されたDiscord音楽ボットです。幾度となく挫折したボット制作の経験から得た教訓をすべて注ぎ込み、「私だけの快適なMusic Bot」を目指して開発されました。

### Key Highlights
- **スムーズな応答性:** 重い処理を別プロセスで実行することで、Bot本体の応答性を常に維持します。
- **クリアな音質:** FFmpegのオーディオフィルターを利用し、クリアで安定した音質を提供します。
- **柔軟なプレイリスト機能:** 個人用プレイリストに加え、権限管理が可能なサーバー共有プレイリストをサポートします。
- **直感的なUI:** 全ての主要な操作は、リアルタイムに更新されるインタラクティブなボタンとメニューから行えます。

---

## Key Features

- **Core Playback:**
    - Play, pause, resume, skip, and return to previous tracks.
    - A real-time, persistent interactive control panel.
    - Loop modes for a single track or the entire queue.

- **Advanced Playlist System:**
    - Create and manage your own persistent personal playlists.
    - Collaborate on server-wide playlists with a permission system (owner, collaborators).
    - Add entire YouTube playlists in one go.

- **User Experience & Customization:**
    - User profiles to save settings like volume.
    - Interactive search for tracks by keyword or URL.
    - Automatic disconnection after a period of inactivity.

---

## Prerequisites

The following software is required to run this bot.

- **Python 3.10** or higher
- **FFmpeg**
    - **[IMPORTANT]** FFmpeg is essential for audio processing. You must install it on your system and ensure it's available in your system's PATH.
    - **[重要]** FFmpegは、音声データを処理するために不可欠です。お使いのシステムに別途インストールし、環境変数のPATHに通しておく必要があります。

---

## Getting Started

Follow these steps to get the bot running in your own environment.

> **💡 Easy Method (簡単な方法):**
> If you are not familiar with Git, the easiest way is to download the `Source code (zip)` of the latest version from the [**Releases Page**](https://github.com/hanumgf/y1oing-music_Bot/releases/latest). After downloading, please proceed from **Step 2** below.
> 
> Gitの操作が苦手な方は、このリポジトリの[**Releasesページ**](https://github.com/hanumgf/y1oing-music_Bot/releases/latest)から最新版のソースコード (`Source code (zip)`) を直接ダウンロードするのが一番簡単です。ダウンロードした後は、下の **Step 2** から手順を進めてください。

---

### Step 1: Clone the Repository (リポジトリのクローン)
```sh
git clone https://github.com/hanumgf/y1oing-music_Bot.git
```
```sh
cd y1oing-music_Bot
```

### Step 2: Create a Virtual Environment (仮想環境の作成)
```sh
python -m venv venv
```

Activate the virtual environment:
- **Windows:**
  ```sh
  .\venv\Scripts\activate
  ```
- **macOS / Linux:**
  ```sh
  source venv/bin/activate
  ```

### Step 3: Install Dependencies (依存関係のインストール)
```sh
pip install -r requirements.txt
```

### Step 4: Prepare your Discord Bot Token (Discord Bot Tokenの準備)
1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application.
2.  Navigate to the "Bot" tab and click "Add Bot".
3.  Enable all three **Privileged Gateway Intents**.
4.  Click "Reset Token" to generate your bot's token and copy it securely.

### Step 5: Configure Environment Variables (環境変数の設定)
Create a new file named `.env` in the project root directory. Then, add the following content and set your bot token.
```env
# .env
DISCORD_TOKEN="ここにあなたのボットのトークンを貼り付けます"
```

### Step 6: Configure the Bot (ボットの基本設定)
Edit the `config.json` file to set your user ID as the bot owner. This gives you access to owner-only commands.
(次に `config.json` ファイルを編集し、あなたのユーザーIDをBotの所有者として設定します。これにより、所有者限定コマンドが使えるようになります。)

1.  **Get your User ID (あなたのユーザーIDを取得):**
    - In Discord, enable "Developer Mode" in `User Settings` > `Advanced`.
    - Right-click your own profile icon and select "Copy User ID".

2.  **Edit `config.json` (`config.json`の編集):**
    - Open the `config.json` file in the project root.
    - Replace "Your_User_ID_Here" inside `owner_ids` with your own user ID.
```json
{
  "prefix": "?",
  "owner_ids": [
    "Your_User_ID_Here"
  ]
}
```

### Step 7: Run the Bot (ボットの起動)
```sh
python run.py
```

---

## For Developers: Fast Command Sync

To apply slash commands to a test server instantly (instead of waiting up to an hour), follow these steps.

1.  **Get your Test Server ID (テストサーバーIDの取得)**
    - In Discord, enable "Developer Mode" in `User Settings` > `Advanced`.
    - Right-click your server icon and select "Copy Server ID".

2.  **Edit `client.py` (`client.py`の編集)**
    - Open `bot/client.py`.
    - Find the `TEST_GUILD` line and replace the ID with your server's ID.
        - **Before:**
      ```python
      TEST_GUILD = discord.Object(id=0000)
      ```
        - **After:**
      ```python
      TEST_GUILD = discord.Object(id=YOUR_SERVER_ID_HERE)
      ```

    - Next, modify the command sync block inside the `setup_hook` method:
        - **Before:**
      ```python
      # self.tree.copy_global_to(guild=TEST_GUILD)
      # await self.tree.sync(guild=TEST_GUILD)
      await self.tree.sync()
      ```

        - **After:**
      ```python
      self.tree.copy_global_to(guild=TEST_GUILD)
      await self.tree.sync(guild=TEST_GUILD)
      # await self.tree.sync()
      ```

Restart the bot, and slash commands will be available immediately on your test server.

---

## Command List

| Command Group             | Command(s)                      | Description (Japanese: 説明)                                      |
|:--------------------------|:--------------------------------|:------------------------------------------------------------------|
| **Connection**            | `/join`, `/leave`               | Connects to or disconnects from a voice channel (ボイスチャンネルへの接続/切断). |
| **Playback**              | `/play`, `/pause`, `/resume`    | Core playback controls (再生/一時停止/再開).                          |
|                           | `/stop`, `/skip`, `/previous`   | Track navigation and stopping playback (停止/スキップ/前の曲へ).    |
|                           | `/nowplaying`                   | Displays the interactive control panel (再生パネルの表示).               |
| **Queue**                 | `/queue`, `/queue_remove`       | Manages the song queue (キューの表示と管理).                           |
| **Search**                | `/search`                       | Interactively search for tracks (対話的な楽曲検索).                     |
| **Playlist (Personal)**   | `/playlist [...]`               | Manages your personal playlists (個人プレイリストの管理).                |
| **Playlist (Server)**     | `/serverplaylist [...]`         | Manages shared server playlists (サーバー共有プレイリストの管理).           |
| **Settings**              | `/volume`, `/loop`, `/profile`  | Manages user and playback settings (設定の管理).                   |
| **Utility**               | `/help`, `/feedback`  | Provides help and utility functions (ヘルプとユーティリティ).               |

---

## License & Credit

This project is licensed under the MIT License. See the `LICENSE` file for more details.

Created by [`y1.ing`](https://discord.com/users/1030100948003065866)
