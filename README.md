# Red Discord Bot

A highly customizable, modular, and self-hosted Discord bot for your server.

---

**Developer:** Jin Park

---

## Overview

Red Discord Bot is a fully modular bot, meaning all features and commands can be enabled or disabled to your liking, making it completely customizable. You host and maintain your own instance, giving you full control over your bot's features and data.

**Key Features:**

- **Moderation:** Kick, ban, softban, hackban, mod-log, filter, chat cleanup, warnings, mutes, permissions, and more.
- **Audio:** Music playback from YouTube, SoundCloud, local files, playlists, and queues. Includes equalizer and advanced audio controls.
- **Custom Commands:** Create your own commands and aliases for your server.
- **Image & Media:** Image manipulation and fun image commands.
- **Downloader:** Install and manage third-party cogs (plugins) directly from Discord.
- **Admin Tools:** Announcements, admin utilities, and automation.
- **Streams & Reports:** Stream alerts, reporting tools, and more.
- **Memory Palace:**
    - Persistent, visual memory spaces for your server.
    - Organize messages, files, and memories into themed rooms and sub-rooms.
    - ASCII map navigation, context menu support, smart suggestions, and robust management tools.
    - Overlapping perspectives: multiple users can place the same message in different rooms with their own context.
    - All data is stored locally for privacy and control.

**Extensible:**
- Easily add or remove features by loading or unloading cogs.
- Install third-party cogs for even more functionality.

---

## Installation

Red Discord Bot is supported on:
- **Windows**
- **MacOS**
- **Most major Linux distributions**

### Quick Start

1. **Install Python 3.8–3.11** and [git](https://git-scm.com/).
2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv redenv
   source redenv/bin/activate  # On Windows: redenv\Scripts\activate
   ```
3. **Install Red Discord Bot:**
   ```bash
   python -m pip install -U pip wheel
   python -m pip install -U Red-DiscordBot
   ```
4. **Set up your instance:**
   ```bash
   redbot-setup
   ```
   Follow the prompts to configure your data location, backend, and instance name.
5. **Run the bot:**
   ```bash
   redbot <your instance name>
   ```
   The bot will walk you through the initial setup, including your Discord bot token and prefix.

For detailed platform-specific instructions, see the [docs](https://docs.discord.red/en/stable/install_guides/).

---

## Usage & Features

- All features are modular and can be enabled/disabled as needed.
- Use `[p]help` (replace `[p]` with your prefix) in Discord to see all available commands.
- The Memory Palace feature provides `/palace`, `/place`, `/enter`, `/memory`, `/addroom`, `/movememory`, `/renamememory`, `/deletememory`, `/renameroom`, `/deleteroom`, and `/memorypalacehelp` commands, as well as right-click context menu support.

---

## Extending Red

- Red supports third-party cogs (plugins) for additional features.
- Use the Downloader cog to install and manage cogs directly from Discord.
- See the [official documentation](https://docs.discord.red/en/stable/guide_cog_creation.html) for creating your own cogs.

---

## License

This project is licensed under the [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.en.html).

---

## Credits

Developed and maintained by Jin Park.

Red Discord Bot is inspired by the open-source community and is not affiliated with Discord Inc.

---
