from startgg_request import StartGG
from match import Match
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
        self.station = None
        self.IsAdmin = None
        self.selectedPhaseId = None
        self.selectedPoolId = None
        self.playerList = []
        result = self.sgg_request.get_tournament(slug)
        if result:
            self.events = result.get('events', [])
            self.selectedEvent = None
            station = result.get('stations', {})['nodes']
            for s in station:
                s['isUsed'] = False
            self.station = station
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
            else:
                raise ValueError("No players found for the selected event.")
        else:
            raise ValueError("No event selected. Please select an event first.")
    def select_event(self, event_id :int):
        for event in self.events:
            if event['id'] == event_id:
                self.selectedEvent = event
                self._set_player_list()
                return
        raise ValueError(f"Event with slug '{event_id}' not found in tournament '{self.slug}'.")
    
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
        if self.selectedEvent:
            self.selectedPhaseId = phase_id
        else:
            raise ValueError("No event selected. Please select an event first.")
    def select_pool(self, pool_id: int):
        if self.selectedEvent:
            self.selectedPoolId = pool_id
        else:
            raise ValueError("No event selected. Please select an event first.")
    def get_matches(self, state : int = 1):
        if self.selectedEvent == None:
            raise ValueError("No event selected. Please select an event first.")
        if self.selectedPhaseId == None:
            raise ValueError("No phase selected. Please select an phase first.")
        if self.selectedPoolId == None:
            raise ValueError("No pool selected. Please select an pool first.")

        matches = self.sgg_request.get_phase_matches(self.selectedEvent['id'], self.selectedPhaseId, self.selectedPoolId , state)
        if matches:
            return matches[0]['sets']['nodes']
        else:
            raise ValueError("No matches found for the selected phase.")

myTournament = Tournament("test-7545")

myTournament.select_event(1366944)
# print(myTournament.playerList)

# phases = myTournament.get_event_phases()
# print(phases)
myTournament.select_pool(2872458)
myTournament.select_event_phase(1956358)
matches = myTournament.get_matches()
# print(matches)

# print(myTournament.station)
# print(myTournament.events)
p1 = {'name': 'P4', 'id': 20412918}
p2 = {'name': 'P5', 'id': 20412928}
myMatch = Match(p1, p2,90324698, 5, myTournament.sgg_request)
myMatch.set_station(1)
myMatch.start_match()
myMatch.report_Match(True, 1271, 1277)
myMatch.report_Match(True, 1271, 1277)
myMatch.report_Match(True, 1271, 1277)
myMatch.report_Match(True, 1271, 1277)