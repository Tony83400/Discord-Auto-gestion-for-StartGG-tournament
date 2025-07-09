
from models.lang import translate

class Match:
    def __init__(self, p1,p2 , matchId , bestOf_N , startGG, round):
        self.p1 = p1
        self.p2 = p2
        self.p1_score = 0  # Initialize player 1 score
        self.p2_score = 0
        self.matchId = matchId
        self.sgg_request = startGG
        self.stationNumber = -1  # Default value for station number
        self.gameData = []
        self.bestOf_N = bestOf_N  # Number of games in the match
        self.number_of_games_to_win = bestOf_N - int(bestOf_N/2)  # Total number of games in the match
        self.isComplete = False
        self.charactersName = []  # List to store character names, if needed
        self.characters = {}  # Dictionary to store character IDs and names
        self.charactersIDbyName = {}  # Dictionary to store character names by ID, if needed
        self.round = round
    def set_characters(self, characters):
        # Set the characters for the match
        self.characters = {char['id']: char['name'] for char in characters}
        self.charactersName = [char['name'] for char in characters]
        self.charactersIDbyName = {char['name']: char['id'] for char in characters}
    def start_match(self):
        # Start the match using the StartGG API
        result = self.sgg_request.startMatch(self.matchId)
    def set_station(self, station_id):
        # Set the station number for the match
        self.stationNumber = station_id
        print(translate("station_assigned_log", station=station_id, match=self.matchId))
        self.sgg_request.assign_station_to_set(self.matchId, station_id)
    def report_Match(self, isWinnerP1 : bool , characterP1_name : int, characterP2_name: int):
 
        p1_char_id = self.charactersIDbyName.get(characterP1_name, None)
        p2_char_id = self.charactersIDbyName.get(characterP2_name, None)

        p1_Id = self.p1['id']
        p2_Id = self.p2['id']
        winner = self.p1 if isWinnerP1 else self.p2
        match = {
           'gameNum' : len(self.gameData) + 1,  # Commence à 1, pas à 0
           'winnerId': winner['id'],  # ID de l'entrant gagnant
              'selections': [
                {'entrantId': p1_Id, 'characterId': p1_char_id},  # ID de l'entrant et ID du personnage
                {'entrantId':  p2_Id, 'characterId': p2_char_id}   # ID de l'entrant et ID du personnage
              ]
       }
        #Ajoute le nombre de game gagné au joueur gagnant
        if isWinnerP1:
            self.p1['gamesWon'] = self.p1.get('gamesWon', 0) + 1
        else:
            self.p2['gamesWon'] = self.p2.get('gamesWon', 0) + 1
        self.gameData.append(match)
        if winner['gamesWon'] >= self.number_of_games_to_win:
           # Si tous les jeux sont terminés, on envoie le rapport de match
           result = self.sgg_request.update_match_score(self.matchId, self.gameData, self.gameData[-1]['winnerId'])
           self.gameData = []  # Réinitialise les données du match après l'envoi
           self.isComplete = True
    # Dans match.py, ajoutez cette méthode :
    def submit_to_startgg(self):
        """Soumet le résultat du match à start.gg"""
        try:
            # Utiliser votre objet StartGG pour reporter le résultat
            # Exemple d'appel API (à adapter selon votre implémentation)
            result = self.startgg_api.report_match(
                match_id=self.sggId,
                p1_score=self.p1_score,
                p2_score=self.p2_score,
                winner_id=self.p1['id'] if self.p1_score > self.p2_score else self.p2['id']
            )
            return result.get('success', False)
        except Exception as e:
            print(translate("startgg_report_error", error=e))
            return False
