from dotenv import load_dotenv
import os

load_dotenv()  # Charge le fichier .env

token = os.getenv('DISCORD_BOT_TOKEN')

import discord
from discord.ext import commands
from match_report import send_match_report

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

            print("Salons créés avec succès!")
            
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
async def create_match(ctx, player1: str ="J1", player2: str = "J2"):
    characters_list = ["Ryu", "Ken", "Chun-Li", "Zangief", "Cammy", "Blanka", "Guile", "Dhalsim", "M. Bison", "Akuma", "Sagat", "Vega", "Balrog", "E. Honda", "Ibuki", "Elena", "Juri", "Karin", "Laura", "Birdie", "F.A.N.G", "Rashid", "Necalli", "Zeku", "Ed", "Sakura", "Kage", "Lucia", "Poison", "Gill"]

    # Utilisez ctx.channel pour envoyer dans le salon actuel
    result = await send_match_report(
        channel=ctx.channel,  # Envoie dans le salon où la commande a été tapée
        player1=player1,      # Utilise le nom fourni en paramètre
        player2=player2,      # Utilise le nom fourni en paramètre
        characters=characters_list
    )
    
bot.run(token)