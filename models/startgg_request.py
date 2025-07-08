import requests
from typing import Optional, Dict, Any

class StartGG:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.start.gg/gql/alpha"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Méthode interne pour les requêtes GraphQL"""
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API error: {e}")
            return None
    
    def get_tournament(self, event_slug: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un événement par son slug."""
        query = """
 query Tournament($slug: String!) {
     tournament(slug: $slug) {
        id
        name
        events {
            id
            name
            numEntrants 
        }
        stations(perPage: 500) {
            nodes {
                id
                number
            }
        }
        admins(roles: null) {
            name
        }
    }
}
        """
        variables = {"slug": event_slug}
        response = self._make_request(query, variables)
        # return response
        if response and "data" in response:
            return response["data"]["tournament"]
        return None
    
    def get_event_phases(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les phases d'un événement par son ID."""
        query = """
            query EventPhases($eventId: ID!) {
                event(id: $eventId) {
                    id
                    name
                    numEntrants
                    phases {
                        id
                        name
                        phaseGroups {
                            nodes {
                                id
                                displayIdentifier
                            }
                        }
                    }
                    videogame {
                        id
                    }
                }
            }

        """
        variables = {"eventId": event_id}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["event"]
        return None
    
    #Récupère les matchs d'une phase spécifique
    def get_phase_matches(self,eventId : str ,  phase_id: str, phaseGroupId : str , state = 1 ) -> Optional[Dict[str, Any]]:
        """Récupère les matchs d'une phase spécifique. permet de filtrer par état."""
        query = """
    query PhaseSets($phaseId: ID!,$phaseGroupId: ID!, $eventId: ID! , $state: [Int]!) {
         event(id: $eventId) {
        phases(phaseId: $phaseId) {
            id
            name
            sets(filters: { phaseGroupIds: [$phaseGroupId], state: $state , hideEmpty: true}) {
                nodes {
                    id
                    identifier
                    round
                    slots {
                        entrant {
                            name
                            id
                        }
                    }
                    stream {
                        id
                    }
                    station {
                        id
                    }

                }
            }
        }
    }
    }
        """
        variables = {"phaseId": phase_id , "phaseGroupId": phaseGroupId, "eventId": eventId , "state": state}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["event"]["phases"]
        return None
    def get_phase_match_for_round(self,eventId : str ,  phase_id: str, phaseGroupId : str ) -> Optional[Dict[str, Any]]:
        """Récupère les matchs d'une phase spécifique. permet de filtrer par état."""
        query = """
    query PhaseSets($phaseId: ID!,$phaseGroupId: ID!, $eventId: ID!) {
         event(id: $eventId) {
        phases(phaseId: $phaseId) {
            sets(filters: { phaseGroupIds: [$phaseGroupId]}) {
                nodes {
                    round
                    fullRoundText
                }
            }
        }
    }
    }
        """
        variables = {"phaseId": phase_id , "phaseGroupId": phaseGroupId, "eventId": eventId}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["event"]["phases"][0]['sets']
        return None
    #Update le score d'un match
    def update_match_score(self, set_id: str, games: list[Dict], winner_id: str) -> Optional[Dict[str, Any]]:
        """Met à jour le score d'un match avec reportBracketSet
        
        Args:
            set_id: ID du set (ex: "90260300")
            games: Liste des jeux [
                {
                    "winnerId": str,  # ID de l'entrant gagnant
                    "gameNum": int,        # Numéro de la partie (commence à 1)
                    "selections": List[Dict]  # Optionnel
                    [
                        {"entrantId": str, "characterId": int},  # ID de l'entrant et ID du personnage
                        ...
                    ]
                }
            ]
            winner_id: ID de l'entrant gagnant
        """
        query = """
    mutation ReportBracketSet($setId: ID!, $winnerId: ID!, $gameData: [BracketSetGameDataInput!]!) {
        reportBracketSet(
            setId: $setId,
            winnerId: $winnerId,
            gameData: $gameData
        ) {
            id
            state
            identifier
        }
    }
        """
        
        # Formatage strict selon les exigences de l'API
        formatted_games = []
        for game in games:
            formatted_game = {
                "gameNum": game["gameNum"],  # Doit commencer à 1
                "winnerId": game["winnerId"],  # ID de l'entrant gagnant
                "selections": game.get("selections", [])
            }
            formatted_games.append(formatted_game)
        
        variables = {
            "setId": set_id,
            "winnerId": winner_id,
            "gameData": games
        }
        
        response = self._make_request(query, variables)
        # return response

        if response and "data" in response:
            return response["data"]["reportBracketSet"]
        
        return None
    def get_all_characters(self, id : int =1386) -> Optional[Dict[str, Any]]:
        """Récupère tous les personnages disponibles."""
        query = """
   query Videogame ($id: ID!) {
    videogame(id: $id) {
        characters {
            name
            id
        }
    }
}

        """
        variables = {"id": id}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["videogame"]["characters"]
        return None

    def get_all_player_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Récupère tous les joueurs d'un événement."""
        query = """
    query EventPlayers ($eventId: ID!, $pageNumber: Int!) {
    event(id: $eventId) {
        entrants(query: { page: $pageNumber, perPage: 100 }) {
            nodes {
                id
                name
                participants {
                    user {
                        authorizations {
                            id
                            externalId
                            externalUsername
                            type
                        }
                    }
                }
            }
        }
    }
}

        """
        for page in range(1, 100):
            variables = {"eventId": event_id, "pageNumber": page}
            response = self._make_request(query, variables)
            if response and "data" in response:
                players = response["data"]["event"]["entrants"]["nodes"]
                if not players:
                    break
            else:
                return None
            if page == 1:
                all_players = players
            else:
                all_players.extend(players)
        return all_players if 'all_players' in locals() else None
    
    def startMatch(self, matchId: str):
        """Démarre un match en utilisant l'API StartGG."""
        query = """
        mutation MarkSetInProgress ($matchId: ID!) {
            markSetInProgress(setId: $matchId) {
                id
            }
        }
        """
        variables = {"matchId": matchId}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["markSetInProgress"]
        return None
    def assign_station_to_set (self, set_id: str, station_id: str) -> Optional[Dict[str, Any]]:
        """Assigne une station à un set."""
        query = """
        mutation assignStation($setId: ID!, $stationId: ID!) {
            assignStation(setId: $setId, stationId: $stationId) {
                identifier
            }
        }
        """
        variables = {"setId": set_id, "stationId": station_id}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["assignStation"]
        return None
    def create_station(self, tournament_id: str, station_number: int) -> Optional[Dict[str, Any]]:
        """Crée une nouvelle station pour un événement."""
        query = """
        mutation UpsertStation( $tournamentId: ID!, $fields: StationUpsertInput!) {
        upsertStation(tournamentId: $tournamentId , fields: $fields) {
            id
        }
    }


        """
        variables = {"tournamentId": tournament_id, "fields": { "number":station_number }}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["upsertStation"]['id']
        return None
    def delete_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Supprime une station."""
        query = """
        mutation DeleteStation($stationId: ID!) {
            deleteStation(stationId: $stationId) 
        }
        """
        variables = {"stationId": station_id}
        response = self._make_request(query, variables)
        return response
    def reset_set(self, set_id: str) -> Optional[Dict[str, Any]]:
        """Réinitialise un set."""
        query = """
        mutation ResetSet($setId: ID!) {
            resetSet(setId: $setId) {
                id
            }
        }
        """
        variables = {"setId": set_id}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return True
        return False