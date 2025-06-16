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





@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def remove_match(ctx, match_number: str = "a"):
    guild = ctx.guild
    channel_name = f"match-{match_number}"
    
    # Trouve le salon à supprimer
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    
    if channel:
        try:
            await channel.delete()
            await ctx.send(f"Salon {channel_name} supprimé avec succès.")
        except discord.Forbidden:
            await ctx.send("Erreur: Le bot n'a pas les permissions nécessaires pour supprimer ce salon.")
        except discord.HTTPException:
            await ctx.send("Erreur lors de la suppression du salon.")
    else:
        await ctx.send(f"Aucun salon trouvé avec le nom {channel_name}.")


@bot.command()
async def test(ctx):
    p1 = {'id': 1, 'name': 'Player1', 'discordId': '1234567890', 'discordName': 'PlayerOne'}
    p2 = {'id': 2, 'name': 'Player2', 'discordId': '0987654321', 'discordName': 'PlayerTwo'}
    myMatch = Match(p1, p2, 90324698, 3, StartGG(sggKey))
    myMatch.set_characters([
        {'id': 1271, 'name': 'Character1'},
        {'id': 1277, 'name': 'Character2'},
    ])
    
    myMatch.set_station(1)
    myMatch.start_match()
    await start_match(ctx, myMatch)

    


async def start_match(ctx , myMatch: Match):
    """Commande pour gérer un match complet avec attente des reports"""
    # Initialisation
    p1 = myMatch.p1
    p2 = myMatch.p2
    
    await ctx.send(f"**Match démarré** - {p1['name']} vs {p2['name']} (BO3)")

    # Boucle des games
    for game_num in range(1, myMatch.bestOf_N + 1):
        # 1. Envoi et attente du report
        await ctx.send(f"**Game {game_num}** - En attente du report...")
        
        try:
            # Cette ligne attendra que les joueurs aient tout complété
            result = await send_match_report(
                channel=ctx.channel,
                player1=p1['name'],
                player2=p2['name'],
                characters= myMatch.charactersName  # Votre liste
            )
            
            # 2. Traitement du résultat
            print(f"Résultat reçu pour Game {game_num}: {result}")
            if result["isP1Winner"]:
                myMatch.report_Match(True, result['p1_char'], result['p2_char'])
                await ctx.send(f"✅ Game {game_num} reportée: {p1['name']} gagne")
            else:
                myMatch.report_Match(False, result['p1_char'], result['p2_char'])
                await ctx.send(f"✅ Game {game_num} reportée: {p2['name']} gagne")
            
            # 3. Vérification si le match est terminé
            if myMatch.isComplete:  # À implémenter dans votre classe Match
                await ctx.send("**Match terminé !**")
                break
                
        except asyncio.TimeoutError:
            await ctx.send("⌛ Temps écoulé - Match annulé")
            return

    await ctx.send("**Processus terminé**")
    return myMatch

# Variable globale pour le gestionnaire (à ajouter après les imports)
match_manager = None
current_tournament = None

# Nouvelles commandes à ajouter à ton bot

@bot.command()
async def setup_tournament(ctx, tournament_slug: str, event_id: int, phase_id: int, pool_id: int , best_of: int = 3):
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
        
        # Créer le gestionnaire de matchs
        match_manager = MatchManager(bot, tournament)
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
    """Affiche l'aide pour la gestion des tournois"""
    embed = discord.Embed(title="🎯 Guide de Gestion des Tournois", color=0x00ff00)
    
    embed.add_field(
        name="1️⃣ Configuration",
        value="`!setup_tournament <slug> <event_id> <phase_id> <pool_id>`\n"
              "Configure le tournoi avec les IDs nécessaires",
        inline=False
    )
    
    embed.add_field(
        name="2️⃣ Démarrage",
        value="`!start_matches`\nDémarre la gestion automatique",
        inline=False
    )
    
    embed.add_field(
        name="3️⃣ Contrôle",
        value="`!match_status` - Voir le statut\n"
              "`!stop_matches` - Arrêter la gestion\n"
              "`!refresh_matches` - Recharger les matchs",
        inline=False
    )
    
    embed.add_field(
        name="4️⃣ Gestion des stations",
        value="`!list_stations` - Voir toutes les stations\n"
              "`!force_station_free <num>` - Libérer une station\n"
              "`!manual_assign <num>` - Assigner manuellement",
        inline=False
    )
    
    await ctx.send(embed=embed)
@bot.command()
async def force_refresh(ctx):
    """Force le rafraîchissement des matchs en attente"""
    global match_manager
    
    if not match_manager:
        await ctx.send("❌ Aucun gestionnaire configuré.")
        return
    
    if await match_manager.refresh_pending_matches(ctx):
        await ctx.send("🔄 Nouveaux matchs récupérés!")
    else:
        await ctx.send("ℹ️ Aucun nouveau match trouvé")

bot.run(token)