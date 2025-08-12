# Project Documentation: y1oing BOT

This document provides a comprehensive overview of the design, architecture, and features for the **y1oing BOT** project.
このドキュメントは、**y1oing BOT** プロジェクトの設計、アーキテクチャ、そして機能の全体像を解説するものです。

## 1. Project Philosophy & Goals

### 1.1. Motivation
This project was born out of a determination to succeed where previous attempts at building a music bot had failed. It is a response to the current landscape of music bots, which, while feature-rich, often neglect the core user experience and performance aspects that truly matter. The ultimate goal was to craft a music bot that is both functional and user-friendly—prioritizing responsiveness and an intuitive interface.

> **日本語:** このプロジェクトは、幾度となく挫折した音楽ボット制作への再挑戦から生まれました。多機能でありながら、本当に大切な「使いやすさ」や「パフォーマンス」がおろそかになりがちな既存のBotへの一つの答えです。応答性に優れ、直感的に使える、安定して使いやすい音楽ボットを創り上げることが目標でした。

### 1.2. Core Objectives
- **Project Name**: **y1oing BOT**
- **Primary Goal**: To create a comfortable and quality music bot, built for a great personal experience. (私だけの快適なMusic Botを作ること。)
- **Technology**: **Python**, chosen for its robust ecosystem and developer-friendly nature.

---

## 2. Feature Blueprint

y1oing BOT is equipped with a rich set of features, designed to provide a pleasant music experience.
(y1oing BOTは、快適な音楽体験を提供するために設計された、豊富な機能を備えています。)

| Category                  | Feature                               | Description                                                                 |
|:--------------------------|:--------------------------------------|:----------------------------------------------------------------------------|
| **Core Playback**         | Clear Audio Playback                  | Play, pause, resume, skip, and return to previous tracks with clear audio quality. |
|                           | Interactive Control Panel             | A real-time, persistent UI for all major playback controls.                 |
|                           | Versatile Loop Modes                  | Loop a single track, the entire queue, or turn looping off.                 |
|                           | Dynamic Volume Control                | Adjust volume on the fly (0-200%) via commands or interactive buttons.      |
| **Advanced Queue**        | Functional Queue Management           | Add, view, and remove tracks from a responsive queue system.                |
|                           | Interactive Search                    | Search YouTube and select tracks from a clean, paginated results menu.      |
|                           | Background Buffering Support          | Pre-buffers the next track to ensure smooth transitions.                    |
| **Playlist System**       | Personal Playlists                    | Create, manage, and play your own private, persistent playlists.            |
|                           | Shared Server Playlists               | Collaborate on server-wide playlists with a flexible permission model.      |
|                           | YouTube Playlist Integration          | Add entire public YouTube playlists to your queue or personal playlists.    |
| **User Customization**    | User Profile System                   | Save and automatically load your preferred settings (volume, EQ).           |
|                           | Audio Equalizer                       | Fine-tune audio output with a configurable multi-band equalizer.            |
| **User Experience**       | Responsive Architecture               | Heavy tasks are offloaded to separate processes, ensuring the bot remains responsive. |
|                           | Auto-Disconnect                       | Automatically leaves the voice channel after inactivity to save resources.  |
|                           | Helpful Command Guide                 | An interactive help menu guides users through all available features.       |

---

## 3. Command Interface

The bot is controlled via a clean and intuitive set of application (slash) commands.

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
| **Utility**               | `/help`, `/about`, `/feedback`  | Provides help and utility functions (ヘルプとユーティリティ).               |

---

## 4. Technical Architecture

### 4.1. Tech Stack
- **Language**: Python 3.10+
- **Core Library**: discord.py 2.x
- **Audio Source**: yt-dlp
- **Audio Engine**: FFmpeg
- **Data Persistence**: JSON files

### 4.2. Directory Structure
The project is architected with a clean separation of concerns, promoting modularity and maintainability.
(プロジェクトは、関心の分離を徹底したクリーンなアーキテクチャで構築されています。)

```bash
y1oing-bot/
├── .env.example              # Example environment file
├── .gitignore                # Files and directories to be ignored by Git
├── config.json               # Bot's static configuration
├── PROJECT_DOCUMENTATION.md  # Detailed project documentation
├── README.md                 # The main landing page for the repository
├── requirements.txt          # List of Python dependencies
├── run.py                    # The entry point script to start the bot
│
├── bot/
│   ├── __init__.py
│   ├── client.py               # Core bot client class, event handling
│   ├── main.py                 # Bot initialization and startup logic
│   └── cogs/                   # Command modules (Cogs), grouped by feature
│       ├── __init__.py
│       ├── playback.py
│       ├── playlist.py
│       ├── profile.py
│       ├── server_playlist.py
│       └── utility.py
│
├── data/                       # Persistent data (Generally not tracked by Git)
│   ├── playlists/
│   │   ├── server/
│   │   │   └── .gitkeep        # Placeholder to keep the directory in Git
│   │   └── solo/
│   │       └── .gitkeep
│   └── profiles/
│       └── .gitkeep
│
└── utils/
    ├── __init__.py
    ├── audio_handler.py          # Manages yt-dlp and FFmpeg in a separate process
    ├── player.py                 # The core playback state machine for a single server
    ├── playlist_manager.py       # Handles all CRUD logic for playlist data
    ├── profile_manager.py        # Handles loading/saving of user profiles
    └── views.py                  # Defines interactive UI components (Buttons, Menus)

---

## 5. Development Milestones

The project was developed through a structured, phased approach, ensuring each component was built upon a stable foundation. All planned phases are now complete.
(このプロジェクトは段階的なアプローチで開発され、各コンポーネントが安定した基盤の上に構築されることを保証しました。計画されたすべてのフェーズは現在完了しています。)

### Phase 1: Core Playback Engine `[COMPLETED]`
- **Objective**: Establish a stable and functional playback foundation.
- **Key Deliverables**:
    - `[✔]` Core commands (`/play`, `/pause`, `/stop`, etc.)
    - `[✔]` Interactive "Now Playing" panel
    - `[✔]` Functional queue management
    - `[✔]` Basic interactive search

### Phase 2: Playlist & User Systems `[COMPLETED]`
- **Objective**: Build comprehensive playlist and user-centric features.
- **Key Deliverables**:
    - `[✔]` Full implementation of personal and server-shared playlists
    - `[✔]` Complete permission model for server playlists
    - `[✔]` Track and queue looping functionality
    - `[✔]` User profile system for persistent settings

### Phase 3: Advanced Features & Optimization `[COMPLETED]`
- **Objective**: Enhance the audio experience and overall performance.
- **Key Deliverables**:
    - `[✔]` Advanced search capabilities
    - `[✔]` Gapless playback support via background buffering
    - `[✔]` Multi-band audio equalizer
    - `[✔]` Performance profiling and optimization

### Phase 4: Polish & Finalization `[COMPLETED]`
- **Objective**: Finalize the user experience and prepare for release.
- **Key Deliverables**:
    - `[✔]` Polished and helpful `/help` command
    - `[✔]` Final utility commands (`/feedback`, `/about`)
    - `[✔]` Extensive bug fixing and stability testing
```

### Final Project Status

| Milestone                 | Status          | Description (概要)                     |
|:--------------------------|:----------------|:---------------------------------------|
| Initial Design & Planning | ✅ Completed      | 設計・計画                             |
| Environment Setup         | ✅ Completed      | 環境構築                               |
| **Phase 1: Core Engine**  | ✅ Completed      | コアエンジン                           |
| **Phase 2: Playlists**    | ✅ Completed      | プレイリスト機能                       |
| **Phase 3: Advanced**     | ✅ Completed      | 高度な機能                             |
| **Phase 4: Finalization** | ✅ Completed      | 仕上げ                                 |
| **Official Release 1.0**  | 🚀 **Released**   | **リリース完了**                       |

[![Creater](https://cdn.discordapp.com/avatars/1030100948003065866/ed537c0f7ab8757d38afc475b5b69065.webp?size=30)](https://discord.com/users/1030100948003065866)
