from dotenv import load_dotenv
import os

from dotenv import load_dotenv
from startgg_request import StartGG

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
# from tournament import Tournament

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
            # Catégorie pour les matchs
            # matches_category = await guild.create_category("⚔ Matchs en cours")
            # await guild.create_text_channel(f"match-A", category=matches_category)
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
bot.run(token)