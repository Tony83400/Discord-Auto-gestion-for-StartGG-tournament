import asyncio
from typing import Dict, List
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
        self.player_list = {}  # Dictionnaire pour stocker les joueurs et leurs IDs Discord
        
    async def initialize_matches(self, interaction):
        """Initialise la liste des matchs en attente"""
        try:
            matches = self.tournament.get_matches(state=1)  # Matchs non commencés
            self.pending_matches = matches.copy()
            await interaction.followup.send(f"🎯 {len(self.pending_matches)} matchs en attente de traitement")
            return True
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de la récupération des matchs: {e}")
            return False
    def reset_all_match(self):
        for id in self.active_matches:
            match = self.active_matches[id]
            match_id = match['sgg_match']['id']
            self.tournament.sgg_request.reset_set(match_id)

    async def refresh_matches_list(self, interaction=None):
        """Actualise la liste des matchs en attente depuis l'API"""
        try:
            # Récupérer les nouveaux matchs disponibles
            new_matches = self.tournament.get_matches(state=1)  # Matchs non commencés
            
            # Filtrer les matchs qui ne sont pas déjà en cours ou dans la liste d'attente
            current_match_ids = set()
            
            # Ajouter les IDs des matchs en cours
            for match_info in self.active_matches.values():
                current_match_ids.add(match_info['sgg_match']['id'])
            
            # Ajouter les IDs des matchs en attente
            for pending_match in self.pending_matches:
                current_match_ids.add(pending_match['id'])
            
            # Ajouter uniquement les nouveaux matchs
            new_pending_matches = []
            for match in new_matches:
                if match['id'] not in current_match_ids:
                    new_pending_matches.append(match)
                    self.pending_matches.append(match)
            
            if new_pending_matches and interaction:
                await interaction.followup.send(f"🔄 {len(new_pending_matches)} nouveaux matchs détectés et ajoutés à la file")
            
            return len(new_pending_matches)
            
        except Exception as e:
            print(f"Erreur lors de l'actualisation des matchs: {e}")
            if interaction:
                await interaction.followup.send(f"❌ Erreur lors de l'actualisation: {e}")
            return 0
    
    async def start_match_processing(self, interaction):
        """Démarre le processus automatique de gestion des matchs"""
        if self.is_running:
            await interaction.followup.send("⚠️ Le gestionnaire de matchs est déjà en cours d'exécution")
            return
            
        if not self.pending_matches:
            if not await self.initialize_matches(interaction):
                return
        
        self.is_running = True
        await interaction.followup.send("🚀 Démarrage du gestionnaire automatique de matchs")
        
        # Lancer la boucle principale
        asyncio.create_task(self.match_processing_loop(interaction))
    
    async def stop_match_processing(self, interaction):
        """Arrête le processus automatique"""
        self.is_running = False
        await interaction.followup.send("⏹️ Arrêt du gestionnaire de matchs demandé")
    
    async def match_processing_loop(self, interaction):
        """Boucle principale qui gère l'attribution automatique des matchs"""
        refresh_counter = 0
        
        while self.is_running and (self.pending_matches or self.active_matches):
            try:
                # Assigner de nouveaux matchs aux stations libres
                await self.assign_pending_matches(interaction)
                
                # Vérifier les matchs terminés
                await self.check_completed_matches(interaction)
                
                # Actualiser la liste des matchs toutes les 30 secondes (6 cycles de 5 secondes)
                refresh_counter += 1
                if refresh_counter >= 6:
                    new_matches_count = await self.refresh_matches_list()
                    if new_matches_count > 0:
                        print(f"Nouveaux matchs détectés: {new_matches_count}")
                    refresh_counter = 0
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Erreur dans la boucle de traitement: {e}")
                await asyncio.sleep(10)
        
        self.is_running = False
        await interaction.followup.send("✅ Tous les matchs ont été traités!")
    
    async def assign_pending_matches(self, interaction):
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
            for station_num in available_stations:
                if not self.pending_matches:
                    break
                    
                match_to_assign = self.pending_matches.pop(0)
                await self.assign_match_to_station(interaction, match_to_assign, station_num)
                
        except Exception as e:
            print(f"Erreur lors de l'assignation: {e}")
    
    async def assign_match_to_station(self, interaction, sgg_match, station_number: int):
        """Assigne un match spécifique à une station"""
        try:
            # Créer l'objet Match
            my_match = sggMatch_to_MyMatch(sgg_match, self.tournament)  # BO3 par défaut
            
            # Configurer les personnages (tu peux adapter selon tes besoins)
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
            channel = await self.create_match_channel(interaction.guild, my_match, station_number)
            
            # Stocker les infos du match actif
            self.active_matches[station_number] = {
                'match_object': my_match,
                'sgg_match': sgg_match,
                'channel': channel,
                'task': None
            }
            
            # Lancer le match en arrière-plan
            task = asyncio.create_task(self.run_match(channel, my_match, station_number))
            self.active_matches[station_number]['task'] = task
            
            # Notification
            p1_name = sgg_match['slots'][0]['entrant']['name']
            p2_name = sgg_match['slots'][1]['entrant']['name']
            
            # Utiliser followup si la réponse initiale a déjà été envoyée, sinon utiliser response
            try:
                await interaction.followup.send(f"🎮 Match assigné à la station {station_number}: **{p1_name}** vs **{p2_name}**")
            except:
                # Si followup échoue, essayer d'envoyer dans le channel où la commande a été exécutée
                await interaction.channel.send(f"🎮 Match assigné à la station {station_number}: **{p1_name}** vs **{p2_name}**")
            
        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Erreur lors de l'assignation du match: {e}")
            except:
                await interaction.channel.send(f"❌ Erreur lors de l'assignation du match: {e}")
    
    def get_station_id_by_number(self, station_number: int) -> str:
        """Récupère l'ID de la station par son numéro"""
        for station in self.tournament.station:
            if station['number'] == station_number:
                return station['id']
        raise ValueError(f"Station {station_number} non trouvée")
    
    async def create_match_channel(self, guild, my_match: Match, station_number: int):
        """Crée un canal pour le match uniquement visible par les joueurs concernés"""
        try:
            # Trouve ou crée la catégorie des matchs
            category = discord.utils.get(guild.categories, name="⚔ Matchs en cours")
            if not category:
                category = await guild.create_category("⚔ Matchs en cours")

            # Définir les permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False)  # cacher pour tous
            }
            p1_id_sgg = my_match.p1['id']
            p2_id_sgg = my_match.p2['id']
            print("\nJoueurs : ",my_match.p1, my_match.p2)
            print("Player List : ",self.player_list,"\n")
            print("Guild : ",guild)
            member1 = None
            member2 = None

            # Vérifier que les IDs existent dans le mapping
            p1_discord_id = self.tournament.DiscordIdForPlayer.get(p1_id_sgg)
            p2_discord_id = self.tournament.DiscordIdForPlayer.get(p2_id_sgg)
            if p1_discord_id is not None:
                p1_discord_id = int(p1_discord_id)
            if p2_discord_id is not None:   
                p2_discord_id = int(p2_discord_id)
            for m in guild.members:
                if int(m.id) == p1_discord_id:
                    member1 = m
                if int(m.id) == p2_discord_id:
                    member2 = m
            if member1:
                overwrites[member1] = discord.PermissionOverwrite(view_channel=True)
            if member2:
                overwrites[member2] = discord.PermissionOverwrite(view_channel=True)
            # Crée le canal avec les permissions
            channel_name = f"station-{station_number}"
            channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

            return channel
        except Exception as e:
            print(f"Erreur lors de la création du canal pour le match: {e}")
            return None

    async def run_match(self, channel, my_match: Match, station_number: int):
        """Exécute un match complet"""
        try:
            if not channel:
                print("Pas de canal disponible pour le match")
                return
                
            p1_id_sgg = my_match.p1['id']
            p2_id_sgg = my_match.p2['id']
            p1_name = my_match.p1['name']
            p2_name = my_match.p2['name']
            if p1_id_sgg not in self.tournament.DiscordIdForPlayer :
                p1_id = p1_id_sgg
            else:
                p1_id = self.tournament.DiscordIdForPlayer[p1_id_sgg]
                
            if p2_id_sgg not in self.tournament.DiscordIdForPlayer :
                p2_id = p2_id_sgg
            else:
                p2_id = self.tournament.DiscordIdForPlayer[p2_id_sgg]
            await channel.send(f"🎯 **Match démarré** - <@{p1_id}> vs <@{p2_id}> (BO{my_match.bestOf_N})")
            
            # Importer ici pour éviter les imports circulaires
            from match_report import send_match_report
            
            # Boucle des games
            for game_num in range(1, my_match.bestOf_N + 1):
                if my_match.isComplete:
                    break
                    
                await channel.send(f"**Game {game_num}** - En attente du report...")
                
                try:
                    # Attendre le report avec timeout plus long
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
                        
                        # NOUVEAU: Programmer la suppression du channel dans 1 minute
                        await channel.send("🕐 Ce channel sera supprimé dans 1 minute...")
                        asyncio.create_task(self.schedule_channel_deletion(channel, station_number))
                        break
                        
                except asyncio.TimeoutError:
                    await channel.send("⌛ Temps écoulé pour ce game - Match en pause")
                    # Ne pas annuler complètement, laisser la possibilité de reprendre
                    return
                    
        except Exception as e:
            await channel.send(f"❌ Erreur pendant le match: {e}")
            print(f"Erreur match: {e}")
    
    async def schedule_channel_deletion(self, channel, station_number: int):
        """Programme la suppression du channel après 1 minute"""
        try:
            # Attendre 1 minute
            await asyncio.sleep(60)
            
            # Supprimer le channel
            if channel:
                await channel.delete()
                print(f"Channel station-{station_number} supprimé automatiquement")
                
        except discord.NotFound:
            # Le channel a déjà été supprimé
            print(f"Channel station-{station_number} déjà supprimé")
        except discord.Forbidden:
            print(f"Pas les permissions pour supprimer le channel station-{station_number}")
        except Exception as e:
            print(f"Erreur lors de la suppression du channel station-{station_number}: {e}")
    
    async def check_completed_matches(self, interaction):
        """Vérifie et nettoie les matchs terminés"""
        completed_stations = []
        
        for station_num, match_info in self.active_matches.items():
            task = match_info['task']
            my_match = match_info['match_object']
            
            # Vérifier si le match est terminé
            if task and task.done() or my_match.isComplete:
                completed_stations.append(station_num)
        
        # Nettoyer les matchs terminés
        for station_num in completed_stations:
            await self.cleanup_completed_match(interaction, station_num)
    
    async def cleanup_completed_match(self, interaction, station_number: int):
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
            
            # Nettoyer la liste des matchs actifs (le channel sera supprimé automatiquement)
            del self.active_matches[station_number]
            
            # NOUVEAU: Actualiser la liste des matchs après avoir libéré une station
            await self.refresh_matches_list()
            
            # Essayer d'utiliser followup en premier, puis channel si ça échoue
            try:
                await interaction.followup.send(f"🔄 Station {station_number} libérée")
            except:
                # Si l'interaction n'est plus valide, utiliser le channel principal
                if hasattr(interaction, 'channel'):
                    await interaction.channel.send(f"🔄 Station {station_number} libérée")
            
        except Exception as e:
            print(f"Erreur nettoyage: {e}")
    
    async def get_status(self, interaction):
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
        
        await interaction.followup.send(embed=embed)
        