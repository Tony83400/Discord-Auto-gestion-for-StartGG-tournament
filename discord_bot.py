from time import sleep
from dotenv import load_dotenv
import os

from dotenv import load_dotenv
from startgg_request import StartGG
from match_manager import MatchManager

import asyncio
import traceback
import discord
from discord.ext import commands
from discord import app_commands
from match_report import send_match_report
from startgg_request import StartGG
from match import Match
from tournament import Tournament

load_dotenv()  # Charge le fichier .env

token = os.getenv('DISCORD_BOT_TOKEN')
sggKey = os.getenv('START_GG_KEY')

# Variable globale pour le gestionnaire (à ajouter après les imports)
match_manager = None
current_tournament = None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user.name} ({bot.user.id})")
    
    # Synchroniser les commandes slash
    try:
        synced = await bot.tree.sync()
        print(f"Synchronisé {len(synced)} commande(s) slash")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes: {e}")
    
    # Trouve le serveur principal (si le bot est sur un seul serveur)
    guild = bot.guilds[0] if bot.guilds else None
    
    if guild:
        try:
            print(f"Bot prêt sur le serveur: {guild.name} ({guild.id})")
        except discord.Forbidden:
            print("Erreur: Le bot n'a pas les permissions nécessaires")
        except discord.HTTPException:
            print("Erreur lors de la création des salons")

# Conversion des commandes en slash commands

@bot.tree.command(name="setup_tournament", description="Configure un tournoi pour la gestion automatique")
@app_commands.describe(
    tournament_slug="Slug du tournoi (ex: tournament-name-1)",
    event_id="ID de l'événement",
    phase_id="ID de la phase",
    pool_id="ID de la pool",
    best_of="Format du match (ex: 3 pour BO3)",
    setup_number="Nombre de stations à créer"
)
async def setup_tournament(interaction: discord.Interaction, tournament_slug: str, event_id: int, phase_id: int, pool_id: int, best_of: int, setup_number: int):
    """Configure un tournoi pour la gestion automatique"""
    global match_manager, current_tournament
    
    await interaction.response.defer()
    
    try:
        await interaction.followup.send(f"⚙️ Configuration du tournoi: {tournament_slug}")
        
        # Créer l'objet tournament
        tournament = Tournament(tournament_slug)
        tournament.select_event(event_id)
        tournament.select_event_phase(phase_id)
        tournament.select_pool(pool_id)
        tournament.set_best_of(best_of)
        tournament._set_player_list()  # Mettre à jour la liste des joueurs
        for i in range(setup_number):
            tournament.create_station(i + 1)  # Créer les stations
            print(f"Station {i + 1} créée avec succès")

        # Créer le gestionnaire de matchs
        match_manager = MatchManager(bot, tournament)
        match_manager.player_list = tournament.DiscordIdForPlayer  # Mettre à jour la liste des joueurs dans le gestionnaire
        current_tournament = tournament
        
        # Afficher les infos
        stations_count = len([s for s in tournament.station if not s['isUsed']])
        await interaction.followup.send(f"✅ Tournoi configuré!\n"
                      f"📊 Événement: {tournament.selectedEvent['name']}\n"
                      f"🎮 Stations disponibles: {stations_count}")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors de la configuration: {e}")

@bot.tree.command(name="start_matches", description="Démarre la gestion automatique des matchs")
async def start_matches(interaction: discord.Interaction):
    """Démarre la gestion automatique des matchs"""
    global match_manager
    
    if not match_manager:
        await interaction.response.send_message("❌ Aucun tournoi configuré. Utilisez `/setup_tournament` d'abord.")
        return
    
    await interaction.response.defer()
    await match_manager.start_match_processing(interaction)

@bot.tree.command(name="stop_matches", description="Arrête la gestion automatique des matchs et nettoie tout")
async def stop_matches(interaction: discord.Interaction):
    """Arrête la gestion automatique des matchs et nettoie tout"""
    global match_manager, current_tournament
    
    if not match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire actif.")
        return
    
    await interaction.response.defer()
    
    # 1. Arrêter le gestionnaire de matchs
    await match_manager.stop_match_processing(interaction)
    
    # 2. Nettoyer tous les channels
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
    
    # Supprimer la catégorie ⚔ Matchs en cours
    category = discord.utils.get(interaction.guild.categories, name="⚔ Matchs en cours")
    if category:
        try:
            await category.delete()
            await interaction.followup.send(f"🧹 {deleted_channels} channels supprimés et catégorie nettoyée.")
        except discord.Forbidden:
            await interaction.followup.send(f"🧹 {deleted_channels} channels supprimés. Permission refusée pour supprimer la catégorie.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"🧹 {deleted_channels} channels supprimés. Erreur lors de la suppression de la catégorie: {e}")
    else:
        if deleted_channels > 0:
            await interaction.followup.send(f"🧹 {deleted_channels} channels supprimés.")
    match_manager.reset_all_match()

    # 3. Supprimer toutes les stations
    if current_tournament:
        try:
            stations_in_use = []
            stations_removed = 0
            
            # Supprimer toutes les stations
            for i in range(len(current_tournament.station) - 1, -1, -1):
                station = current_tournament.station[i]
                # Forcer la suppression même si en cours d'utilisation
                try:
                    station['isUsed'] = False
                    current_tournament.delete_station(i + 1)  # i + 1 car les stations sont numérotées à partir de 1
                    stations_removed += 1
                except Exception as e:
                    print(f"Erreur lors de la suppression de la station {i + 1}: {e}")
            
            if stations_removed > 0:
                await interaction.followup.send(f"🗑️ {stations_removed} stations ont été supprimées.")
            
            # Nettoyer les listes
            match_manager.reset_all_match()
            current_tournament.station.clear()  # Vider la liste des stations
            match_manager.active_matches.clear()  # Vider les matchs actifs du gestionnaire
            match_manager.pending_matches.clear()  # Vider les matchs en attente
            
            await interaction.followup.send("✅ **Arrêt complet terminé :**\n"
                          f"• Gestionnaire de matchs arrêté\n"
                          f"• {deleted_channels} channels supprimés\n"
                          f"• {stations_removed} stations supprimées\n"
                          f"• Toutes les listes nettoyées")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de la suppression des stations: {e}")
    else:
        await interaction.followup.send("✅ **Arrêt terminé :**\n"
                      f"• Gestionnaire de matchs arrêté\n"
                      f"• {deleted_channels} channels supprimés\n"
                      f"• Aucune station à supprimer")


@bot.tree.command(name="match_status", description="Affiche le statut du gestionnaire de matchs")
async def match_status(interaction: discord.Interaction):
    """Affiche le statut du gestionnaire de matchs"""
    global match_manager
    
    if not match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    
    await interaction.response.defer()
    await match_manager.get_status(interaction)

@bot.tree.command(name="refresh_matches", description="Recharge la liste des matchs en attente")
async def refresh_matches(interaction: discord.Interaction):
    """Recharge la liste des matchs en attente"""
    global match_manager
    
    if not match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    
    await interaction.response.defer()
    if await match_manager.initialize_matches(interaction):
        await interaction.followup.send("🔄 Liste des matchs rechargée!")

@bot.tree.command(name="force_station_free", description="Force la libération d'une station (en cas de problème)")
@app_commands.describe(station_number="Numéro de la station à libérer")
async def force_station_free(interaction: discord.Interaction, station_number: int):
    """Force la libération d'une station (en cas de problème)"""
    global current_tournament, match_manager
    
    if not current_tournament:
        await interaction.response.send_message("❌ Aucun tournoi configuré.")
        return
    
    await interaction.response.defer()
    
    try:
        # Libérer la station dans le tournament
        for station in current_tournament.station:
            if station['number'] == station_number:
                station['isUsed'] = False
                if 'current_match' in station:
                    del station['current_match']
                break
        
        # Nettoyer le match manager si nécessaire
        if match_manager and station_number in match_manager.active_matches:

            await match_manager.cleanup_completed_match(interaction, station_number)
        
        await interaction.followup.send(f"🔧 Station {station_number} forcée à être libre")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur: {e}")

@bot.tree.command(name="list_stations", description="Liste toutes les stations et leur statut")
async def list_stations(interaction: discord.Interaction):
    """Liste toutes les stations et leur statut"""
    global current_tournament
    
    if not current_tournament:
        await interaction.response.send_message("❌ Aucun tournoi configuré.")
        return
    
    embed = discord.Embed(title="🎮 Statut des Stations", color=0x3498db)
    
    for station in current_tournament.station:
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

@bot.tree.command(name="manual_assign", description="Assigne manuellement le prochain match à une station spécifique")
@app_commands.describe(station_number="Numéro de la station où assigner le match")
async def manual_assign(interaction: discord.Interaction, station_number: int):
    """Assigne manuellement le prochain match à une station spécifique"""
    global match_manager
    
    if not match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    
    if not match_manager.pending_matches:
        await interaction.response.send_message("❌ Aucun match en attente.")
        return
    
    # Vérifier que la station est libre
    station_free = False
    for station in match_manager.tournament.station:
        if station['number'] == station_number and not station['isUsed']:
            station_free = True
            break
    
    if not station_free:
        await interaction.response.send_message(f"❌ La station {station_number} n'est pas disponible.")
        return
    
    await interaction.response.defer()
    
    # Assigner le match
    next_match = match_manager.pending_matches.pop(0)
    await match_manager.assign_match_to_station(interaction, next_match, station_number)

@bot.tree.command(name="help_tournament", description="Affiche le menu d'aide complet du bot")
async def help_tournament(interaction: discord.Interaction):
    """Affiche le menu d'aide complet du bot"""
    embed = discord.Embed(
        title="🆘 Aide du Bot de Tournoi",
        description="Liste complète des commandes disponibles",
        color=0x3498db
    )

    # Section Gestion de Tournoi
    embed.add_field(
        name="🎯 **Gestion de Tournoi**",
        value=(
            "`/setup_tournament` - Configure un nouveau tournoi\n"
            "`/start_matches` - Démarre la gestion automatique des matchs\n"
            "`/stop_matches` - Arrête la gestion automatique\n"
            "`/refresh_matches` - Recharge la liste des matchs\n"
            "`/match_status` - Affiche l'état actuel"
        ),
        inline=False
    )

    # Section Gestion des Stations
    embed.add_field(
        name="🕹️ **Gestion des Stations**",
        value=(
            "`/list_stations` - Affiche le statut de toutes les stations\n"
            "`/force_station_free` - Libère une station manuellement\n"
            "`/manual_assign` - Assigne un match à une station spécifique\n"
            "`/remove_all_stations` - Supprime toutes les stations"
        ),
        inline=False
    )

    # Section Maintenance
    embed.add_field(
        name="🔧 **Maintenance**",
        value=(
            "`/clean_all_channels` - Nettoie tous les salons de match\n"
            "`/help_tournament` - Affiche ce message d'aide"
        ),
        inline=False
    )

    # Pied de page avec des conseils
    embed.set_footer(
        text="Astuce: Les commandes slash offrent une meilleure intégration avec Discord"
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clean_all_channels", description="Nettoie tous les salons de match")
async def clean_all_channels(interaction: discord.Interaction):
    """Nettoie tous les messages du salon"""
    await interaction.response.defer()
    
    # Supprime tous les channels stations
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
    
    # Supprime la catégorie ⚔ Matchs en cours
    category = discord.utils.get(interaction.guild.categories, name="⚔ Matchs en cours")
    if category:
        try:
            await category.delete()
            await interaction.followup.send(f"✅ {deleted_channels} channels supprimés et catégorie nettoyée.")
        except discord.Forbidden:
            await interaction.followup.send(f"✅ {deleted_channels} channels supprimés. Permission refusée pour supprimer la catégorie.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"✅ {deleted_channels} channels supprimés. Erreur lors de la suppression de la catégorie: {e}")
    else:
        await interaction.followup.send(f"✅ {deleted_channels} channels supprimés.")

@bot.tree.command(name="remove_all_stations", description="Supprime toutes les stations du tournoi")
async def remove_all_stations(interaction: discord.Interaction):
    """Supprime toutes les stations du tournoi"""
    global current_tournament, match_manager
    
    if not current_tournament:
        await interaction.response.send_message("❌ Aucun tournoi configuré.")
        return
    
    await interaction.response.defer()
    
    try:
        stations_in_use = []
        stations_removed = 0
        
        # Supprimer toutes les stations
        for i in range(len(current_tournament.station) - 1, -1, -1):
            station = current_tournament.station[i]
            if station['isUsed']:
                stations_in_use.append(station['number'])
                continue
            
            # Supprimer la station via l'API StartGG
            current_tournament.delete_station(i + 1)  # i + 1 car les stations sont numérotées à partir de 1
            stations_removed += 1
        
        # Messages de résultat
        if stations_in_use:
            await interaction.followup.send(f"⚠️ Stations {', '.join(map(str, stations_in_use))} en cours d'utilisation et ne peuvent pas être supprimées.")
        
        if stations_removed > 0:
            await interaction.followup.send(f"✅ {stations_removed} stations ont été supprimées.")
        
        # Nettoyer les listes si toutes les stations ont été supprimées
        if not stations_in_use:
            current_tournament.station.clear()  # Vider la liste des stations
            if match_manager:
                match_manager.active_matches.clear()  # Vider les matchs actifs du gestionnaire
                await interaction.followup.send("🔄 Matchs actifs du gestionnaire réinitialisés.")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors de la suppression des stations: {e}")
@bot.tree.command(name="force_refresh", description="Force l'actualisation de la liste des matchs")
async def force_refresh(interaction: discord.Interaction):
    """Force l'actualisation de la liste des matchs"""
    global match_manager
    
    if not match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    
    await interaction.response.defer()
    new_matches = await match_manager.refresh_matches_list(interaction)
    await interaction.followup.send(f"🔄 Actualisation forcée terminée! {new_matches} nouveaux matchs ajoutés.")

bot.run(token)