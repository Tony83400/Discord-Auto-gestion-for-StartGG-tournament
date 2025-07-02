from dotenv import load_dotenv
import os
import discord
from functools import wraps
from discord.ext import commands
from discord import app_commands
from config_tournament_view import TournamentModal

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
                    "❌ Cette commande ne peut être utilisée que sur un serveur Discord (pas en DM).",
                    ephemeral=True
                )
                return

            member = interaction.user
            if not isinstance(member, discord.Member):
                member = await interaction.guild.fetch_member(interaction.user.id)

            role_names = [role.name for role in member.roles]
            if role_name not in role_names:
                await interaction.response.send_message(
                    f"❌ Tu dois avoir le rôle `{role_name}` pour utiliser cette commande.",
                    ephemeral=True
                )
                return

            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user.name} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synchronisé {len(synced)} commande(s) slash")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes: {e}")

    role_name = "Tournament Admin"

    for guild in bot.guilds:
        print(f"🔗 Connecté au serveur : {guild.name} ({guild.id})")

        # Vérification si le rôle existe déjà
        existing_role = discord.utils.get(guild.roles, name=role_name)

        if existing_role:
            print(f"✅ Le rôle '{role_name}' existe déjà sur : {guild.name}")
        else:
            try:
                await guild.create_role(
                    name=role_name,
                    colour=discord.Colour.blue(),
                    reason=f"Création automatique par le bot {bot.user.name}"
                )
                print(f"✅ Rôle '{role_name}' créé sur : {guild.name}")
            except discord.Forbidden:
                print(f"❌ Permissions insuffisantes pour créer le rôle sur : {guild.name}")
            except Exception as e:
                print(f"❌ Erreur lors de la création du rôle sur {guild.name} : {e}")

        # Vérification des permissions du bot sur chaque serveur
        try:
            me = guild.me  # Le bot lui-même dans ce serveur
            bot_permissions = me.guild_permissions

            if bot_permissions.manage_roles and bot_permissions.send_messages:
                print(f"✅ Le bot a les permissions nécessaires sur : {guild.name}")
            else:
                print(f"⚠️ Attention : Le bot pourrait ne pas avoir toutes les permissions nécessaires sur : {guild.name}")
        except Exception as e:
            print(f"❌ Erreur lors de la vérification des permissions sur {guild.name} : {e}")

@bot.tree.command(name="setup_tournament", description="Configure un tournoi pour la gestion automatique")
@has_role("Tournament Admin")
async def setup_tournament(interaction: discord.Interaction):
    global current_tournament_guild_id 

    current_tournament_guild_id = interaction.guild.id
    modal = TournamentModal(bot)
    await interaction.response.send_modal(modal)

@bot.tree.command(name="start_matches", description="Démarre la gestion automatique des matchs")
@has_role("Tournament Admin")
async def start_matches(interaction: discord.Interaction):
    if not bot.match_manager:
        await interaction.response.send_message("❌ Aucun tournoi configuré. Utilisez `/setup_tournament` d'abord.")
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            "❌ Le tournoi actuel est sur un autre serveur.",
            ephemeral=True
        )
        return
    await interaction.response.defer()
    await bot.match_manager.start_match_processing(interaction)

@bot.tree.command(name="stop_matches", description="Arrête la gestion automatique des matchs et nettoie tout")
@has_role("Tournament Admin")
async def stop_matches(interaction: discord.Interaction):
    
    if not bot.match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire actif.")
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            "❌ Le tournoi actuel est sur un autre serveur.",
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
                print(f"Permission refusée pour supprimer le channel {channel.name}.")
            except discord.HTTPException as e:
                print(f"Erreur lors de la suppression du channel {channel.name}: {e}")
    
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

    await interaction.followup.send("✅ **Arrêt complet terminé :**\n"
                    f"• Gestionnaire de matchs arrêté\n"
                    f"• {deleted_channels} channels supprimés\n"
                    f"• {num_stations} stations supprimées\n"
                    f"• Toutes les listes nettoyées")

@bot.tree.command(name="match_status", description="Affiche le statut du gestionnaire de matchs")
async def match_status(interaction: discord.Interaction):
    if not bot.match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            "❌ Le tournoi actuel est sur un autre serveur.",
            ephemeral=True
        )
        return
    await interaction.response.defer()
    await bot.match_manager.get_status(interaction)



@bot.tree.command(name="force_station_free", description="Force la libération d'une station (en cas de problème)")
@has_role("Tournament Admin")
@app_commands.describe(station_number="Numéro de la station à libérer")
async def force_station_free(interaction: discord.Interaction, station_number: int):
    if not bot.current_tournament:
        await interaction.response.send_message("❌ Aucun tournoi configuré.")
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            "❌ Le tournoi actuel est sur un autre serveur.",
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
        
        await interaction.followup.send(f"🔧 Station {station_number} forcée à être libre")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur: {e}")

@bot.tree.command(name="list_stations", description="Liste toutes les stations et leur statut")
async def list_stations(interaction: discord.Interaction):
    if not bot.current_tournament:
        await interaction.response.send_message("❌ Aucun tournoi configuré.")
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            "❌ Le tournoi actuel est sur un autre serveur.",
            ephemeral=True
        )
        return
    embed = discord.Embed(title="🎮 Statut des Stations", color=0x3498db)
    
    for station in bot.current_tournament.station:
        status = "🔴 Occupée" if station['isUsed'] else "🟢 Libre"
        match_info = ""
        
        if station['isUsed'] and 'current_match' in station:
            match = station['current_match']
            p1 = match['slots'][0]['entrant']['name']
            p2 = match['slots'][1]['entrant']['name']
            match_info = f"\n📋 {p1} vs {p2}"
        
        embed.add_field(
            name=f"Station {station['number']}",
            value=f"{status}{match_info}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Affiche le menu d'aide complet du bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🆘 Aide du Bot de Tournoi",
        description="**Commandes disponibles** :",
        color=0x3498db
    )

    # Section Configuration
    embed.add_field(
        name="⚙️ **CONFIGURATION**",
        value=(
            "`/setup_tournament` - Configurer un nouveau tournoi\n"
            "`/start_matches` - Démarrer la gestion automatique\n"
            "`/stop_matches` - Tout arrêter et nettoyer\n"
            "`/force_refresh` - Rechargement complet (en cas de bug)"
        ),
        inline=False
    )

    # Section Matchs en cours
    embed.add_field(
        name="⚔ **MATCHS EN COURS**",
        value=(
            "`/match_status` - Statut global du gestionnaire\n"
            "`/list_stations` - Liste des stations et leur état"
        ),
        inline=False
    )

    # Section Maintenance
    embed.add_field(
        name="🔧 **MAINTENANCE**",
        value=(
            "`/force_station_free [n°]` - Libérer une station bloquée\n"
        ),
        inline=False
    )

    # Footer avec conseil
    embed.set_footer(
        text="💡 Les commandes marquées nécessitent le rôle 'Tournament Admin'"
    )

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="force_refresh", description="[ADMIN] Force un rechargement COMPLET des matchs (en cas de problème)")
@has_role("Tournament Admin")
async def force_refresh(interaction: discord.Interaction):
    """Recharge intégralement la liste des matchs et nettoie les états"""
    if not bot.match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    global current_tournament_guild_id

    if current_tournament_guild_id != interaction.guild.id:
        await interaction.response.send_message(
            "❌ Le tournoi actuel est sur un autre serveur.",
            ephemeral=True
        )
        return
    await interaction.response.defer()
    
    # 1. Nettoyer les états existants
    bot.match_manager.pending_matches.clear()
    if hasattr(bot.match_manager, 'active_matches'):
        bot.match_manager.active_matches.clear()
    
    # 2. Rechargement complet depuis l'API
    try:
        matches = bot.tournament.get_matches(state=1)  # Matchs non commencés
        bot.match_manager.pending_matches = matches.copy()
        
        # 3. Réinitialiser les stations
        if bot.current_tournament:
            for station in bot.current_tournament.station:
                station['isUsed'] = False
                if 'current_match' in station:
                    del station['current_match']
        
        await interaction.followup.send(
            f"♻️ **Rechargement forcé réussi !**\n"
            f"• {len(matches)} matchs en attente\n"
            f"• Toutes stations réinitialisées\n"
            f"• États internes nettoyés"
        )
        
    except Exception as e:
        error_msg = f"❌ Échec du rechargement : {str(e)}"
        print(error_msg)
        await interaction.followup.send(error_msg)
bot.run(token)