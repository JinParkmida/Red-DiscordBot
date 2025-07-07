import os
import json
from redbot.core import commands
from discord.ext.commands import Context
from discord import Message, Interaction, TextStyle
from discord import app_commands
from discord.ui import Modal, TextInput, View
import re
from collections import defaultdict
from collections.abc import AsyncIterable
from discord.ext.commands import CommandError
from discord import Embed

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "data", "memorypalace")
DEFAULT_ROOMS = {
    "library": {"name": "Library", "icon": "📚", "memories": [], "subrooms": {}},
    "gallery": {"name": "Gallery", "icon": "🎨", "memories": [], "subrooms": {}},
    "archive": {"name": "Archive", "icon": "📦", "memories": [], "subrooms": {}},
    "workshop": {"name": "Workshop", "icon": "🔨", "memories": [], "subrooms": {}},
}

class PlaceMemoryModal(Modal, title="Place in Memory Palace"):
    room = TextInput(label="Room (e.g. library or workshop.botcorner)", required=True)  # type: ignore
    title = TextInput(label="Title for this memory", required=True)  # type: ignore
    description = TextInput(label="Description (optional)", required=False, style=TextStyle.paragraph)  # type: ignore

    def __init__(self, bot, message, callback):
        super().__init__()
        self.bot = bot
        self.message = message
        self._callback = callback

    async def on_submit(self, interaction: Interaction):
        # type: ignore
        await self._callback(
            interaction,
            self.message,
            getattr(self.room, 'value', self.room),  # type: ignore
            getattr(self.title, 'value', self.title),  # type: ignore
            getattr(self.description, 'value', self.description)  # type: ignore
        )

class MemoryPalace(commands.Cog):
    """Persistent, visual memory spaces for your server."""

    def __init__(self, bot):
        self.bot = bot
        os.makedirs(DATA_DIR, exist_ok=True)

    def cog_unload(self):
        pass

    async def cog_load(self):
        print("[MemoryPalace] Cog loaded. Use /palace to get started!")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        channel = getattr(guild, 'system_channel', None)
        if channel is None:
            channel = next((c for c in getattr(guild, 'text_channels', []) if getattr(c.permissions_for(guild.me), 'send_messages', False)), None)
        if channel:
            await channel.send("🏰 **Memory Palace is here!** Use `/palace` to explore your server's memory map and `/help memorypalace` for more info.")

    def _get_guild_file(self, guild_id):
        return os.path.join(DATA_DIR, f"{guild_id}.json")

    def _load_palace(self, guild_id):
        path = self._get_guild_file(guild_id)
        if not os.path.exists(path):
            return {"rooms": json.loads(json.dumps(DEFAULT_ROOMS))}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_palace(self, guild_id, data):
        path = self._get_guild_file(guild_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _find_room(self, rooms, room_path):
        current = rooms
        for name in room_path:
            if not isinstance(current, dict) or name not in current or current[name] is None:
                return None
            current = current[name]
            if isinstance(current, dict) and "subrooms" in current:
                current = current["subrooms"]
        return current

    def _get_room_and_parent(self, rooms, room_path):
        current = rooms
        parent = None
        key = None
        for name in room_path:
            if not isinstance(current, dict) or name not in current or current[name] is None:
                return None, None, None
            parent = current
            key = name
            current = current[name]
            if isinstance(current, dict) and "subrooms" in current:
                current = current["subrooms"]
        if parent and key:
            return parent.get(key), parent, key
        return None, None, None

    def _suggest_subroom(self, room_dict):
        if not isinstance(room_dict, dict):
            return []
        keyword_counts = {}
        for mem in room_dict.get("memories", []):
            title = mem.get("title", "")
            description = mem.get("description", "")
            text = f"{title} {description}".lower()
            words = re.findall(r"\b\w{4,}\b", text)
            for word in words:
                keyword_counts[word] = keyword_counts.get(word, 0) + 1
        suggestions = [k for k, v in keyword_counts.items() if v > 5]
        return suggestions

    def _find_all_memory_locations(self, guild_id, message_id):
        palace = self._load_palace(guild_id)
        rooms = palace.get("rooms", {})
        locations = []
        def search(room_path, room_dict):
            for i, mem in enumerate(room_dict.get("memories", [])):
                if mem.get("message_id") == message_id:
                    locations.append((room_path, i, mem))
            for subname, subdata in room_dict.get("subrooms", {}).items():
                search(room_path + [subname], subdata)
        for name, data in rooms.items():
            search([name], data)
        return locations

    @commands.hybrid_command()
    async def palace(self, ctx: Context):
        """Show the Memory Palace map."""
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        if not rooms:
            await ctx.send("No rooms found. Use /addroom to create your first room!")
            return
        def room_line(room, data, indent=""):
            icon = data.get('icon', '?')
            name = data.get('name', room)
            memories = data.get('memories', [])
            line = f"{indent}{icon} {name} [{len(memories)} memories]"
            lines = [line]
            suggestions = self._suggest_subroom(data)
            if suggestions:
                lines.append(f"{indent}  💡 Suggest sub-room for: {', '.join(suggestions)}")
            for subname, subdata in data.get("subrooms", {}).items():
                lines += room_line(subname, subdata, indent + "  ")
            return lines
        map_lines = [f"🏰 {getattr(getattr(ctx, 'guild', None), 'name', 'Unknown Guild')} Memory Palace 🏰", "┌─────────────────────────────┐"]
        for name, data in rooms.items():
            map_lines += room_line(name, data)
        map_lines.append("└─────────────────────────────┘")
        await ctx.send(f"```\n" + "\n".join(map_lines) + "\n```")

    @commands.hybrid_command()
    async def addroom(self, ctx: Context, name: str, parent: str = "", icon: str = "🏷️"):
        """Add a new room or sub-room. Use parent for sub-room (e.g. /addroom BotCorner workshop)."""
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        if parent:
            parent = parent.lower()
            if parent not in rooms:
                await ctx.send(f"❌ Parent room '{parent}' does not exist. Available: {', '.join(rooms.keys())}")
                return
            if name.lower() in rooms[parent].get("subrooms", {}):
                await ctx.send(f"❌ Sub-room '{name}' already exists in {parent}.")
                return
            rooms[parent].setdefault("subrooms", {})[name.lower()] = {"name": name, "icon": icon, "memories": [], "subrooms": {}}
            self._save_palace(getattr(ctx.guild, 'id', None), palace)
            await ctx.send(f"✅ Sub-room '{name}' added to {parent}!")
        else:
            if name.lower() in rooms:
                await ctx.send(f"❌ Room '{name}' already exists.")
                return
            rooms[name.lower()] = {"name": name, "icon": icon, "memories": [], "subrooms": {}}
            self._save_palace(getattr(ctx.guild, 'id', None), palace)
            await ctx.send(f"✅ Room '{name}' added!")

    async def _maybe_suggest_subroom(self, ctx, room_dict, room_path):
        suggestions = self._suggest_subroom(room_dict)
        if suggestions:
            await ctx.send(f"💡 Consider creating a sub-room for: {', '.join(suggestions)} in {'.'.join(room_path)} (use /addroom <name> {'.'.join(room_path)})")

    @commands.hybrid_command()
    async def place(self, ctx: Context, room: str, title: str, *, description: str = ""):
        """Place the last message in the channel into a Memory Palace room or sub-room (use room.subroom)."""
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        room_path = room.lower().split(".")
        current = rooms
        for name in room_path:
            if not isinstance(current, dict) or name not in current or current[name] is None:
                await ctx.send(f"❌ Room path '{room}' does not exist.")
                return
            current = current[name]
            if isinstance(current, dict) and "subrooms" in current:
                current = current["subrooms"]
        # Get the last message before the command
        messages = []
        history = getattr(ctx.channel, 'history', None)
        if callable(history):
            hist_obj = history(limit=2)
            if isinstance(hist_obj, AsyncIterable):
                async for m in hist_obj:
                    messages.append(m)
        target_msg = messages[1] if len(messages) > 1 else None
        if not target_msg or not hasattr(target_msg, 'id') or not hasattr(target_msg, 'author') or not hasattr(target_msg, 'channel'):
            await ctx.send("❌ Couldn't find a message to place.")
            return
        author = getattr(target_msg, 'author', None)
        channel = getattr(target_msg, 'channel', None)
        if author is None or getattr(author, 'id', None) is None or channel is None or getattr(channel, 'id', None) is None or getattr(ctx, 'author', None) is None or getattr(getattr(ctx, 'author', None), 'id', None) is None:
            await ctx.send("❌ Could not determine message author, channel, or placer.")
            return
        memory = {
            "message_id": getattr(target_msg, 'id', None),
            "channel_id": getattr(channel, 'id', None),
            "author_id": getattr(author, 'id', None),
            "placer_id": getattr(getattr(ctx, 'author', None), 'id', None),
            "title": title,
            "description": description,
            "jump_url": getattr(target_msg, 'jump_url', ""),
        }
        parent = rooms
        for name in room_path[:-1]:
            parent = parent[name]["subrooms"]
        parent[room_path[-1]]["memories"].append(memory)
        self._save_palace(getattr(ctx.guild, 'id', None), palace)
        await ctx.send(f"✅ Placed memory in {room}! Use /palace to view.")
        await self._maybe_suggest_subroom(ctx, parent[room_path[-1]], room_path)

    @commands.hybrid_command()
    async def enter(self, ctx: Context, room: str):
        """List all memories in a room or sub-room (use room.subroom)."""
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        room_path = room.lower().split(".")
        current = rooms
        for name in room_path:
            if not isinstance(current, dict) or name not in current or current[name] is None:
                await ctx.send(f"❌ Room path '{room}' does not exist.")
                return
            current = current[name]
            if isinstance(current, dict) and "subrooms" in current:
                current = current["subrooms"]
        parent = rooms
        for name in room_path[:-1]:
            parent = parent[name]["subrooms"]
        memories = parent[room_path[-1]].get("memories", [])
        if not memories:
            await ctx.send(f"❌ No memories in {room} yet.")
            return
        lines = [f"**{parent[room_path[-1]].get('icon', '?')} {parent[room_path[-1]].get('name', room)}**"]
        for i, mem in enumerate(memories, 1):
            desc = mem.get("description", "")
            desc = desc[:60] + ("..." if len(desc) > 60 else "")
            lines.append(f"`{i}.` **{mem.get('title', '?')}** — {desc}")
        await ctx.send("\n".join(lines))

    @commands.hybrid_command()
    async def memory(self, ctx: Context, room: str, index: int):
        """Show a specific memory from a room or sub-room by its number (use room.subroom)."""
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        room_path = room.lower().split(".")
        current = rooms
        for name in room_path:
            if not isinstance(current, dict) or name not in current or current[name] is None:
                await ctx.send(f"❌ Room path '{room}' does not exist.")
                return
            current = current[name]
            if isinstance(current, dict) and "subrooms" in current:
                current = current["subrooms"]
        parent = rooms
        for name in room_path[:-1]:
            parent = parent[name]["subrooms"]
        memories = parent[room_path[-1]].get("memories", [])
        if not memories or index < 1 or index > len(memories):
            await ctx.send(f"❌ Invalid memory number. Use /enter {room} to see available memories.")
            return
        mem = memories[index - 1]
        locations = self._find_all_memory_locations(getattr(ctx.guild, 'id', None), mem.get("message_id"))
        embed = Embed()
        embed.title = mem.get("title", "?")
        embed.description = mem.get("description", "(No description)") or "(No description)"
        embed.add_field(name="Placed by", value=f"<@{mem.get('placer_id', '?')}>", inline=True)
        embed.add_field(name="Original Author", value=f"<@{mem.get('author_id', '?')}>", inline=True)
        embed.add_field(name="Jump to Message", value=f"[Go to message]({mem.get('jump_url', '')})", inline=False)
        if len(locations) > 1:
            loc_lines = []
            for loc_path, idx, m in locations:
                placer = m.get("placer_id", "?")
                context = m.get("description", "")
                loc_lines.append(f"{'/'.join(loc_path)} (by <@{placer}>): {context[:40]}")
            embed.add_field(name="Other rooms/contexts", value="\n".join(loc_lines), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def movememory(self, ctx: Context, from_room: str, index: int, to_room: str):
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        from_path = from_room.lower().split(".")
        to_path = to_room.lower().split(".")
        parent = rooms
        for name in from_path[:-1]:
            parent = parent[name]["subrooms"]
        memories = parent[from_path[-1]].get("memories", [])
        if not memories or index < 1 or index > len(memories):
            await ctx.send(f"❌ Invalid memory number. Use /enter {from_room} to see available memories.")
            return
        mem = memories.pop(index - 1)
        parent_to = rooms
        for name in to_path[:-1]:
            parent_to = parent_to[name]["subrooms"]
        parent_to[to_path[-1]].setdefault("memories", []).append(mem)
        self._save_palace(getattr(ctx.guild, 'id', None), palace)
        await ctx.send(f"✅ Moved memory to {to_room}.")

    @commands.hybrid_command()
    async def renamememory(self, ctx: Context, room: str, index: int, new_title: str):
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        room_path = room.lower().split(".")
        parent = rooms
        for name in room_path[:-1]:
            parent = parent[name]["subrooms"]
        memories = parent[room_path[-1]].get("memories", [])
        if not memories or index < 1 or index > len(memories):
            await ctx.send(f"❌ Invalid memory number. Use /enter {room} to see available memories.")
            return
        memories[index - 1]["title"] = new_title
        self._save_palace(getattr(ctx.guild, 'id', None), palace)
        await ctx.send(f"✅ Memory renamed to {new_title}.")

    @commands.hybrid_command()
    async def deletememory(self, ctx: Context, room: str, index: int):
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        room_path = room.lower().split(".")
        parent = rooms
        for name in room_path[:-1]:
            parent = parent[name]["subrooms"]
        memories = parent[room_path[-1]].get("memories", [])
        if not memories or index < 1 or index > len(memories):
            await ctx.send(f"❌ Invalid memory number. Use /enter {room} to see available memories.")
            return
        del memories[index - 1]
        self._save_palace(getattr(ctx.guild, 'id', None), palace)
        await ctx.send(f"✅ Memory deleted.")

    @commands.hybrid_command()
    async def renameroom(self, ctx: Context, room: str, new_name: str):
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        room_path = room.lower().split(".")
        parent = rooms
        for name in room_path[:-1]:
            parent = parent[name]["subrooms"]
        parent[room_path[-1]]["name"] = new_name
        self._save_palace(getattr(ctx.guild, 'id', None), palace)
        await ctx.send(f"✅ Room renamed to {new_name}.")

    @commands.hybrid_command()
    async def deleteroom(self, ctx: Context, room: str):
        palace = self._load_palace(getattr(ctx.guild, 'id', None))
        rooms = palace.get("rooms", {})
        room_path = room.lower().split(".")
        if len(room_path) == 1:
            if room_path[0] in rooms:
                del rooms[room_path[0]]
                self._save_palace(getattr(ctx.guild, 'id', None), palace)
                await ctx.send(f"✅ Room '{room}' deleted.")
                return
            else:
                await ctx.send(f"❌ Room '{room}' does not exist.")
                return
        parent = rooms
        for name in room_path[:-1]:
            parent = parent[name]["subrooms"]
        if room_path[-1] in parent:
            del parent[room_path[-1]]
            self._save_palace(getattr(ctx.guild, 'id', None), palace)
            await ctx.send(f"✅ Sub-room '{room}' deleted.")
        else:
            await ctx.send(f"❌ Sub-room '{room}' does not exist.")

    @commands.hybrid_command(name="memorypalacehelp")
    async def memorypalace_help(self, ctx: Context):
        embed = Embed(title="🏰 Memory Palace Help & Onboarding",
                      description="Turn your server's history into an explorable memory space!\n\n**Core Features:**")
        embed.add_field(
            name="/palace",
            value="Show the ASCII map of your Memory Palace, with all rooms and memory counts.",
            inline=False)
        embed.add_field(
            name="/place <room> <title> [description]",
            value="Place the last message in the channel into a room or sub-room. Use dot notation for sub-rooms (e.g., `workshop.botcorner`).",
            inline=False)
        embed.add_field(
            name="Right-click → Place in Memory Palace",
            value="Use the context menu on any message to place it in a room with a custom title and description.",
            inline=False)
        embed.add_field(
            name="/enter <room>",
            value="List all memories in a room or sub-room.",
            inline=False)
        embed.add_field(
            name="/memory <room> <index>",
            value="Show details and all perspectives for a specific memory.",
            inline=False)
        embed.add_field(
            name="/addroom <name> [parent] [icon]",
            value="Create a new room or sub-room. Use the parent argument for sub-rooms.",
            inline=False)
        embed.add_field(
            name="/movememory, /renamememory, /deletememory",
            value="Move, rename, or delete memories.",
            inline=False)
        embed.add_field(
            name="/renameroom, /deleteroom",
            value="Rename or delete rooms and sub-rooms.",
            inline=False)
        embed.add_field(
            name="Smart Suggestions",
            value="The bot will suggest new sub-rooms if it detects patterns in your memories.",
            inline=False)
        embed.add_field(
            name="Overlapping Perspectives",
            value="Multiple users can place the same message in different rooms, each with their own context.",
            inline=False)
        embed.set_footer(text="Tip: Use /memorypalacehelp anytime for a refresher! Feedback and ideas welcome.")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, CommandError):
            await ctx.send(f"❌ {str(error)}")
        else:
            await ctx.send("❌ An unexpected error occurred. Please try again or contact the bot owner.")

@app_commands.context_menu(name="Place in Memory Palace")
async def place_in_palace_context_menu(interaction: Interaction, message: Message):
    cog = getattr(getattr(interaction, 'client', None), 'get_cog', lambda name: None)("MemoryPalace")
    if cog is None or not hasattr(cog, '_handle_place_modal'):
        await interaction.response.send_message("❌ MemoryPalace cog not loaded.", ephemeral=True)
        return
    modal = PlaceMemoryModal(getattr(cog, 'bot', None), message, getattr(cog, '_handle_place_modal', None))
    await interaction.response.send_modal(modal)

# This method must be attached to the cog instance after class definition
async def _handle_place_modal(self, interaction: Interaction, message: Message, room: str, title: str, description: str):
    guild = getattr(interaction, 'guild', None)
    if not guild:
        await interaction.response.send_message("❌ This can only be used in a server.", ephemeral=True)
        return
    palace = self._load_palace(getattr(guild, 'id', None))
    rooms = palace.get("rooms", {})
    room_path = room.lower().split(".")
    current = rooms
    for name in room_path:
        if not isinstance(current, dict) or name not in current or current[name] is None:
            await interaction.response.send_message(f"❌ Room path '{room}' does not exist.", ephemeral=True)
            return
        current = current[name]
        if isinstance(current, dict) and "subrooms" in current:
            current = current["subrooms"]
    parent = rooms
    for name in room_path[:-1]:
        parent = parent[name]["subrooms"]
    memory = {
        "message_id": getattr(message, 'id', None),
        "channel_id": getattr(getattr(message, 'channel', None), 'id', None),
        "author_id": getattr(getattr(message, 'author', None), 'id', None),
        "placer_id": getattr(getattr(interaction, 'user', None), 'id', None),
        "title": title,
        "description": description,
        "jump_url": getattr(message, 'jump_url', ""),
    }
    parent[room_path[-1]]["memories"].append(memory)
    self._save_palace(getattr(guild, 'id', None), palace)
    await interaction.response.send_message(f"✅ Placed memory in {room}! Use /palace to view.", ephemeral=True)
    suggestions = self._suggest_subroom(parent[room_path[-1]])
    if suggestions:
        await interaction.followup.send(f"💡 Consider creating a sub-room for: {', '.join(suggestions)} in {room} (use /addroom <name> {room})", ephemeral=True)

setattr(MemoryPalace, '_handle_place_modal', _handle_place_modal)

def setup(bot):
    bot.add_cog(MemoryPalace(bot))
    bot.tree.add_command(place_in_palace_context_menu) 