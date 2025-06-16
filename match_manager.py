import asyncio
from typing import Dict, List, Optional
import discord
from discord.ext import commands
from match import Match
from tournament import Tournament, sggMatch_to_MyMatch

class MatchManager:
    def __init__(self, bot: commands.Bot, tournament: Tournament):
        self.bot = bot
        self.tournament = tournament
        self.active_matches: Dict[int, Dict] = {}  # station_number -> match_info
        self.pending_matches: List[Dict] = []  # Liste des matchs en attente
        self.is_running = False
        self.last_refresh_time = 0  # Pour éviter trop de requêtes API
        
    async def initialize_matches(self, ctx):
        """Initialise la liste des matchs en attente"""
        try:
            matches = self.tournament.get_matches(state=1)  # Matchs non commencés
            self.pending_matches = matches.copy()
            await ctx.send(f"🎯 {len(self.pending_matches)} matchs en attente de traitement")
            return True
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la récupération des matchs: {e}")
            return False
    
    async def refresh_pending_matches(self, ctx=None):
        """Rafraîchit la liste des matchs en attente depuis start.gg"""
        try:
            import time
            current_time = time.time()
            
            # Éviter de spam l'API (minimum 30 secondes entre les refresh)
            if current_time - self.last_refresh_time < 30:
                return False
                
            self.last_refresh_time = current_time
            
            # Récupérer les nouveaux matchs depuis start.gg
            new_matches = self.tournament.get_matches(state=1)  # Matchs non commencés
            
            # Filtrer les matchs déjà en cours
            active_match_ids = set()
            for match_info in self.active_matches.values():
                active_match_ids.add(match_info['sgg_match']['id'])
            
            # Filtrer les matchs déjà en attente
            pending_match_ids = {match['id'] for match in self.pending_matches}
            
            # Ajouter seulement les nouveaux matchs
            new_count = 0
            for match in new_matches:
                if match['id'] not in active_match_ids and match['id'] not in pending_match_ids:
                    self.pending_matches.append(match)
                    new_count += 1
            
            if ctx and new_count > 0:
                await ctx.send(f"🔄 {new_count} nouveaux matchs détectés!")
                
            return new_count > 0
            
        except Exception as e:
            if ctx:
                await ctx.send(f"❌ Erreur lors du rafraîchissement: {e}")
            print(f"Erreur refresh: {e}")
            return False
    
    async def start_match_processing(self, ctx):
        """Démarre le processus automatique de gestion des matchs"""
        if self.is_running:
            await ctx.send("⚠️ Le gestionnaire de matchs est déjà en cours d'exécution")
            return
            
        if not self.pending_matches:
            if not await self.initialize_matches(ctx):
                return
        
        self.is_running = True
        await ctx.send("🚀 Démarrage du gestionnaire automatique de matchs")
        
        # Lancer la boucle principale
        asyncio.create_task(self.match_processing_loop(ctx))
    
    async def stop_match_processing(self, ctx):
        """Arrête le processus automatique"""
        self.is_running = False
        await ctx.send("⏹️ Arrêt du gestionnaire de matchs demandé")
    
    async def match_processing_loop(self, ctx):
        """Boucle principale qui gère l'attribution automatique des matchs"""
        refresh_counter = 0
        
        while self.is_running:
            try:
                # Vérifier les matchs terminés AVANT d'assigner de nouveaux matchs
                await self.check_completed_matches(ctx)
                
                # Rafraîchir la liste des matchs périodiquement
                refresh_counter += 1
                if refresh_counter >= 6:  # Toutes les 30 secondes (6 x 5s)
                    await self.refresh_pending_matches(ctx)
                    refresh_counter = 0
                
                # Assigner de nouveaux matchs aux stations libres
                await self.assign_pending_matches(ctx)
                
                # Vérifier s'il reste des matchs à traiter
                if not self.pending_matches and not self.active_matches:
                    # Dernier check pour voir s'il y a de nouveaux matchs
                    if not await self.refresh_pending_matches(ctx):
                        break
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Erreur dans la boucle de traitement: {e}")
                await asyncio.sleep(10)
        
        self.is_running = False
        await ctx.send("✅ Tous les matchs ont été traités!")
    
    async def assign_pending_matches(self, ctx):
        """Assigne les matchs en attente aux stations libres"""
        if not self.pending_matches:
            return
            
        try:
            # Trouver les stations disponibles
            available_stations = []
            for station in self.tournament.station:
                if not station['isUsed'] and station['number'] not in self.active_matches:
                    available_stations.append(station['number'])
            
            # Assigner un match par station disponible
            assigned_count = 0
            for station_num in available_stations:
                if not self.pending_matches:
                    break
                    
                match_to_assign = self.pending_matches.pop(0)
                await self.assign_match_to_station(ctx, match_to_assign, station_num)
                assigned_count += 1
                
            if assigned_count > 0:
                await ctx.send(f"📋 {assigned_count} match(s) assigné(s) aux stations")
                
        except Exception as e:
            print(f"Erreur lors de l'assignation: {e}")
    
    async def assign_match_to_station(self, ctx, sgg_match, station_number: int):
        """Assigne un match spécifique à une station"""
        try:
            # Créer l'objet Match
            my_match = sggMatch_to_MyMatch(sgg_match, self.tournament.bestOf_N)
            
            # Configurer les personnages
            character_names = [char['name'] for char in self.tournament.characterList]
            my_match.set_characters(self.tournament.characterList)
            
            # Assigner à la station
            my_match.set_station(self.get_station_id_by_number(station_number))
            my_match.start_match()
            
            # Marquer la station comme utilisée
            for station in self.tournament.station:
                if station['number'] == station_number:
                    station['isUsed'] = True
                    station['current_match'] = sgg_match
                    break
            
            # Créer un canal pour ce match
            channel = await self.create_match_channel(ctx.guild, my_match, station_number)
            
            # Stocker les infos du match actif
            self.active_matches[station_number] = {
                'match_object': my_match,
                'sgg_match': sgg_match,
                'channel': channel,
                'task': None,
                'start_time': asyncio.get_event_loop().time()
            }
            
            # Lancer le match en arrière-plan
            task = asyncio.create_task(self.run_match(channel, my_match, station_number))
            self.active_matches[station_number]['task'] = task
            
            # Notification
            p1_name = sgg_match['slots'][0]['entrant']['name']
            p2_name = sgg_match['slots'][1]['entrant']['name']
            await ctx.send(f"🎮 Match assigné à la station {station_number}: **{p1_name}** vs **{p2_name}**")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de l'assignation du match: {e}")
    
    def get_station_id_by_number(self, station_number: int) -> str:
        """Récupère l'ID de la station par son numéro"""
        for station in self.tournament.station:
            if station['number'] == station_number:
                return station['id']
        raise ValueError(f"Station {station_number} non trouvée")
    
    async def create_match_channel(self, guild, my_match: Match, station_number: int):
        """Crée un canal pour le match"""
        try:
            # Trouve ou crée la catégorie des matchs
            category = discord.utils.get(guild.categories, name="⚔ Matchs en cours")
            if not category:
                category = await guild.create_category("⚔ Matchs en cours")
            
            # Crée le canal
            channel_name = f"station-{station_number}"
            channel = await guild.create_text_channel(channel_name, category=category)
            
            return channel
        except Exception as e:
            print(f"Erreur création canal: {e}")
            return None
    
    async def run_match(self, channel, my_match: Match, station_number: int):
        """Exécute un match complet"""
        try:
            if not channel:
                print("Pas de canal disponible pour le match")
                return
                
            p1_name = my_match.p1['name']
            p2_name = my_match.p2['name']
            
            await channel.send(f"🎯 **Match démarré** - {p1_name} vs {p2_name} (BO{my_match.bestOf_N})")
            
            # Importer ici pour éviter les imports circulaires
            from match_report import send_match_report
            
            # Boucle des games
            for game_num in range(1, my_match.bestOf_N + 1):
                if my_match.isComplete:
                    break
                    
                await channel.send(f"**Game {game_num}** - En attente du report...")
                
                try:
                    # Attendre le report avec timeout
                    result = await asyncio.wait_for(
                        send_match_report(
                            channel=channel,
                            player1=p1_name,
                            player2=p2_name,
                            characters=my_match.charactersName
                        ),
                        timeout=1800  # 30 minutes
                    )
                    
                    # Traiter le résultat
                    if result["isP1Winner"]:
                        my_match.report_Match(True, result['p1_char'], result['p2_char'])
                        await channel.send(f"✅ Game {game_num} reportée: **{p1_name}** gagne")
                    else:
                        my_match.report_Match(False, result['p1_char'], result['p2_char'])
                        await channel.send(f"✅ Game {game_num} reportée: **{p2_name}** gagne")
                    
                    if my_match.isComplete:
                        winner_name = p1_name if my_match.p1_score > my_match.p2_score else p2_name
                        await channel.send(f"🏆 **Match terminé !** Vainqueur: **{winner_name}**")
                        
                        # IMPORTANT: Reporter le résultat sur start.gg
                        await self.report_match_to_startgg(my_match, channel)
                        break
                        
                except asyncio.TimeoutError:
                    await channel.send("⌛ Temps écoulé pour ce game - Match en pause")
                    return
                    
        except Exception as e:
            await channel.send(f"❌ Erreur pendant le match: {e}")
            print(f"Erreur match: {e}")
        finally:
            # Marquer le match comme terminé
            if station_number in self.active_matches:
                self.active_matches[station_number]['completed'] = True
    
    async def report_match_to_startgg(self, my_match: Match, channel):
        """Reporte le résultat du match sur start.gg"""
        try:
            # Cette fonction devrait être implémentée dans votre classe Match ou Tournament
            # Elle doit faire l'appel API pour reporter le résultat
            success = my_match.submit_to_startgg()  # À implémenter
            
            if success:
                await channel.send("✅ Résultat reporté sur start.gg")
            else:
                await channel.send("⚠️ Erreur lors du report sur start.gg")
                
        except Exception as e:
            await channel.send(f"❌ Erreur report start.gg: {e}")
            print(f"Erreur report start.gg: {e}")
    
    async def check_completed_matches(self, ctx):
        """Vérifie et nettoie les matchs terminés"""
        completed_stations = []
        
        for station_num, match_info in self.active_matches.items():
            task = match_info['task']
            my_match = match_info['match_object']
            
            # Vérifier si le match est terminé
            if (task and task.done()) or my_match.isComplete or match_info.get('completed', False):
                completed_stations.append(station_num)
        
        # Nettoyer les matchs terminés
        for station_num in completed_stations:
            await self.cleanup_completed_match(ctx, station_num)
    
    async def cleanup_completed_match(self, ctx, station_number: int):
        """Nettoie un match terminé et libère la station"""
        try:
            match_info = self.active_matches.get(station_number)
            if not match_info:
                return
            
            # Libérer la station
            for station in self.tournament.station:
                if station['number'] == station_number:
                    station['isUsed'] = False
                    if 'current_match' in station:
                        del station['current_match']
                    break
            
            # Programmer la suppression du canal
            if match_info.get('channel'):
                channel = match_info['channel']
                asyncio.create_task(self.delayed_channel_cleanup(channel))
            
            # Nettoyer la liste des matchs actifs
            del self.active_matches[station_number]
            
            # Forcer un refresh des matchs après completion
            await self.refresh_pending_matches(ctx)
            
            if ctx:
                await ctx.send(f"🔄 Station {station_number} libérée - Recherche de nouveaux matchs...")
            
        except Exception as e:
            print(f"Erreur nettoyage: {e}")
    
    async def delayed_channel_cleanup(self, channel):
        """Supprime un canal après un délai"""
        try:
            await asyncio.sleep(300)  # 5 minutes de délai
            await channel.delete()
        except:
            pass  # Canal peut-être déjà supprimé
    
    async def get_status(self, ctx):
        """Affiche le statut actuel du gestionnaire"""
        embed = discord.Embed(
            title="📊 Statut du Gestionnaire de Matchs",
            color=0x00ff00 if self.is_running else 0xff0000
        )
        
        embed.add_field(
            name="État", 
            value="🟢 Actif" if self.is_running else "🔴 Arrêté", 
            inline=True
        )
        
        embed.add_field(
            name="Matchs en attente", 
            value=len(self.pending_matches), 
            inline=True
        )
        
        embed.add_field(
            name="Matchs en cours", 
            value=len(self.active_matches), 
            inline=True
        )
        
        # Détail des stations
        if self.active_matches:
            stations_info = []
            for station_num, match_info in self.active_matches.items():
                sgg_match = match_info['sgg_match']
                p1 = sgg_match['slots'][0]['entrant']['name']
                p2 = sgg_match['slots'][1]['entrant']['name']
                stations_info.append(f"Station {station_num}: {p1} vs {p2}")
            
            embed.add_field(
                name="Stations actives",
                value="\n".join(stations_info) if stations_info else "Aucune",
                inline=False
            )
        
        await ctx.send(embed=embed)