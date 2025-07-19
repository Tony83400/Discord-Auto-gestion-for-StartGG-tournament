from models.startgg_request import StartGG
from models.match import Match
from dotenv import load_dotenv
import os

load_dotenv()  # Charge le fichier .env

sggKey = os.getenv('START_GG_KEY')
class Tournament:
    def __init__(self, slug):
        self.slug = slug
        self.sgg_request = StartGG(sggKey)
        self.events = None
        self.selectedEvent = None
        self.name= None
        self.station = None
        self.IsAdmin = None
        self.selectedPhaseId = None
        self.selectedPoolId = None
        self.selectedPool = None
        self.playerList = []
        self.DiscordIdForPlayer = {}
        self.selectedPhase = None
        self.rounds = None
        self.id = None
        self.numAttendees = 0
        self.characterList = self.sgg_request.get_all_characters() #Peut etre changer pour d'autre jeux
        self.bestOf_N = 3  # Nombre de jeux par match, peut être modifié selon le tournoi
        self.round_where_bo5_start_winner = None 
        self.round_where_bo5_start_loser = None
        self.bo_custom = False  # Indique si la configuration par round est personnalisée
        result = self.sgg_request.get_tournament(slug)
        if result:
            self.name = result.get('name')
            self.events = result.get('events', [])
            self.selectedEvent = None
            self.id = result.get('id')
            self.IsAdmin = result.get('admins', []) != None
        else:
            raise ValueError(f"Tournament with slug '{slug}' not found.")
    def _set_player_list(self):
        if self.selectedEvent:
            players = self.sgg_request.get_all_player_event(self.selectedEvent['id'])
            if players:
                for player in players:
                    newPlayer = {
                        'id': player['id'],
                        'name': player['name'],
                    }
                    if player['participants'][0]['user'] != None:
                            for elt in player['participants'][0]['user']['authorizations']:
                                if elt['type'] == 'DISCORD':
                                    newPlayer['discordId'] = elt['externalId']
                                    newPlayer['discordName'] = elt['externalUsername']
                    else:
                        newPlayer['discordId'] = None
                        newPlayer['discordName'] = None
                    self.playerList.append(newPlayer)
                for player in self.playerList:
                    if player['discordId'] != None:
                        self.DiscordIdForPlayer[player['id']] = player['discordId']
            else:
                raise ValueError("No players found for the selected event.")
        else:
            raise ValueError("No event selected. Please select an event first.")
    def select_event(self, event_id :int):
        self.selectedEvent = self.sgg_request.get_event_phases(event_id)
        if self.selectedEvent:
            self._set_player_list()
            self.characterList = self.sgg_request.get_all_characters(self.selectedEvent['videogame']['id'])  # Mettre à jour la liste des personnages pour l'événement sélectionné
    def select_event_by_name(self, event_name: str):
        event_name = event_name.replace('-', ' ')
        if self.events:
            for event in self.events:
                if event['name'].lower() == event_name.lower():
                    self.selectedEvent = self.sgg_request.get_event_phases(event['id'])
                    return

    def set_best_of(self, bestOf_N: int, round_where_bo5_start_winner: int = None , round_where_bo5_start_loser: int = None):
        if bestOf_N > 0:
            self.bestOf_N = bestOf_N
            self.round_where_bo5_start_winner = round_where_bo5_start_winner
            self.round_where_bo5_start_loser = round_where_bo5_start_loser
        else:
            raise ValueError("Best of N must be a positive integer.")
    def get_event_phases(self):
        if self.selectedEvent:
            phases = self.sgg_request.get_event_phases(self.selectedEvent['id'])
            if phases:
                return phases
            else:
                raise ValueError("No phases found for the selected event.")
        else:
            raise ValueError("No event selected. Please select an event first.")
    
    def select_event_phase(self, phase_id: int):
        if phase_id is not int:
            if phase_id.isdigit():
                phase_id = int(phase_id)
            else:
                return
            
        if self.selectedEvent:
            self.selectedPhaseId = phase_id
            for phase in self.selectedEvent['phases']:
                if int(phase['id']) == int(phase_id):
                    self.selectedPhase = phase
                    self.selectedPoolId = None
        else:
            raise ValueError("No event selected. Please select an event first.")
    def select_pool(self, pool_id: int):
        if pool_id is not int:
            if pool_id.isdigit():
                pool_id = int(pool_id)
            else:
                return
        if self.selectedPhase is None:
            return
        if self.selectedEvent:
            self.selectedPoolId = pool_id
            for pool in self.selectedPhase.get('phaseGroups', [])['nodes']:
                if int(pool['id']) == int(pool_id):
                    self.selectedPool = pool
                    self._set_player_list()
        else:
            raise ValueError("No event selected. Please select an event first.")
    def order_match(self,matchList):
        if not matchList:
            return []
        def custom_sort_key(item):
            round_val = item['round']
            if round_val < 0:
                return (0, -round_val)  # Groupe 0 (négatifs), tri décroissant
            else:
                return (1, round_val)    # Groupe 1 (positifs), tri croissant

        # Tri de la liste
        sorted_data = sorted(matchList, key=custom_sort_key)
        return sorted_data
    def get_matches(self, state : int = 1):
        if self.selectedEvent == None:
            raise ValueError("No event selected. Please select an event first.")
        if self.selectedPhaseId == None:
            raise ValueError("No phase selected. Please select an phase first.")
        if self.selectedPoolId == None:
            raise ValueError("No pool selected. Please select an pool first.")

        matches = self.sgg_request.get_phase_matches(self.selectedEvent['id'], self.selectedPhaseId, self.selectedPoolId , state)
        final_matches = []
        if matches:
            for match in matches[0]['sets']['nodes']:
                entrants = match['slots']
    
                if entrants[0]['entrant'] != None and entrants[1]['entrant'] != None and match['stream'] == None:
                    final_matches.append(match)
                    
            final_matches = self.order_match(final_matches)
            
            return final_matches
        else:
            raise ValueError("No matches found for the selected phase.")
    def get_round_of_match(self):
        if self.selectedEvent == None:
            raise ValueError("No event selected. Please select an event first.")
        if self.selectedPhaseId == None:
            raise ValueError("No phase selected. Please select an phase first.")
        if self.selectedPoolId == None:
            raise ValueError("No pool selected. Please select an pool first.")
        if self.rounds is not None:
            return self.rounds
        matches = self.sgg_request.get_phase_match_for_round(self.selectedEvent['id'], self.selectedPhaseId, self.selectedPoolId)
        if matches:
            roundList = []
            unique_rounds = []
            for r in matches['nodes']:
                if r['round'] not in roundList:
                    roundList.append(r['round'])
                    unique_rounds.append(r)
            self.rounds = unique_rounds
            return unique_rounds       
            
            
        else:
            raise ValueError("No matches found for the selected phase.")
    
    def assign_Match_to_station(self, match , station_number: int):
        if self.selectedEvent == None:
            raise ValueError("No event selected. Please select an event first.")
        if self.selectedPhaseId == None:
            raise ValueError("No phase selected. Please select an phase first.")
        if self.selectedPoolId == None:
            raise ValueError("No pool selected. Please select an pool first.")
        myMatch = sggMatch_to_MyMatch(match, self)
        for s in self.station:
            if s['number'] == station_number:
                if s['isUsed'] == False:
                    s['isUsed'] = True
                    myMatch.set_station(s['id'])
                    myMatch.start_match()
                    s['match'] = match
                    print(f"Match assigné à la station {station_number}.")
                    return match
                else:
                    raise ValueError(f"Station {station_number} is already in use.")
    def create_station(self, number):
        if not self.station:
            self.station = []
        else :
            for s in self.station:
                if s['number'] == number:
                    print(f"Station {number} already exists.")
                    return
        id = self.sgg_request.create_station(self.id, number)
        if id is None:
            print(f"Failed to create station {number}.")
            return
        new_station = {
            'number': number,
            'isUsed': False,
            'id': id,  # ID will be set when the station is created in StartGG
            'match': None
        }
        self.station.append(new_station)
        print(f"Station {number} created.")
        return new_station
       
    def delete_station(self, number):
        if self.station:
            for s in self.station:
                if s['number'] == number:
                    if not s['isUsed']:
                        self.sgg_request.delete_station(s['id'])
                        self.station.remove(s)
                        print(f"Station {number} deleted.")
                        return
                    else:
                        print(f"Station {number} already use and can't be deleted.")
                        return
            print(f"Station {number} don't exist.")
            return
        else:
            print("No stations available to delete.")
            return
    def find_station_available(self):
        if self.station:
            for s in self.station:
                if not s['isUsed']:
                    return s['number']
            print("No available station found.")
            return None
        else:
            print("No stations available.")
            return None
    

def sggMatch_to_MyMatch(match, tournament : Tournament):
    if tournament.round_where_bo5_start_winner is not None and tournament.round_where_bo5_start_loser is not None:
        if match['round'] >= tournament.round_where_bo5_start_winner and match['round'] >= 0:
            bestOf_N = 5
        elif match['round'] < 0 and match['round'] <= tournament.round_where_bo5_start_loser:
            bestOf_N = 5
        else :
            bestOf_N = 3
            
    else:
        bestOf_N = tournament.bestOf_N
    p1 = match['slots'][0]['entrant']
    p2 = match['slots'][1]['entrant']
    matchId = match['id']
    round = match['fullRoundText']
    return Match(p1, p2, matchId, bestOf_N, StartGG(sggKey) , round)
