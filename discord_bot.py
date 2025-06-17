from dotenv import load_dotenv
import os

from dotenv import load_dotenv
from startgg_request import StartGG
from match_manager import MatchManager

import asyncio
import traceback
load_dotenv()  # Charge le fichier .env

token = os.getenv('DISCORD_BOT_TOKEN')
sggKey = os.getenv('START_GG_KEY')
import discord
from discord.ext import commands
from match_report import send_match_report
from startgg_request import StartGG
from match import Match
from tournament import Tournament

# Variable globale pour le gestionnaire (à ajouter après les imports)
match_manager = None
current_tournament = None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user.name} ({bot.user.id})")
 # Trouve le serveur principal (si le bot est sur un seul serveur)
    guild = bot.guilds[0] if bot.guilds else None
    
    if guild:
        try:
 
            print(f"Bot prêt sur le serveur: {guild.name} ({guild.id})")
            
        except discord.Forbidden:
            print("Erreur: Le bot n'a pas les permissions nécessaires")
        except discord.HTTPException:
            print("Erreur lors de la création des salons")




# Nouvelles commandes à ajouter à ton bot

@bot.command()
async def setup_tournament(ctx, tournament_slug: str, event_id: int, phase_id: int, pool_id: int , best_of: int , setup_number : int):
    """Configure un tournoi pour la gestion automatique"""
    global match_manager, current_tournament
    
    try:
        await ctx.send(f"⚙️ Configuration du tournoi: {tournament_slug}")
        
        # Créer l'objet tournament
        tournament = Tournament(tournament_slug)
        tournament.select_event(event_id)
        tournament.select_event_phase(phase_id)
        tournament.select_pool(pool_id)
        tournament.set_best_of(best_of)
        tournament._set_player_list()  # Mettre à jour la liste des joueurs
        for i in range(setup_number):
            tournament.create_station(i + 1)  # Créer les stations
        # Créer le gestionnaire de matchs
        match_manager = MatchManager(bot, tournament)
        match_manager.player_list = tournament.DiscordIdForPlayer  # Mettre à jour la liste des joueurs dans le gestionnaire
        current_tournament = tournament
        
        # Afficher les infos
        stations_count = len([s for s in tournament.station if not s['isUsed']])
        await ctx.send(f"✅ Tournoi configuré!\n"
                      f"📊 Événement: {tournament.selectedEvent['name']}\n"
                      f"🎮 Stations disponibles: {stations_count}")
        
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la configuration: {e}")

@bot.command()
async def start_matches(ctx):
    """Démarre la gestion automatique des matchs"""
    global match_manager
    
    if not match_manager:
        await ctx.send("❌ Aucun tournoi configuré. Utilisez `!setup_tournament` d'abord.")
        return
    
    await match_manager.start_match_processing(ctx)

@bot.command()
async def stop_matches(ctx):
    """Arrête la gestion automatique des matchs"""
    global match_manager
    
    if not match_manager:
        await ctx.send("❌ Aucun gestionnaire actif.")
        return
    
    await match_manager.stop_match_processing(ctx)

@bot.command()
async def match_status(ctx):
    """Affiche le statut du gestionnaire de matchs"""
    global match_manager
    
    if not match_manager:
        await ctx.send("❌ Aucun gestionnaire configuré.")
        return
    
    await match_manager.get_status(ctx)

@bot.command()
async def refresh_matches(ctx):
    """Recharge la liste des matchs en attente"""
    global match_manager
    
    if not match_manager:
        await ctx.send("❌ Aucun gestionnaire configuré.")
        return
    
    if await match_manager.initialize_matches(ctx):
        await ctx.send("🔄 Liste des matchs rechargée!")

@bot.command()
async def force_station_free(ctx, station_number: int):
    """Force la libération d'une station (en cas de problème)"""
    global current_tournament, match_manager
    
    if not current_tournament:
        await ctx.send("❌ Aucun tournoi configuré.")
        return
    
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
            await match_manager.cleanup_completed_match(ctx, station_number)
        
        await ctx.send(f"🔧 Station {station_number} forcée à être libre")
        
    except Exception as e:
        await ctx.send(f"❌ Erreur: {e}")

@bot.command()
async def list_stations(ctx):
    """Liste toutes les stations et leur statut"""
    global current_tournament
    
    if not current_tournament:
        await ctx.send("❌ Aucun tournoi configuré.")
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
    
    await ctx.send(embed=embed)

@bot.command()
async def manual_assign(ctx, station_number: int):
    """Assigne manuellement le prochain match à une station spécifique"""
    global match_manager
    
    if not match_manager:
        await ctx.send("❌ Aucun gestionnaire configuré.")
        return
    
    if not match_manager.pending_matches:
        await ctx.send("❌ Aucun match en attente.")
        return
    
    # Vérifier que la station est libre
    station_free = False
    for station in match_manager.tournament.station:
        if station['number'] == station_number and not station['isUsed']:
            station_free = True
            break
    
    if not station_free:
        await ctx.send(f"❌ La station {station_number} n'est pas disponible.")
        return
    
    # Assigner le match
    next_match = match_manager.pending_matches.pop(0)
    await match_manager.assign_match_to_station(ctx, next_match, station_number)

# Commande d'aide pour expliquer l'utilisation
@bot.command()
async def help_tournament(ctx):
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
    "`!setup_tournament <slug> <event_id> <phase_id> <pool_id> <best_of> <setup_number>`\n"
    "Configure un nouveau tournoi\n\n"
    "`!start_matches`\nDémarre la gestion automatique des matchs\n\n"
    "`!stop_matches`\nArrête la gestion automatique\n\n"
    "`!refresh_matches`\nRecharge la liste des matchs\n\n"
    "`!match_status`\nAffiche l'état actuel"
    ),
    inline=False
    )

    # Section Gestion des Stations
    embed.add_field(
    name="🕹️ **Gestion des Stations**",
    value=(
    "`!list_stations`\nAffiche le statut de toutes les stations\n\n"
    "`!force_station_free <num>`\nLibère une station manuellement\n\n"
    "`!manual_assign <num>`\nAssigne un match à une station spécifique\n\n"
    "`!remove_all_stations`\nSupprime toutes les stations"
    ),
    inline=False
    )

    # Section Maintenance
    embed.add_field(
    name="🔧 **Maintenance**",
    value=(
    "`!clean_all_channels`\nNettoie tous les salons de match\n\n"
    "`!help`\nAffiche ce message d'aide"
    ),
    inline=False
    )

    # Pied de page avec des conseils
    embed.set_footer(
    text="Astuce: Utilisez !help_tournament pour un guide détaillé sur la gestion de tournoi"
    )

    await ctx.send(embed=embed)
@bot.command()
async def clean_all_channels(ctx):
    """Nettoie tous les messages du salon"""
   #Supprime tout les channel stations
    for channel in ctx.guild.channels:
        if channel.name.startswith("station-"):
            try:
                await channel.delete()
                ctx.send(f"Channel {channel.name} supprimé.")
            except discord.Forbidden:
                print(f"Permission refusée pour supprimer le channel {channel.name}.")
            except discord.HTTPException as e:
                print(f"Erreur lors de la suppression du channel {channel.name}: {e}")
    
    #Supprime la catégorie ⚔ Matchs en cours
    category = discord.utils.get(ctx.guild.categories, name="⚔ Matchs en cours")
    if category:
        try:
            await category.delete()
            ctx.send(f"Catégorie {category.name} supprimée.")
        except discord.Forbidden:
            print(f"Permission refusée pour supprimer la catégorie {category.name}.")
        except discord.HTTPException as e:
            print(f"Erreur lors de la suppression de la catégorie {category.name}: {e}")
@bot.command()
async def remove_all_stations(ctx):
    """Supprime toutes les stations du tournoi"""
    global current_tournament
    
    if not current_tournament:
        await ctx.send("❌ Aucun tournoi configuré.")
        return
    
    try:
        # Supprimer toutes les stations
        for i in range(len(current_tournament.station) - 1, -1, -1):
            station = current_tournament.station[i]
            if station['isUsed']:
                await ctx.send(f"❌ Station {station['number']} est en cours d'utilisation et ne peut pas être supprimée.")
                continue
            
            # Supprimer la station via l'API StartGG
            current_tournament.delete_station(i + 1)  # i + 1 car les stations sont numérotées à partir de 1
        await ctx.send("✅ Toutes les stations ont été supprimées.")
        current_tournament.station.clear()  # Vider la liste des stations
        if match_manager:
            match_manager.active_matches.clear()  # Vider les matchs actifs du gestionnaire
            await ctx.send("🔄 Matchs actifs du gestionnaire réinitialisés.")
        
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la suppression des stations: {e}")

bot.run(token)