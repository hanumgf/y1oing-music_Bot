# y1Music-Bot

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

This project is a Discord music bot designed with a focus on responsiveness and stable operation. Drawing upon lessons learned from numerous failed bot development attempts, it was developed with the aim of creating "my own comfortable Music Bot".

### Key Highlights
- **Smooth responsiveness:** By executing heavy processing in a separate process, the responsiveness of the Bot itself is maintained at all times.
- **Clear sound quality:** Utilising FFmpeg's audio filters, we provide clear and stable sound quality.
- **Flexible playlist features:** In addition to personal playlists, it supports server-shared playlists with permission management.
- **An intuitive UI:** All key operations can be performed via interactive buttons and menus that update in real time.

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
> If you are not familiar with Git, the easiest way is to download the `Source code (zip)` of the latest version from the [**Releases Page**](https://github.com/y0sh-dev/y1Music-Bot/releases/latest). After downloading, please proceed from **Step 2** below.

---

### Step 1: Clone the Repository (リポジトリのクローン)
```sh
git https://github.com/y0sh-dev/y1Music-Bot.git
```
```sh
cd y1Music-Bot
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
DISCORD_TOKEN="Paste your bot token here"
```

### Step 6: Configure the Bot (ボットの基本設定)
Edit the `config.json` file to set your user ID as the bot owner. This gives you access to owner-only commands.

1.  **Get your User ID:**
    - In Discord, enable "Developer Mode" in `User Settings` > `Advanced`.
    - Right-click your own profile icon and select "Copy User ID".

2.  **Edit `config.json`:**
    - Open the `config.json` file in the project root.
    - Replace "Your_User_ID_Here" inside `owner_ids` with your own user ID.
    ```json
    {
      "prefix": "?",
      "feedback_recipient_id": "Your_User_ID_Here",
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

1.  **Get your Test Server ID**
    - In Discord, enable "Developer Mode" in `User Settings` > `Advanced`.
    - Right-click your server icon and select "Copy Server ID".

2.  **Edit `client.py`**
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
