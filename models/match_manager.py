import asyncio
import copy
from typing import Dict, List
import discord
from discord.ext import commands
from models.match import Match
from models.tournament import Tournament, sggMatch_to_MyMatch
from models.lang import translate

class MatchManager:
    def __init__(self, bot: commands.Bot, tournament: Tournament , player_can_check_presence_of_other_player: bool = False):
        self.bot = bot
        self.tournament = tournament
        self.active_matches: Dict[int, Dict] = {}  # station_number -> match_info
        self.pending_matches: List[Dict] = []  # Liste des matchs en attente
        self.is_running = False
        self.player_can_check_presence_of_other_player = player_can_check_presence_of_other_player  # Indique si les joueurs peuvent vérifier la présence de l'autre
        self.player_list = {}  # Dictionnaire pour stocker les joueurs et leurs IDs Discord
        self.match_already_played = []
    def are_players_available(self, match_to_check):
        """Vérifie si les joueurs du match ne sont pas déjà dans un match en cours"""
        p1_id = match_to_check['slots'][0]['entrant']['id']
        p2_id = match_to_check['slots'][1]['entrant']['id']
        p1_discord_id = self.tournament.DiscordIdForPlayer.get(p1_id)
        p2_discord_id = self.tournament.DiscordIdForPlayer.get(p2_id)
        
        for player_id in self.bot.player_in_game:
            if player_id == p1_discord_id:
                return False, match_to_check['slots'][0]['entrant']['name']
            if player_id == p2_discord_id:
                return False, match_to_check['slots'][1]['entrant']['name']
        
        return True, None
        
        return True
    def deepcopy(self):
        # Crée une nouvelle instance sans appeler __init__ (pour éviter side effects)
        new_manager = MatchManager.__new__(MatchManager)

        # Copier les attributs simples
        new_manager.bot = self.bot  # Référence au bot, pas besoin de deepcopy
        new_manager.tournament = copy.deepcopy(self.tournament)

        # Copie profonde des dictionnaires et listes
        new_manager.active_matches = copy.deepcopy(self.active_matches)
        new_manager.pending_matches = copy.deepcopy(self.pending_matches)
        new_manager.match_already_played = copy.deepcopy(self.match_already_played)

        # Copie des autres attributs
        new_manager.is_running = copy.copy(self.is_running)
        new_manager.player_can_check_presence_of_other_player = copy.copy(self.player_can_check_presence_of_other_player)
        new_manager.player_list = copy.deepcopy(self.player_list)
 

        return new_manager

        return new_manager   
    async def initialize_matches(self, interaction):
        """Initialise la liste des matchs en attente"""
        try:
            matches = self.tournament.get_matches(state=1)  # Matchs non commencés
            
            self.pending_matches = matches.copy()
            await interaction.followup.send(translate("pending_matches_count", count=len(self.pending_matches)))
            return True
        except Exception as e:
            await interaction.followup.send(translate("match_fetch_error", error=e))
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
                try:
                    await interaction.followup.send(translate("new_matches_added", count=len(new_pending_matches)))
                except discord.errors.NotFound:
                    if hasattr(interaction, 'channel') and interaction.channel:
                        await interaction.channel.send(translate("new_matches_added", count=len(new_pending_matches)))
            return len(new_pending_matches)
            
        except Exception as e:
            print(translate("refresh_error_log", error=e))
            if interaction:
                try:
                    await interaction.followup.send(translate("refresh_error", error=e))
                except discord.errors.NotFound:
                    if hasattr(interaction, 'channel') and interaction.channel:
                        await interaction.channel.send(translate("refresh_error", error=e))
            return 0
    
    async def start_match_processing(self, interaction):
        """Démarre le processus automatique de gestion des matchs"""
        if self.is_running:
            await interaction.followup.send(translate("match_manager_already_running"))
            return
        if not self.pending_matches:
            if not await self.initialize_matches(interaction):
                return
        self.is_running = True
        await interaction.followup.send(translate("match_manager_started"))
        asyncio.create_task(self.match_processing_loop(interaction))
    
    async def stop_match_processing(self, interaction):
        """Arrête le processus automatique"""
        self.is_running = False
        await interaction.followup.send(translate("match_manager_stopped"))
    
    async def match_processing_loop(self, interaction):
        """Boucle principale qui gère l'attribution automatique des matchs"""
        refresh_counter = 0
        
        while self.is_running and (self.pending_matches or self.active_matches):
            try:
                await self.assign_pending_matches(interaction)
                await self.check_completed_matches(interaction)
                refresh_counter += 1
                if refresh_counter >= 6:
                    new_matches_count = await self.refresh_matches_list()
                    if new_matches_count > 0:
                        print(translate("new_matches_log", count=new_matches_count))
                    refresh_counter = 0
                await asyncio.sleep(5)
            except Exception as e:
                print(translate("processing_loop_error_log", error=e))
                await asyncio.sleep(10)
        self.is_running = False
        await interaction.followup.send(translate("all_matches_processed"))
    
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
            
            # Variables pour suivre l'état précédent
            if not hasattr(self, '_last_availability_status'):
                self._last_availability_status = None
                self._unavailable_players = set()
            
            current_unavailable_players = set()
            any_available = False
            
            # Assigner un match par station disponible
            for station_num in available_stations:
                if not self.pending_matches:
                    break
                    
                # Trouver le premier match avec des joueurs disponibles
                match_index = None
                for i, match in enumerate(self.pending_matches):
                    if match['id'] in self.match_already_played:
                        continue
                    available, unavailable_player = self.are_players_available(match)
                    if available:
                        match_index = i
                        any_available = True
                        break
                    elif unavailable_player:
                        current_unavailable_players.add(unavailable_player)
                
                if match_index is None:
                    # Aucun match avec joueurs disponibles
                    if current_unavailable_players != self._unavailable_players:
                        # Envoyer un message seulement si la liste des joueurs indisponibles a changé
                        players_list = ", ".join(current_unavailable_players)
                        await interaction.followup.send(
                            translate("players_unavailable", players=players_list),
                            delete_after=60  # Supprime le message après 60 secondes
                        )
                        self._unavailable_players = current_unavailable_players
                    return
                    
                match_to_assign = self.pending_matches.pop(match_index)
                await self.assign_match_to_station(interaction, match_to_assign, station_num)
                
        except Exception as e:
            print(f"Assignation Error: {e}")
    
    async def assign_match_to_station(self, interaction, sgg_match, station_number: int):
        """Assigne un match spécifique à une station"""
        try:
            my_match = sggMatch_to_MyMatch(sgg_match, self.tournament)
            character_names = [char['name'] for char in self.tournament.characterList]
            my_match.set_characters(self.tournament.characterList)
            my_match.set_station(self.get_station_id_by_number(station_number))
            my_match.start_match()
            for station in self.tournament.station:
                if station['number'] == station_number:
                    station['isUsed'] = True
                    station['current_match'] = sgg_match
                    break
            # Ajouter les joueurs à la liste des joueurs en jeu
            p1_id = sgg_match['slots'][0]['entrant']['id']
            p2_id = sgg_match['slots'][1]['entrant']['id']
            p1_id = self.tournament.DiscordIdForPlayer.get(p1_id)
            p2_id = self.tournament.DiscordIdForPlayer.get(p2_id)
            self.bot.player_in_game.extend([p1_id, p2_id])  # Modification ici
            channel = await self.create_match_channel(interaction.guild, my_match, station_number)
            self.active_matches[station_number] = {
                'match_object': my_match,
                'sgg_match': sgg_match,
                'channel': channel,
                'task': None
            }
            task = asyncio.create_task(self.run_match(channel, my_match, station_number))
            self.active_matches[station_number]['task'] = task
            p1_name = sgg_match['slots'][0]['entrant']['name']
            p2_name = sgg_match['slots'][1]['entrant']['name']
            p1_id = sgg_match['slots'][0]['entrant']['id']
            p2_id = sgg_match['slots'][1]['entrant']['id']
            try:
                p1_id = self.tournament.DiscordIdForPlayer.get(p1_id)
                p2_id = self.tournament.DiscordIdForPlayer.get(p2_id)
                self.bot.player_in_game.append(p1_id, p2_id)
                await interaction.followup.send(translate("match_assigned", station=station_number, p1=p1_name, p2=p2_name))
            except:
                await interaction.channel.send(translate("match_assigned", station=station_number, p1=p1_name, p2=p2_name))
        except Exception as e:
            try:
                await interaction.followup.send(translate("match_assign_error", error=e))
            except:
                await interaction.channel.send(translate("match_assign_error", error=e))
    
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
            print(f"Error match channel: {e}")
            return None

    async def run_match(self, channel, my_match, station_number):
        """Exécute un match complet avec vérification de présence"""
        try:
            if not channel:
                print(translate("no_channel_for_match"))
                return
            self.match_already_played.append(my_match.matchId)
            # Récupérer les informations du match
            p1_id_sgg = my_match.p1['id']
            p2_id_sgg = my_match.p2['id']
            p1_name = my_match.p1['name']
            p2_name = my_match.p2['name']
            
            # Récupérer l'ID du set pour les appels API
            sgg_match = self.active_matches[station_number]['sgg_match']
            set_id = sgg_match['id']
            
            # Marquer le set comme en attente des joueurs
            self.tournament.sgg_request.mark_set_as_pending(set_id)
            
            # Vérifier la présence des joueurs
            from view.player_presence import check_player_presence
            presence_result = await check_player_presence(channel, my_match, self, station_number)
            
            if presence_result == 'dq_p1':
                # Disqualifier le joueur 1, le joueur 2 gagne
                await channel.send(translate("player_dq_no_show", player=p1_name, winner=p2_name))
                self.tournament.sgg_request.DQ_player(set_id, p2_id_sgg)
                await channel.send(translate("channel_delete_soon"))
                asyncio.create_task(self.schedule_channel_deletion(channel, station_number))
                return
                
            elif presence_result == 'dq_p2':
                # Disqualifier le joueur 2, le joueur 1 gagne
                await channel.send(translate("player_dq_no_show", player=p2_name, winner=p1_name))
                self.tournament.sgg_request.DQ_player(set_id, p1_id_sgg)
                await channel.send(translate("channel_delete_soon"))
                asyncio.create_task(self.schedule_channel_deletion(channel, station_number))
                return
            
            self.tournament.sgg_request.startMatch(set_id)
            
            
            # Continuer avec le code existant du match...
            from view.match_report import send_match_report
            
            for game_num in range(1, my_match.bestOf_N + 1):
                if my_match.isComplete:
                    break
                    
                await channel.send(translate("game_waiting_report", game=game_num))
                
                try:
                    result = await asyncio.wait_for(
                        send_match_report(
                            channel=channel,
                            player1=p1_name,
                            player2=p2_name,
                            characters=my_match.charactersName
                        ),
                        timeout=1800
                    )
                    
                    if result["isP1Winner"]:
                        my_match.report_Match(True, result['p1_char'], result['p2_char'])
                        await channel.send(translate("game_reported", game=game_num, winner=p1_name))
                    else:
                        my_match.report_Match(False, result['p1_char'], result['p2_char'])
                        await channel.send(translate("game_reported", game=game_num, winner=p2_name))
                    
                    if my_match.isComplete:
                        winner_name = p1_name if my_match.p1_score > my_match.p2_score else p2_name
                        await channel.send(translate("match_finished", winner=winner_name))
                        await channel.send(translate("channel_delete_soon"))
                        asyncio.create_task(self.schedule_channel_deletion(channel, station_number))
                        break
                        
                except asyncio.TimeoutError:
                    await channel.send(translate("game_timeout"))
                    return
                    
        except Exception as e:
            await channel.send(translate("match_error", error=e))
            print(translate("match_error_log", error=e))

    
    async def schedule_channel_deletion(self, channel, station_number: int):
        """Programme la suppression du channel après 1 minute"""
        try:
            await asyncio.sleep(60)
            if channel:
                await channel.delete()
                print(translate("channel_deleted_log", station=station_number))
        except discord.NotFound:
            print(translate("channel_already_deleted_log", station=station_number))
        except discord.Forbidden:
            print(translate("channel_delete_permission_error_log", station=station_number))
        except Exception as e:
            print(translate("channel_delete_error_log", station=station_number, error=e))
    
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
            # Retirer les joueurs de la liste des joueurs en jeu
            sgg_match = match_info['sgg_match']
            p1_id = sgg_match['slots'][0]['entrant']['id']
            p2_id = sgg_match['slots'][1]['entrant']['id']
            p1_id = self.tournament.DiscordIdForPlayer.get(p1_id)
            p2_id = self.tournament.DiscordIdForPlayer.get(p2_id)
            try:
                self.bot.player_in_game.remove(p1_id)
                self.bot.player_in_game.remove(p2_id)
            except ValueError:
                pass  # En cas où les IDs ne sont pas dans la liste
            for station in self.tournament.station:
                if station['number'] == station_number:
                    station['isUsed'] = False
                    if 'current_match' in station:
                        del station['current_match']
                    break
            del self.active_matches[station_number]
            await self.refresh_matches_list()
            try:
                await interaction.followup.send(translate("station_freed", number=station_number))
            except:
                if hasattr(interaction, 'channel'):
                    await interaction.channel.send(translate("station_freed", number=station_number))
        except Exception as e:
            print(translate("cleanup_error_log", error=e))
    
    async def get_status(self, interaction):
        """Affiche le statut actuel du gestionnaire"""
        embed = discord.Embed(
            title=translate("match_manager_status_title"),
            color=0x00ff00 if self.is_running else 0xff0000
        )
        embed.add_field(
            name=translate("status_state_label"),
            value=translate("status_active") if self.is_running else translate("status_stopped"),
            inline=True
        )
        embed.add_field(
            name=translate("status_pending_matches_label"),
            value=len(self.pending_matches),
            inline=True
        )
        embed.add_field(
            name=translate("status_active_matches_label"),
            value=len(self.active_matches),
            inline=True
        )
        if self.active_matches:
            stations_info = []
            for station_num, match_info in self.active_matches.items():
                sgg_match = match_info['sgg_match']
                p1 = sgg_match['slots'][0]['entrant']['name']
                p2 = sgg_match['slots'][1]['entrant']['name']
                stations_info.append(translate("status_station_info", station=station_num, p1=p1, p2=p2))
            embed.add_field(
                name=translate("status_active_stations_label"),
                value="\n".join(stations_info) if stations_info else translate("status_none"),
                inline=False
            )
        await interaction.followup.send(embed=embed)