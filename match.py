from startgg_request import StartGG

class Match:
    def __init__(self, p1,p2 , matchId , bestOf_N , startGG):
        self.p1 = p1
        self.p2 = p2
        self.matchId = matchId
        self.sgg_request = startGG
        self.stationNumber = -1  # Default value for station number
        self.gameData = []
        self.number_of_games_to_win = bestOf_N - int(bestOf_N/2)  # Total number of games in the match

    def start_match(self):
        # Start the match using the StartGG API
        result = self.sgg_request.startMatch(self.matchId)
    def set_station(self, station_number):
        # Set the station number for the match
        self.stationNumber = station_number
    def report_Match(self, isWinnerP1 : bool , characterP1_id : int, characterP2_id : int):
        p1_Id = self.p1['id']
        p2_Id = self.p2['id']
        winner = self.p1 if isWinnerP1 else self.p2
        match = {
           'gameNum' : len(self.gameData) + 1,  # Commence à 1, pas à 0
           'winnerId': winner['id'],  # ID de l'entrant gagnant
              'selections': [
                {'entrantId': p1_Id, 'characterId': characterP1_id},  # ID de l'entrant et ID du personnage
                {'entrantId':  p2_Id, 'characterId': characterP2_id}   # ID de l'entrant et ID du personnage
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