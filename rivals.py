##https://discord.com/oauth2/authorize?client_id=1341684106743775283&permissions=274877991936&scope=bot%20applications.commands

import os
import math
import random
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord import option, Embed, Color, Interaction
from discord.ui import Button, View

# Load the .env file to get the token
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Configure intents (presences are required for activity checking)
intents = discord.Intents.default()
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# A set to keep track of members we ignore
ignored_members = set()

#######################################
# DummyMember class for filler slots  #
#######################################

class DummyMember:
    def __init__(self, display_name, dummy_id):
        self.display_name = display_name
        self.id = dummy_id

#######################################
#         Bot Event Handlers          #
#######################################

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

#######################################
#         IGNORE COMMANDS             #
#######################################

@bot.slash_command(name="ignore", description="Exclude a user from random assignment.")
@option("user", discord.Member, description="User to ignore")
async def ignore_user(ctx: discord.ApplicationContext, user: discord.Member):
    if user.bot:
        await ctx.respond(f"{user.display_name} is a bot and won't be assigned anyway.", ephemeral=True)
        return
    if user.id in ignored_members:
        await ctx.respond(f"{user.display_name} is already ignored.", ephemeral=True)
    else:
        ignored_members.add(user.id)
        await ctx.respond(f"Ignoring {user.display_name} from random assignment.", ephemeral=True)

@bot.slash_command(name="unignore", description="Remove a user from the ignore list.")
@option("user", discord.Member, description="User to unignore")
async def unignore_user(ctx: discord.ApplicationContext, user: discord.Member):
    if user.id not in ignored_members:
        await ctx.respond(f"{user.display_name} is not in the ignore list.", ephemeral=True)
    else:
        ignored_members.remove(user.id)
        await ctx.respond(f"{user.display_name} is no longer ignored.", ephemeral=True)

#######################################
#      Helper Functions               #
#######################################

def get_marvel_players_from_voice_channel(voice_channel: discord.VoiceChannel):
    """
    Returns a list of non-bot, non-ignored members in the voice channel
    who are actively playing 'Marvel Rivals'.
    """
    marvel_players = []
    for member in voice_channel.members:
        if member.bot or member.id in ignored_members:
            continue
        playing_marvel = False
        if member.activities:
            for activity in member.activities:
                if activity.name and activity.name.lower() == "marvel rivals":
                    playing_marvel = True
                    break
        if playing_marvel:
            marvel_players.append(member)
    return marvel_players

def assign_roles_mapping(players):
    """
    Given a list of exactly 6 players (active and/or dummy fillers),
    randomly assign roles as follows:
      - Approximately 20% Vanguard, 20% Duelist, 20% Strategist.
      - 50% of the combined Vanguard & Duelist players become Flex,
        meaning they get both a Vanguard and a Duelist suggestion.
      - Any players falling outside these slices (if any) are assigned a random role
        among Vanguard, Duelist, or Strategist.
    Returns a tuple (role_map, ordered_players) where:
      - role_map is a dict mapping player.id to a tuple:
           ("Vanguard", suggestion)
           ("Duelist", suggestion)
           ("Strategist", suggestion)
           ("Flex", vanguard_suggestion, duelist_suggestion)
      - ordered_players is the list in the original order (active players first, then fillers).
    """
    # Work on a copy and randomize order for assignment
    players_copy = players[:]  
    random.shuffle(players_copy)
    total = len(players_copy)  # should be 6

    # Calculate counts using ceil (for 6, each will be 2 because ceil(6*0.2)=2; 2+2+2 = 6)
    vanguard_count = math.ceil(total * 0.2)
    duelist_count = math.ceil(total * 0.2)
    strategist_count = math.ceil(total * 0.2)
    
    vanguard = players_copy[:vanguard_count]
    duelist = players_copy[vanguard_count:vanguard_count + duelist_count]
    strategist = players_copy[vanguard_count + duelist_count:vanguard_count + duelist_count + strategist_count]
    remaining = players_copy[vanguard_count + duelist_count + strategist_count:]
    
    # Determine flex players from the combined Vanguard and Duelist groups
    combined_vd = vanguard + duelist
    random.shuffle(combined_vd)
    flex_count = math.floor(len(combined_vd) * 0.5)
    flex_players = set(combined_vd[:flex_count])
    
    vanguard_non_flex = [m for m in vanguard if m not in flex_players]
    duelist_non_flex = [m for m in duelist if m not in flex_players]
    flex_list = [m for m in combined_vd if m in flex_players]
    strategist_list = strategist

    # Character suggestion pools
    vanguard_chars = ["Captain America", "Thor", "Hulk", "Venom", "Peni Parker", "Magneto", "Doctor Strange", "Groot"]
    duelist_chars = [
        "Mister Fantastic", "Wolverine", "Hawkeye", "Iron Fist", "Moon Knight", "Psylocke", "Squirrel Girl",
        "Winter Soldier", "Black Widow", "Namor", "Storm", "Scarlet Witch", "Star-Lord", "Magik",
        "Spider-Man", "The Punisher", "Hela", "Iron Man", "Black Panther"
    ]
    strategist_chars = ["Invisible Woman", "Cloak and Dagger", "Jeff the Land Shark", "Adam Warlock", "Luna Snow", "Loki", "Rocket Raccoon", "Mantis"]

    total_vanguard_needed = len(vanguard_non_flex) + len(flex_list)
    total_duelist_needed = len(duelist_non_flex) + len(flex_list)
    
    if total_vanguard_needed > len(vanguard_chars):
        vanguard_pool = random.sample(vanguard_chars * ((total_vanguard_needed // len(vanguard_chars)) + 1), total_vanguard_needed)
    else:
        vanguard_pool = random.sample(vanguard_chars, total_vanguard_needed)
        
    if total_duelist_needed > len(duelist_chars):
        duelist_pool = random.sample(duelist_chars * ((total_duelist_needed // len(duelist_chars)) + 1), total_duelist_needed)
    else:
        duelist_pool = random.sample(duelist_chars, total_duelist_needed)
        
    if len(strategist_list) > len(strategist_chars):
        strategist_pool = random.sample(strategist_chars * ((len(strategist_list) // len(strategist_chars)) + 1), len(strategist_list))
    else:
        strategist_pool = random.sample(strategist_chars, len(strategist_list))
    
    role_map = {}
    # Assign roles with suggestions
    for m in vanguard_non_flex:
        role_map[m.id] = ("Vanguard", vanguard_pool.pop(0))
    for m in duelist_non_flex:
        role_map[m.id] = ("Duelist", duelist_pool.pop(0))
    for m in strategist_list:
        role_map[m.id] = ("Strategist", strategist_pool.pop(0))
    for m in flex_list:
        role_map[m.id] = ("Flex", vanguard_pool.pop(0), duelist_pool.pop(0))
    
    # For any players not assigned in the above slices, assign a random role
    for m in remaining:
        chosen_role = random.choice(["Vanguard", "Duelist", "Strategist"])
        if chosen_role == "Vanguard":
            suggestion = vanguard_pool.pop(0) if vanguard_pool else random.choice(vanguard_chars)
            role_map[m.id] = ("Vanguard", suggestion)
        elif chosen_role == "Duelist":
            suggestion = duelist_pool.pop(0) if duelist_pool else random.choice(duelist_chars)
            role_map[m.id] = ("Duelist", suggestion)
        else:
            suggestion = strategist_pool.pop(0) if strategist_pool else random.choice(strategist_chars)
            role_map[m.id] = ("Strategist", suggestion)
    
    # Return the role mapping and the original order (active first, then fillers)
    return role_map, players

def build_embed(role_map, players):
    """
    Build an embed from the role_map and the list of players.
    The players are iterated in the provided order.
    """
    role_lines = []
    for p in players:
        info = role_map.get(p.id, ("",))
        if info[0] == "Vanguard":
            role_lines.append(f"**{p.display_name}** → Vanguard (Suggested: {info[1]})")
        elif info[0] == "Duelist":
            role_lines.append(f"**{p.display_name}** → Duelist (Suggested: {info[1]})")
        elif info[0] == "Strategist":
            role_lines.append(f"**{p.display_name}** → Strategist (Suggested: {info[1]})")
        elif info[0] == "Flex":
            role_lines.append(
                f"**{p.display_name}** → Flex (Choose either: Vanguard [Suggested: {info[1]}] or Duelist [Suggested: {info[2]}])"
            )
        else:
            role_lines.append(f"**{p.display_name}** → Unassigned")
    embed = Embed(
        title="Marvel Rivals Role Assignments",
        description="\n".join(role_lines),
        color=Color.blue()
    )
    return embed

def reroll_characters(role_map):
    """
    Given an existing role_map (with role assignments fixed),
    reassign new character suggestions for each role.
    Returns a new role_map with updated suggestions.
    """
    # Character pools
    vanguard_chars = ["Captain America", "Thor", "Hulk", "Venom", "Peni Parker", "Magneto", "Doctor Strange", "Groot"]
    duelist_chars = [
        "Mister Fantastic", "Wolverine", "Hawkeye", "Iron Fist", "Moon Knight", "Psylocke", "Squirrel Girl",
        "Winter Soldier", "Black Widow", "Namor", "Storm", "Scarlet Witch", "Star-Lord", "Magik",
        "Spider-Man", "The Punisher", "Hela", "Iron Man", "Black Panther"
    ]
    strategist_chars = ["Invisible Woman", "Cloak and Dagger", "Jeff the Land Shark", "Adam Warlock", "Luna Snow", "Loki", "Rocket Raccoon", "Mantis"]
    
    # Count requirements based on the current assignments
    vanguard_ids = [mid for mid, val in role_map.items() if val[0] == "Vanguard"]
    duelist_ids = [mid for mid, val in role_map.items() if val[0] == "Duelist"]
    strategist_ids = [mid for mid, val in role_map.items() if val[0] == "Strategist"]
    flex_ids = [mid for mid, val in role_map.items() if val[0] == "Flex"]
    
    total_vanguard_needed = len(vanguard_ids) + len(flex_ids)
    total_duelist_needed = len(duelist_ids) + len(flex_ids)
    
    if total_vanguard_needed > len(vanguard_chars):
        vanguard_pool = random.sample(vanguard_chars * ((total_vanguard_needed // len(vanguard_chars)) + 1), total_vanguard_needed)
    else:
        vanguard_pool = random.sample(vanguard_chars, total_vanguard_needed)
    
    if total_duelist_needed > len(duelist_chars):
        duelist_pool = random.sample(duelist_chars * ((total_duelist_needed // len(duelist_chars)) + 1), total_duelist_needed)
    else:
        duelist_pool = random.sample(duelist_chars, total_duelist_needed)
    
    if len(strategist_ids) > len(strategist_chars):
        strategist_pool = random.sample(strategist_chars * ((len(strategist_ids) // len(strategist_chars)) + 1), len(strategist_ids))
    else:
        strategist_pool = random.sample(strategist_chars, len(strategist_ids))
    
    new_role_map = {}
    for member_id, val in role_map.items():
        role = val[0]
        if role == "Vanguard":
            new_role_map[member_id] = ("Vanguard", vanguard_pool.pop(0))
        elif role == "Duelist":
            new_role_map[member_id] = ("Duelist", duelist_pool.pop(0))
        elif role == "Strategist":
            new_role_map[member_id] = ("Strategist", strategist_pool.pop(0))
        elif role == "Flex":
            new_role_map[member_id] = ("Flex", vanguard_pool.pop(0), duelist_pool.pop(0))
        else:
            new_role_map[member_id] = val
    return new_role_map

#######################################
#      Custom View and Buttons        #
#######################################

class RoleAssignmentView(View):
    def __init__(self, voice_channel_id, role_map, ordered_players):
        super().__init__(timeout=None)
        self.voice_channel_id = voice_channel_id
        self.role_map = role_map
        self.ordered_players = ordered_players

class RerollRolesButton(Button):
    def __init__(self, label="Reroll", style=discord.ButtonStyle.primary):
        super().__init__(label=label, style=style)
    
    async def callback(self, interaction: Interaction):
        # Re-read the voice channel and reassign roles from scratch
        voice_channel = interaction.guild.get_channel(self.view.voice_channel_id)
        if voice_channel is None:
            await interaction.response.send_message("Voice channel not found.", ephemeral=True)
            return
        active_players = get_marvel_players_from_voice_channel(voice_channel)
        active_players = sorted(active_players, key=lambda x: x.display_name.lower())
        if len(active_players) > 6:
            players = active_players[:6]
        elif len(active_players) < 6:
            num_fillers = 6 - len(active_players)
            filler_names = ["Team Member A", "Team Member B", "Team Member C", "Team Member D", "Team Member E", "Team Member F"]
            fillers = []
            dummy_start = 1000000
            for i in range(num_fillers):
                fillers.append(DummyMember(filler_names[i], dummy_start + i))
            players = active_players + fillers
        else:
            players = active_players
        new_role_map, new_ordered_players = assign_roles_mapping(players)
        self.view.role_map = new_role_map
        self.view.ordered_players = new_ordered_players
        new_embed = build_embed(new_role_map, new_ordered_players)
        await interaction.response.edit_message(embed=new_embed, view=self.view)

class RerollCharactersButton(Button):
    def __init__(self, label="Reroll Character", style=discord.ButtonStyle.secondary):
        super().__init__(label=label, style=style)
    
    async def callback(self, interaction: Interaction):
        # Reroll only character suggestions while preserving role assignments
        new_role_map = reroll_characters(self.view.role_map)
        self.view.role_map = new_role_map
        new_embed = build_embed(new_role_map, self.view.ordered_players)
        await interaction.response.edit_message(embed=new_embed, view=self.view)

#######################################
#      ASSIGN ROLES COMMAND           #
#######################################

@bot.slash_command(
    name="assign_roles",
    description="Assign roles for Marvel Rivals from a specified voice channel. Always shows exactly 6 team members."
)
@option("voice_channel", discord.VoiceChannel, description="Voice channel to scan for active users playing Marvel Rivals")
async def assign_roles(ctx: discord.ApplicationContext, voice_channel: discord.VoiceChannel):
    active_players = get_marvel_players_from_voice_channel(voice_channel)
    active_players = sorted(active_players, key=lambda x: x.display_name.lower())
    if len(active_players) > 6:
        players = active_players[:6]
    elif len(active_players) < 6:
        num_fillers = 6 - len(active_players)
        filler_names = ["Team Member A", "Team Member B", "Team Member C", "Team Member D", "Team Member E", "Team Member F"]
        fillers = []
        dummy_start = 1000000
        for i in range(num_fillers):
            fillers.append(DummyMember(filler_names[i], dummy_start + i))
        players = active_players + fillers
    else:
        players = active_players

    role_map, ordered_players = assign_roles_mapping(players)
    embed = build_embed(role_map, ordered_players)
    view = RoleAssignmentView(voice_channel_id=voice_channel.id, role_map=role_map, ordered_players=ordered_players)
    view.add_item(RerollRolesButton())
    view.add_item(RerollCharactersButton())
    await ctx.respond(embed=embed, view=view)

#######################################
#         DEBUG COMMANDS              #
#######################################

@bot.slash_command(name="debug_members", description="List members in this channel.")
async def debug_members(ctx: discord.ApplicationContext):
    members = ctx.channel.members
    member_names = [member.display_name for member in members if not member.bot]
    if member_names:
        await ctx.respond("Members in this channel:\n" + "\n".join(member_names), ephemeral=True)
    else:
        await ctx.respond("No non-bot members found in this channel.", ephemeral=True)

@bot.slash_command(
    name="debug_activities",
    description="List current activities of channel members (for debugging)."
)
async def debug_activities(ctx: discord.ApplicationContext):
    channel_members = ctx.channel.members
    debug_lines = []
    for member in channel_members:
        if member.bot:
            continue
        if member.activities:
            for activity in member.activities:
                debug_lines.append(f"{member.display_name}: {activity.name} (Type: {activity.type})")
        else:
            debug_lines.append(f"{member.display_name}: No activities found")
    if debug_lines:
        await ctx.respond("\n".join(debug_lines), ephemeral=True)
    else:
        await ctx.respond("No members or activities to display.", ephemeral=True)

#######################################
#          Run the Bot                #
#######################################

bot.run(BOT_TOKEN)
