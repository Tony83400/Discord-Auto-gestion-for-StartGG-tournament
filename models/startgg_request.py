import requests
import time
import os
from typing import Optional, Dict, Any, List
from collections import deque
from threading import Lock

class StartGG:
    def __init__(self, api_keys: Optional[List[str]] = None):
        """
        Initialise le client StartGG avec gestion des limites de rate.
        
        Args:
            api_keys: Liste des clés API. Si None, utilise les variables d'environnement
                     STARTGG_API_KEY_1, STARTGG_API_KEY_2, etc.
        """
        self.api_keys = api_keys or self._load_api_keys_from_env()
        if not self.api_keys:
            raise ValueError("Aucune clé API fournie. Voir la documentation pour configurer les variables d'environnement.")
        
        self.current_key_index = 0
        self.base_url = "https://api.start.gg/gql/alpha"
        
        # Rate limiting: 80 requêtes par minute par clé
        self.max_requests_per_minute = 80 
        self.request_history = {}  # Dict par clé API
        self.locks = {}  # Locks par clé API
        
        # Initialisation pour chaque clé
        for key in self.api_keys:
            self.request_history[key] = deque()
            self.locks[key] = Lock()
        print(f"🔑 Initialisation avec {len(self.api_keys)} clés API.")
        print("📊 Statut des limites de rate:")
        for key, status in self.get_rate_limit_status().items():
            print(f"  {key}: {status['requêtes_restantes']}/{self.max_requests_per_minute} requêtes restantes")    
    def _load_api_keys_from_env(self) -> List[str]:
        """Charge les clés API depuis les variables d'environnement."""
        keys = []
        i = 1
        while True:
            key = os.getenv(f'STARTGG_API_KEY_{i}')
            if key:
                keys.append(key)
                i += 1
            else:
                break
        
        # Fallback sur STARTGG_API_KEY si aucune clé numérotée n'est trouvée
        if not keys:
            main_key = os.getenv('STARTGG_API_KEY')
            if main_key:
                keys.append(main_key)
        
        return keys
    
    def _get_current_headers(self) -> Dict[str, str]:
        """Retourne les headers avec la clé API courante."""
        current_key = self.api_keys[self.current_key_index]
        return {
            "Authorization": f"Bearer {current_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _can_make_request(self, api_key: str) -> bool:
        """Vérifie si on peut faire une requête avec cette clé API."""
        with self.locks[api_key]:
            now = time.time()
            history = self.request_history[api_key]
            
            # Nettoie l'historique (garde seulement les requêtes de la dernière minute)
            while history and now - history[0] > 60:
                history.popleft()
            
            return len(history) < self.max_requests_per_minute
    
    def _record_request(self, api_key: str):
        """Enregistre une requête pour cette clé API."""
        with self.locks[api_key]:
            self.request_history[api_key].append(time.time())
    
    def _get_available_key(self) -> Optional[str]:
        """Trouve une clé API disponible ou attend qu'une se libère."""
        # D'abord, essaie de trouver une clé immédiatement disponible
        for i, key in enumerate(self.api_keys):
            if self._can_make_request(key):
                self.current_key_index = i
                return key
        
        print("⚠️  Toutes les clés API ont atteint leur limite. Attente de disponibilité...")
        
        # Aucune clé disponible, attend qu'une se libère
        while True:
            for i, key in enumerate(self.api_keys):
                if self._can_make_request(key):
                    self.current_key_index = i
                    print(f"✅ Clé API {i+1} disponible")
                    return key
            
            # Attend 1 seconde avant de revérifier
            time.sleep(1)
    
    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Méthode interne pour les requêtes GraphQL avec gestion du rate limiting."""
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Obtient une clé API disponible
                api_key = self._get_available_key()
                if not api_key:
                    print("❌ Aucune clé API disponible")
                    return None
                
                # Enregistre la requête
                self._record_request(api_key)
                
                # Fait la requête
                headers = self._get_current_headers()
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                # Gère les erreurs de rate limiting
                if response.status_code == 429:
                    print(f"⚠️  Rate limit atteint pour la clé {self.current_key_index + 1}. Changement de clé...")
                    retry_count += 1
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Erreur API (tentative {retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2 ** retry_count)  # Backoff exponentiel
                
        print("❌ Échec après toutes les tentatives")
        return None
    
    def get_rate_limit_status(self) -> Dict[str, Dict]:
        """Retourne le statut du rate limiting pour chaque clé."""
        status = {}
        now = time.time()
        
        for i, key in enumerate(self.api_keys):
            with self.locks[key]:
                history = self.request_history[key]
                # Nettoie l'historique
                while history and now - history[0] > 60:
                    history.popleft()
                
                remaining = self.max_requests_per_minute - len(history)
                next_reset = history[0] + 60 if history else now
                
                status[f"Clé {i+1}"] = {
                    "requêtes_utilisées": len(history),
                    "requêtes_restantes": remaining,
                    "prochaine_réinitialisation": time.strftime("%H:%M:%S", time.localtime(next_reset))
                }
        
        return status

    # Toutes vos méthodes existantes restent identiques, seule _make_request change
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
    
    def get_phase_matches(self, eventId: str, phase_id: str, phaseGroupId: str, state=1) -> Optional[Dict[str, Any]]:
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
                    fullRoundText
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
        variables = {"phaseId": phase_id, "phaseGroupId": phaseGroupId, "eventId": eventId, "state": state}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["event"]["phases"]
        return None
    
    def get_phase_match_for_round(self, eventId: str, phase_id: str, phaseGroupId: str) -> Optional[Dict[str, Any]]:
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
        variables = {"phaseId": phase_id, "phaseGroupId": phaseGroupId, "eventId": eventId}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["event"]["phases"][0]['sets']
        return None
    
    def update_match_score(self, set_id: str, games: list[Dict], winner_id: str) -> Optional[Dict[str, Any]]:
        """Met à jour le score d'un match avec reportBracketSet"""
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
        
        formatted_games = []
        for game in games:
            formatted_game = {
                "gameNum": game["gameNum"],
                "winnerId": game["winnerId"],
                "selections": game.get("selections", [])
            }
            formatted_games.append(formatted_game)
        
        variables = {
            "setId": set_id,
            "winnerId": winner_id,
            "gameData": games
        }
        
        response = self._make_request(query, variables)
        if response and "data" in response:
            return response["data"]["reportBracketSet"]
        return None
    
    def get_all_characters(self, id: int = 1386) -> Optional[Dict[str, Any]]:
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
        all_players = []
        for page in range(1, 100):
            variables = {"eventId": event_id, "pageNumber": page}
            response = self._make_request(query, variables)
            if response and "data" in response:
                players = response["data"]["event"]["entrants"]["nodes"]
                if not players:
                    break
                all_players.extend(players)
            else:
                return None
        return all_players if all_players else None
    
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
    
    def assign_station_to_set(self, set_id: str, station_id: str) -> Optional[Dict[str, Any]]:
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
        variables = {"tournamentId": tournament_id, "fields": {"number": station_number}}
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
    
    def mark_set_as_pending(self, set_id: str) -> Optional[Dict[str, Any]]:
        """Marque un set comme en attente."""
        query = """
        mutation MarkSetAsPending($setId: ID!) {
            markSetCalled(setId: $setId) {
                id
            }
        }
        """
        variables = {"setId": set_id}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return True
        return False
    
    def DQ_player(self, set_id: str, winner_id: str):
        """Disqualifie un joueur d'un set."""
        query = """
        mutation DisqualifyPlayer($setId: ID!, $winnerId: ID!) {
            reportBracketSet(isDQ: true , setId: $setId, winnerId: $winnerId) {
                id
            }
        }
        """
        variables = {"setId": set_id, "winnerId": winner_id}
        response = self._make_request(query, variables)
        if response and "data" in response:
            return True
        return False


# Exemple d'utilisation
if __name__ == "__main__":
    # Initialisation avec les clés depuis l'environnement
    client = StartGG()
    
    # Ou initialisation manuelle avec des clés
    # client = StartGG(["votre_cle_1", "votre_cle_2", "votre_cle_3"])
    
    # Vérifier le statut des limites
    