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
from startgg_request import StartGG
from match import Match
from tournament import Tournament
from config_tournament_view import TournamentModal, TournamentView

load_dotenv()  # Charge le fichier .env

token = os.getenv('DISCORD_BOT_TOKEN')
sggKey = os.getenv('START_GG_KEY')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# AJOUTEZ ces attributs au bot pour éviter les variables globales
bot.match_manager = None
bot.current_tournament = None

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


@bot.tree.command(name="setup_tournament", description="Configure un tournoi pour la gestion automatique")
async def setup_tournament(interaction: discord.Interaction):
    """Configure un tournoi pour la gestion automatique"""
    modal = TournamentModal(bot)  # Passer le bot au modal
    await interaction.response.send_modal(modal)

@bot.tree.command(name="start_matches", description="Démarre la gestion automatique des matchs")
async def start_matches(interaction: discord.Interaction):
    """Démarre la gestion automatique des matchs"""
    
    if not bot.match_manager:  # Utiliser bot.match_manager au lieu de match_manager
        await interaction.response.send_message("❌ Aucun tournoi configuré. Utilisez `/setup_tournament` d'abord.")
        return
    
    await interaction.response.defer()
    await bot.match_manager.start_match_processing(interaction)

@bot.tree.command(name="stop_matches", description="Arrête la gestion automatique des matchs et nettoie tout")
async def stop_matches(interaction: discord.Interaction):
    """Arrête la gestion automatique des matchs et nettoie tout"""
    
    if not bot.match_manager:  # Utiliser bot.match_manager
        await interaction.response.send_message("❌ Aucun gestionnaire actif.")
        return
    
    await interaction.response.defer()
    
    # 1. Arrêter le gestionnaire de matchs
    await bot.match_manager.stop_match_processing(interaction)
    
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
    #Remove all stations from the tournament
    num_stations = 0
    for station in bot.current_tournament.station:
        bot.current_tournament.delete_station(station['number'])
        num_stations += 1
    # Nettoyer les listes
    bot.match_manager.reset_all_match()
    bot.current_tournament.station.clear()  # Vider la liste des stations
    bot.match_manager.active_matches.clear()  # Vider les matchs actifs du gestionnaire
    bot.match_manager.pending_matches.clear()  # Vider les matchs en attente

    await interaction.followup.send("✅ **Arrêt complet terminé :**\n"
                    f"• Gestionnaire de matchs arrêté\n"
                    f"• {deleted_channels} channels supprimés\n"
                    f"• {num_stations} stations supprimées\n"
                    f"• Toutes les listes nettoyées")

@bot.tree.command(name="match_status", description="Affiche le statut du gestionnaire de matchs")
async def match_status(interaction: discord.Interaction):
    """Affiche le statut du gestionnaire de matchs"""
    
    if not bot.match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    
    await interaction.response.defer()
    await bot.match_manager.get_status(interaction)

@bot.tree.command(name="refresh_matches", description="Recharge la liste des matchs en attente")
async def refresh_matches(interaction: discord.Interaction):
    """Recharge la liste des matchs en attente"""
    
    if not bot.match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    
    await interaction.response.defer()
    if await bot.match_manager.initialize_matches(interaction):
        await interaction.followup.send("🔄 Liste des matchs rechargée!")

@bot.tree.command(name="force_station_free", description="Force la libération d'une station (en cas de problème)")
@app_commands.describe(station_number="Numéro de la station à libérer")
async def force_station_free(interaction: discord.Interaction, station_number: int):
    """Force la libération d'une station (en cas de problème)"""
    
    if not bot.current_tournament:
        await interaction.response.send_message("❌ Aucun tournoi configuré.")
        return
    
    await interaction.response.defer()
    
    try:
        # Libérer la station dans le tournament
        for station in bot.current_tournament.station:
            if station['number'] == station_number:
                station['isUsed'] = False
                if 'current_match' in station:
                    del station['current_match']
                break
        
        # Nettoyer le match manager si nécessaire
        if bot.match_manager and station_number in bot.match_manager.active_matches:

            await bot.match_manager.cleanup_completed_match(interaction, station_number)
        
        await interaction.followup.send(f"🔧 Station {station_number} forcée à être libre")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur: {e}")

@bot.tree.command(name="list_stations", description="Liste toutes les stations et leur statut")
async def list_stations(interaction: discord.Interaction):
    """Liste toutes les stations et leur statut"""
    
    if not bot.current_tournament:
        await interaction.response.send_message("❌ Aucun tournoi configuré.")
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

@bot.tree.command(name="manual_assign", description="Assigne manuellement le prochain match à une station spécifique")
@app_commands.describe(station_number="Numéro de la station où assigner le match")
async def manual_assign(interaction: discord.Interaction, station_number: int):
    """Assigne manuellement le prochain match à une station spécifique"""
    
    if not bot.match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    
    if not bot.match_manager.pending_matches:
        await interaction.response.send_message("❌ Aucun match en attente.")
        return
    
    # Vérifier que la station est libre
    station_free = False
    for station in bot.match_manager.tournament.station:
        if station['number'] == station_number and not station['isUsed']:
            station_free = True
            break
    
    if not station_free:
        await interaction.response.send_message(f"❌ La station {station_number} n'est pas disponible.")
        return
    
    await interaction.response.defer()
    
    # Assigner le match
    next_match = bot.match_manager.pending_matches.pop(0)
    await bot.match_manager.assign_match_to_station(interaction, next_match, station_number)

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

@bot.tree.command(name="remove_all_stations", description="Supprime toutes les stations du tournoi") #Bit
async def remove_all_stations(interaction: discord.Interaction):
    """Supprime toutes les stations du tournoi"""
    
    if not bot.current_tournament:
        await interaction.response.send_message("❌ Aucun tournoi configuré.")
        return
    
    await interaction.response.defer()
    
    try:
        stations_in_use = []
        stations_removed = 0
        
        # Supprimer toutes les stations
        for s in bot.current_tournament.station:
            # Supprimer la station via l'API StartGG
            bot.current_tournament.delete_station(s['number'])
            stations_removed += 1
        
        if stations_removed > 0:
            await interaction.followup.send(f"✅ {stations_removed} stations ont été supprimées.")
        
        # Nettoyer les listes si toutes les stations ont été supprimées
        if not stations_in_use:
            bot.current_tournament.station.clear()  # Vider la liste des stations
            if bot.match_manager:
                bot.match_manager.active_matches.clear()  # Vider les matchs actifs du gestionnaire
                await interaction.followup.send("🔄 Matchs actifs du gestionnaire réinitialisés.")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors de la suppression des stations: {e}")
        
@bot.tree.command(name="force_refresh", description="Force l'actualisation de la liste des matchs")
async def force_refresh(interaction: discord.Interaction):
    """Force l'actualisation de la liste des matchs"""
    
    if not bot.match_manager:
        await interaction.response.send_message("❌ Aucun gestionnaire configuré.")
        return
    
    await interaction.response.defer()
    new_matches = await bot.match_manager.refresh_matches_list(interaction)
    await interaction.followup.send(f"🔄 Actualisation forcée terminée! {new_matches} nouveaux matchs ajoutés.")
    
# Remplacez votre ancienne commande setup_tournament par celle-ci :
@bot.tree.command(name="setup_tournament_test", description="Configurer un tournoi pour le test via une interface modale")
async def setup_tournament_test(interaction: discord.Interaction):
    """Configurer un tournoi via une interface modale"""
    

bot.run(token)