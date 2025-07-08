
from dotenv import load_dotenv
import os
import discord
from functools import wraps
from discord.ext import commands
from discord import app_commands
from view.tournament_link import TournamentModal
from models.lang import translate


load_dotenv()  # Charge le fichier .env

token = os.getenv('DISCORD_BOT_TOKEN')
sggKey = os.getenv('START_GG_KEY')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# AJOUTEZ ces attributs au bot pour éviter les variables globales
bot.match_manager = None
bot.current_tournament = None
current_tournament_guild_id = None


def has_role(role_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):

            if not interaction.guild:
                await interaction.response.send_message(
                    translate("dm_not_allowed"),
                    ephemeral=True
                )
                return

            member = interaction.user
            if not isinstance(member, discord.Member):
                member = await interaction.guild.fetch_member(interaction.user.id)

            role_names = [role.name for role in member.roles]

            if role_name not in role_names:
                await interaction.response.send_message(
                    translate("missing_role", role=role_name),
                    ephemeral=True
                )
                return

            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

@bot.event
async def on_ready():
    print(translate("bot_connected", name=bot.user.name))

    # Sync commands
    try:
        synced = await bot.tree.sync()
        print(translate("commands_synced", count=len(synced)))
    except Exception as e:
        print(translate("sync_failed", error=e))

    # Vérification admin pour chaque serveur
    for guild in bot.guilds:
        print("\n" + translate("server_info", name=guild.name))
        me = guild.me

        if me.guild_permissions.administrator:
            print(translate("bot_admin"))
        else:
            print(translate("bot_not_admin"))
        role_name = "Tournament Admin"
        try:
            role = discord.utils.get(guild.roles, name=role_name) or \
                   await guild.create_role(
                       name=role_name,
                       color=discord.Color.blue(),
                       reason="Auto-created by bot"
                   )
            print(translate("role_configured", role=role_name))
        except discord.Forbidden:
            print(translate("role_permission_error"))
        except Exception as e:
            print(translate("role_error", error=e))
    print("\n" + translate("bot_ready"))

@bot.tree.command(name="setup_tournament", description=translate("setup_tournament_description"))
@has_role("Tournament Admin")
async def setup_tournament(interaction: discord.Interaction):
    global current_tournament_guild_id 

    current_tournament_guild_id = interaction.guild.id
    modal = TournamentModal(bot)
    await interaction.response.send_modal(modal)

@bot.tree.command(name="start_matches", description=translate("start_matches_description"))
@has_role("Tournament Admin")
async def start_matches(interaction: discord.Interaction):
    if not bot.match_manager:
        await interaction.response.send_message(translate("no_tournament") + " Utilisez `/setup_tournament` d'abord.")
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            translate("wrong_guild"),
            ephemeral=True
        )
        return
    await interaction.response.defer()
    await bot.match_manager.start_match_processing(interaction)

@bot.tree.command(name="stop_matches", description=translate("stop_matches_description"))
@has_role("Tournament Admin")
async def stop_matches(interaction: discord.Interaction):
    
    if not bot.match_manager:
        await interaction.response.send_message(translate("no_manager"))
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            translate("wrong_guild"),
            ephemeral=True
        )
        return
    await interaction.response.defer()
    await bot.match_manager.stop_match_processing(interaction)
    
    deleted_channels = 0
    for channel in interaction.guild.channels:
        if channel.name.startswith("station-"):
            try:
                await channel.delete()
                deleted_channels += 1
            except discord.Forbidden:
                print(translate("delete_permission_denied", name=channel.name))
            except discord.HTTPException as e:
                print(translate("delete_channel_error", name=channel.name, error=e))
    
    category = discord.utils.get(interaction.guild.categories, name="⚔ Matchs en cours")
    if category:
        try:
            await category.delete()
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
    
    num_stations = 0
    if bot.current_tournament:
        for station in bot.current_tournament.station:
            station['isUsed'] = False
            bot.current_tournament.sgg_request.delete_station(station['id'])
            num_stations += 1
    
    bot.match_manager.reset_all_match()
    if bot.current_tournament:
        bot.current_tournament.station.clear()
    bot.match_manager.active_matches.clear()
    bot.match_manager.pending_matches.clear()

    await interaction.followup.send(
        translate(
            "full_stop_done",
            channels=deleted_channels,
            stations=num_stations
        )
    )

@bot.tree.command(name="match_status", description=translate("match_status_description"))
async def match_status(interaction: discord.Interaction):
    if not bot.match_manager:
        await interaction.response.send_message(translate("no_manager"))
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            translate("wrong_guild"),
            ephemeral=True
        )
        return
    await interaction.response.defer()
    await bot.match_manager.get_status(interaction)



@bot.tree.command(name="force_station_free", description=translate("force_station_free_description"))
@has_role("Tournament Admin")
@app_commands.describe(station_number="Numéro de la station à libérer")
async def force_station_free(interaction: discord.Interaction, station_number: int):
    if not bot.current_tournament:
        await interaction.response.send_message(translate("no_tournament"))
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            translate("wrong_guild"),
            ephemeral=True
        )
        return
    await interaction.response.defer()
    
    try:
        for station in bot.current_tournament.station:
            if station['number'] == station_number:
                station['isUsed'] = False
                if 'current_match' in station:
                    del station['current_match']
                break
        
        if bot.match_manager and station_number in bot.match_manager.active_matches:
            await bot.match_manager.cleanup_completed_match(interaction, station_number)
        
        await interaction.followup.send(translate("station_freed", number=station_number))

    except Exception as e:
        await interaction.followup.send(translate("station_free_error", error=e))

@bot.tree.command(name="list_stations", description=translate("stations_description"))
async def list_stations(interaction: discord.Interaction):
    if not bot.current_tournament:
        await interaction.response.send_message(translate("no_tournament"))
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            translate("wrong_guild"),
            ephemeral=True
        )
        return
    embed = discord.Embed(title=translate("stations_title"), color=0x3498db)

    for station in bot.current_tournament.station:
        status = translate("station_used") if station['isUsed'] else translate("station_free")
        match_info = ""

        if station['isUsed'] and 'current_match' in station:
            match = station['current_match']
            p1 = match['slots'][0]['entrant']['name']
            p2 = match['slots'][1]['entrant']['name']
            match_info = "\n" + translate("match_info", p1=p1, p2=p2)

        embed.add_field(
            name=f"Station {station['number']}",
            value=f"{status}{match_info}",
            inline=True
        )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description=translate("help_description"))
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title=translate("help_title"),
        description=translate("help_description"),
        color=0x3498db
    )

    # Section Configuration
    embed.add_field(
        name="⚙️ **CONFIGURATION**",
        value=translate("help_config"),
        inline=False
    )

    # Section Matchs en cours
    embed.add_field(
        name="⚔ **MATCHS EN COURS**",
        value=translate("help_matches"),
        inline=False
    )

    # Section Maintenance
    embed.add_field(
        name="🔧 **MAINTENANCE**",
        value=translate("help_maintenance"),
        inline=False
    )

    # Footer avec conseil
    embed.set_footer(
        text=translate("help_footer")
    )

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="force_refresh", description=translate("force_refresh_description"))
@has_role("Tournament Admin")
async def force_refresh(interaction: discord.Interaction):
    await interaction.response.defer()  # Important pour éviter l'expiration trop rapide
    await bot.match_manager.refresh_matches_list(interaction)
    await interaction.followup.send(translate("refresh_done"))
bot.run(token)