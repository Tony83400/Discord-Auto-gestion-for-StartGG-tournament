from dotenv import load_dotenv
import os

translations = {
    "fr": {
        "station_assigned_log": "Station: {station} assigné au match : {match}",
        "startgg_report_error": "Erreur report start.gg: {error}",
        "event_option_label": "{name} ({numEntrants} participants)",
        "event_select_placeholder": "Sélectionnez un événement",
        "event_selected": "✅ Événement sélectionné : **{name}**",
        "no_phase_available": "Aucune phase disponible",
        "phase_select_placeholder": "Sélectionnez une phase",
        "pool_option_label": "Poule {displayIdentifier}",
        "pool_select_placeholder": "Sélectionnez une poule",
        "player_dq_no_show": "❌ {player} disqualifié pour absence, {winner} gagne le match",
        "present_button": "{player} cliquez ici si vous êtes sur le setup",
        "not_your_button": "❌ Ce n'est pas votre bouton !",
        "player_confirmed_present": "✅ {player} est présent !",
        "time_limit_label": "⏳ Temps limite pour confirmer la présence",
        "players_status_label": "Présence des joueurs",
        "both_players_present": "✅ Les deux joueurs sont présents",
        "player_disqualified": "❌ {player} disqualifié pour absence",
        "time_limit_value": "5 minutes",
        "presence_check_title": "Vérification de présence",
        "presence_check_description": "Veuillez confirmer votre présence sur le setup",
        "no_pool_available": "Aucune poule disponible",
        "validate_config_label": "✅ Valider la configuration",
        "stations_description": "Liste toutes les stations et leur statut",
        "help_description": "affiche le menu d'aide complet du bot",
        "match_status_description": "Affiche le statut du gestionnaire de matchs",
        "force_station_free_description": "Force la libération d'une station (en cas de problème)",
        "config_event_summary": "🎮 **Événement** : {name}",
        "config_phase_summary": "📊 **Phase** : {name}",
        "config_pool_summary": "🏊 **Poule** : {displayIdentifier}",
        "select_event_before_validate": "❌ Veuillez sélectionner au moins un événement avant de valider.",
        "tournament_validated_title": "✅ Configuration du tournoi validée !",
        "next_step_label": "➡️ Étape suivante",
        "next_step_value": "Configurez maintenant les paramètres de match",
        "winner_select_placeholder": "Qui a gagné le match ?",
        "winner_selected": "✅ {name} désigné comme vainqueur",
        "no_character_available": "0 personnage disponible",
        "no_result": "Aucun résultat",
        "character_select_placeholder": "Personnage ({count} disponibles)",
        "character_selected": "✅ {character} sélectionné pour {name}",
        "search_label": "Tapez une partie du nom",
        "match_title": "⚔ {p1} vs {p2}",
        "not_selected": "❌ Non sélectionné",
        "winner_label": "🏆 VAINQUEUR",
        "character_select_for": "Sélection du personnage pour {name}",
        "winner_select_label": "Sélectionnez le gagnant du match :",
        "complete_all_selections": "Veuillez compléter toutes les sélections",
        "result_saved_title": "🎉 Résultat enregistré !",
        "match_configure_desc": "Configurez le match:",
        "match_format_label": "⚔️ Format de match",
        "delete_stations_description": "supprimer toutes les stations",
        "delete_stations_done": "✅ {num_station} stations supprimées",
        "bo_format_value": "Bo{bo}",
        "winner_bracket_bo5_from": "Winner: À partir du round {round}",
        "loser_bracket_bo5_from": "Loser: À partir du round {round}", 
        "winner_bracket_always_bo3": "Winner: Toujours BO3",
        "loser_bracket_always_bo3": "Loser: Toujours BO3",
        "bo_format_custom": "Bo3/BO5",
        "setups_label": "🖥️ Setups",
        "setups_value": "{count} setups" if "{count}" != "1" else "1 setup",
        "setup_numbering_label": "🔢 Numérotation",
        "setup_numbering_value": "Setup #{first} à #{last}",
        "tournament_label": "🎮 Tournoi",
        "event_label": "📊 Événement",
        "event_value": "{name} ({numEntrants} participants)",
        "pool_label": "📅 Pool",
        "pool_value": "{phase} - {pool}",
        "launch_label": "✅ Lancer le Tournoi",
        "launch_value": "Avec la commande `/start_matches`",
        "tournament_config_log": "Tournoi configuré: Bo{bo}, {count} setups (#{first}-#{last})",
        "tournament_config_title": "Configuration du Tournoi",
        "tournament_link_label": "Lien du tournoi",
        "invalid_link_format": "❌ Le lien doit être au format : `https://start.gg/tournament/nom-du-tournoi`\nExemple : `https://start.gg/tournament/evo-2024`",
        "extract_slug_error": "❌ Impossible d'extraire le nom du tournoi depuis le lien.",
        "tournament_not_found": "❌ Tournoi '{slug}' non trouvé. Vérifiez le lien et réessayez.",
        "admin_rights_required": "❌ La clé start.gg associée doit avoir les droits admin pour gérer ce tournoi.",
        "tournament_config_success": "✅ Tournoi configuré avec succès !",
        "events_label": "🎮 Événements",
        "welcome": "Bienvenue sur {server} !",
        "setup_tournament_description": "Configure un tournoi pour la gestion automatique",
        "help": "Aide : Tapez `!aide`",
        "lang_set": "Langue passée en français !",
        "dm_not_allowed": "❌ Cette commande ne peut être utilisée que sur un serveur Discord (pas en DM).",
        "missing_role": "❌ Tu dois avoir le rôle `{role}` pour utiliser cette commande.",
        "bot_connected": "✅ Bot connecté en tant que {name}",
        "commands_synced": "✅ {count} commandes synchronisées",
        "sync_failed": "❌ Échec de la synchronisation : {error}",
        "from_this_round": "À partir de ce round {bo}",
        "never_bo5_in_bracket": "Ne jamais passer en BO5 dans le {bracket_type} bracket",
        "server_info": "🔗 Serveur: {name}",
        "bot_admin": "✅ Bot est ADMIN - Toutes permissions OK",
        "bot_not_admin": "❌ Bot n'est PAS admin\n   → Donnez la permission 'Administrateur' au rôle du bot",
        "role_configured": "✅ Rôle '{role}' configuré",
        "role_permission_error": "❌ Impossible de gérer les rôles (permission manquante)",
        "role_error": "❌ Erreur rôle: {error}",
        "bot_ready": "🔗 Bot prêt !",
        "force_refresh_description": "Force un rechargement COMPLET des matchs",
        "no_tournament": "❌ Aucun tournoi configuré.",
        "wrong_guild": "❌ Le tournoi actuel est sur un autre serveur.",
        "no_manager": "❌ Aucun gestionnaire actif.",
        "full_stop_done": "✅ **Arrêt complet terminé :**\n• Gestionnaire de matchs arrêté\n• {channels} channels supprimés\n• Toutes les listes nettoyées",
        "delete_channel_error": "Erreur lors de la suppression du channel {name}: {error}",
        "delete_permission_denied": "Permission refusée pour supprimer le channel {name}.",
        "station_freed": "🔧 Station {number} forcée à être libre",
        "station_free_error": "❌ Erreur: {error}",
        "stations_title": "🎮 Statut des Stations",
        "station_used": "🔴 Occupée",
        "station_free": "🟢 Libre",
        "match_info": "📋 {p1} vs {p2}",
        "help_title": "🆘 Aide du Bot de Tournoi",
        "help_description": "**Commandes disponibles** :",
        "help_config": "`/setup_tournament` - Configurer un nouveau tournoi\n`/start_matches` - Démarrer la gestion automatique\n`/stop_matches` - Tout arrêter et nettoyer\n`/force_refresh` - Rechargement complet (en cas de bug)",
        "help_matches": "`/match_status` - Statut global du gestionnaire\n`/list_stations` - Liste des stations et leur état",
        "help_maintenance": "`/force_station_free [n°]` - Libérer une station bloquée",
        "help_footer": "💡 Les commandes marquées nécessitent le rôle 'Tournament Admin'",
        "refresh_done": "🔄 Rechargement complet des matchs effectué",
        "pending_matches_count": "🎯 {count} matchs en attente de traitement",
        "bo3_label": "BO3 (standard)",
        "bo5_label": "BO5 (finales)",
        "custom_format_label": "Format personnalisé",
        "setup_number_config_label" : "Premier setup: #{first_setup_number}",
        "all_player_can_check_presence": "Un joueur peut check in son adversaire",
        "no_player_can_check_presence": "Un joueur ne peut pas check in son adversaire",
        "all_matches_in": "Tous les matchs en {bo}",
        "custom_format_desc": "BO3 avant certains rounds, BO5 après",
        "match_fetch_error": "❌ Erreur lors de la récupération des matchs : {error}",
        "new_matches_added": "🔄 {count} nouveaux matchs détectés et ajoutés à la file d'attente",
        "refresh_error_log": "Erreur lors du rafraîchissement des matchs : {error}",
        "refresh_error": "❌ Erreur lors du rafraîchissement des matchs : {error}",
        "match_manager_already_running": "⚠️ Le gestionnaire de matchs est déjà en cours d'exécution",
        "match_manager_started": "🚀 Gestionnaire de matchs démarré",
        "start_matches_description": "Démarre la gestion automatique des matchs",
        "stop_matches_description": "Arrête la gestion automatique des matchs et nettoie tout",
        "match_manager_stopped": "⏹️ Arrêt du gestionnaire de matchs demandé",
        "new_matches_log": "Nouveaux matchs détectés : {count}",
        "processing_loop_error_log": "Erreur dans la boucle de traitement : {error}",
        "all_matches_processed": "✅ Tous les matchs ont été traités !",
        "match_assigned": "🎮 Match assigné à la station {station} : **{p1}** vs **{p2}**",
        "match_assign_error": "❌ Erreur lors de l'assignation du match : {error}",
        "no_channel_for_match": "Aucun channel disponible pour le match",
        "match_started": "🎯 **Match commencé** - <@{p1_id}> vs <@{p2_id}> (BO{bo}) {round}",
        "game_waiting_report": "**Game {game}** - En attente du résultat...",
        "game_reported": "✅ Game {game} reporté : **{winner}** gagne",
        "match_finished": "🏆 **Match terminé !** Vainqueur : **{winner}**",
        "channel_delete_soon": "🕐 Ce channel sera supprimé dans 1 minute...",
        "game_timeout": "⌛ Temps écoulé pour ce jeu - Match en pause",
        "setup_number_invalid": "❌ Le numéro du setup doit être supérieur à 0.",
        "Setup_numbers": "Numéros du premier setup",
        "match_error": "❌ Erreur pendant le match : {error}",
        "match_error_log": "Erreur de match : {error}",
        "channel_deleted_log": "Channel station-{station} supprimé automatiquement",
        "channel_already_deleted_log": "Channel station-{station} déjà supprimé",
        "channel_delete_permission_error_log": "Pas de permission pour supprimer le channel station-{station}",
        "channel_delete_error_log": "Erreur lors de la suppression du channel station-{station} : {error}",
        "cleanup_error_log": "Erreur de nettoyage : {error}",
        "match_manager_status_title": "📊 Statut du gestionnaire de matchs",
        "setup_number_config_title": "Configuration du numéro de setup",
        "launch_tournament_label": "🚀 Lancer le tournoi",
        "finish_config_label": "✅ Terminer la configuration",
        "status_state_label": "État",
        "status_active": "🟢 Actif",
        "status_stopped": "🔴 Arrêté",
        "status_pending_matches_label": "Matchs en attente",
        "status_active_matches_label": "Matchs actifs",
        "status_station_info": "Station {station} : {p1} vs {p2}",
        "status_active_stations_label": "Stations actives",
        "status_none": "Aucun",
        "station_freed_message": "🔄 Station {station} libérée",
        "error_assigning_match": "❌ Erreur lors de l'assignation du match : {error}",
        "error_fetching_matches": "❌ Erreur lors de la récupération des matchs : {error}",
        "error_refreshing_matches": "❌ Erreur lors du rafraîchissement des matchs : {error}",
        "new_matches_console_log": "Nouveaux matchs détectés : {count}",
        "error_processing_loop": "Erreur dans la boucle de traitement : {error}",
        "status_embed_title": "📊 Statut du gestionnaire de matchs",
        "status_field_state": "État",
        "status_value_active": "🟢 Actif",
        "status_value_stopped": "🔴 Arrêté",
        "status_field_pending_matches": "Matchs en attente",
        "status_field_active_matches": "Matchs actifs",
        "status_field_active_stations": "Stations actives",
        "search_modal_title": "Recherche de personnage",
        "select_winner": "Sélectionner le vainqueur",
        "validate": "Valider",
    },
    "en": {
        "station_assigned_log": "Station: {station} assigned to match: {match}",
        "startgg_report_error": "start.gg report error: {error}",
        "event_option_label": "{name} ({numEntrants} entrants)",
        "event_select_placeholder": "Select an event",
        "event_selected": "✅ Event selected: **{name}**",
        "no_phase_available": "No phase available",
        "phase_select_placeholder": "Select a phase",
        "pool_option_label": "Pool {displayIdentifier}",
        "pool_select_placeholder": "Select a pool",
        "no_pool_available": "No pool available",
        "validate_config_label": "✅ Validate Configuration",
        "config_event_summary": "🎮 **Event**: {name}",
        "config_phase_summary": "📊 **Phase**: {name}",
        "config_pool_summary": "🏊 **Pool**: {displayIdentifier}",
        "select_event_before_validate": "❌ Please select at least one event before validating.",
        "tournament_validated_title": "✅ Tournament configuration validated!",
        "setup_tournament_description": "Configure a tournament for automatic management",
        "start_matches_description": "Start automatic match management",
        "next_step_label": "➡️ Next step",
        "stop_matches_description": "Stop automatic match management and clean everything up",
        "match_status_description": "Display the status of the match manager",
        "next_step_value": "Now configure match settings",
        "winner_select_placeholder": "Who won the match?",
        "winner_selected": "✅ {name} designated as winner",
        "no_character_available": "0 character available",
        "no_result": "No result",
        "character_select_placeholder": "Character ({count} available)",
        "character_selected": "✅ {character} selected for {name}",
        "search_label": "Type part of the name",
        "match_title": "⚔ {p1} vs {p2}",
        "not_selected": "❌ Not selected",
        "never_bo5_in_bracket": "Never switch to BO5 in the {bracket_type} bracket",
        "force_station_free_description": "Force the release of a station (in case of issues)",
        "stations_description": "List all stations and their status",
        "winner_label": "🏆 WINNER",
        "character_select_for": "Character selection for {name}",
        "winner_select_label": "Select the match winner:",
        "complete_all_selections": "Please complete all selections",
        "result_saved_title": "🎉 Result saved!",
        "match_configure_desc": "Configure the match:",
        "finish_config_label": "✅ Finish Configuration",
        "match_format_label": "⚔️ Match format",
        "bo_format_value": "Bo{bo}",
        "bo_format_custom": "Bo3/BO5",
        "setups_label": "🖥️ Setups",
        "setups_value": "{count} setups" if "{count}" != "1" else "1 setup",
        "setup_numbering_label": "🔢 Numbering",
        "setup_numbering_value": "Setup #{first} to #{last}",
        "tournament_label": "🎮 Tournament",
        "event_label": "📊 Event",
        "event_value": "{name} ({numEntrants} entrants)",
        "from_this_round": "From this round {bo}",
        "setup_number_config_label" : "First setup: #{first_setup_number}",
        "pool_label": "📅 Pool",
        "pool_value": "{phase} - {pool}",
        "launch_label": "✅ Launch Tournament",
        "launch_value": "With the command `/start_matches`",
        "tournament_config_log": "Tournament configured: Bo{bo}, {count} setups (#{first}-#{last})",
        "tournament_config_title": "Tournament Configuration",
        "tournament_link_label": "Tournament Link",
        "invalid_link_format": "❌ The link must be in the format: `https://start.gg/tournament/tournament-name`\nExample: `https://start.gg/tournament/evo-2024`",
        "extract_slug_error": "❌ Unable to extract tournament name from link.",
        "tournament_not_found": "❌ Tournament '{slug}' not found. Check the link and try again.",
        "admin_rights_required": "❌ The associated start.gg key must have admin rights to manage this tournament.",
        "tournament_config_success": "✅ Tournament configured successfully!",
        "events_label": "🎮 Events",
        "all_player_can_check_presence": "Players can check in each other's presence",
        "no_player_can_check_presence": "Players can't check in each other's presence",
        "player_dq_no_show": "❌ {player} disqualified for no-show, {winner} wins the match",
        "present_button": "{player} click here if you are at the setup",
        "not_your_button": "❌ This is not your button!",
        "player_confirmed_present": "✅ {player} is present!",
        "time_limit_label": "⏳ Time limit to confirm presence",
        "players_status_label": "Player Presence",
        "both_players_present": "✅ Both players are present",
        "player_disqualified": "❌ {player} disqualified for no-show",
        "time_limit_value": "5 minutes",
        "presence_check_title": "Presence Check",
        "presence_check_description": "Please confirm your presence at the setup",
        "winner_bracket_bo5_from": "Winner: From round {round}",
        "loser_bracket_bo5_from": "Loser: From round {round}", 
        "winner_bracket_always_bo3": "Winner: Always BO3",
        "loser_bracket_always_bo3": "Loser: Always BO3",
        "welcome": "Welcome to {server}!",
        "help": "Help: Type `!help`",
        "lang_set": "Language switched to English!",
        "dm_not_allowed": "❌ This command can only be used in a server (not in DM).",
        "missing_role": "❌ You must have the `{role}` role to use this command.",
        "bot_connected": "✅ Bot connected as {name}",
        "commands_synced": "✅ {count} commands synced",
        "sync_failed": "❌ Sync failed: {error}",
        "server_info": "🔗 Server: {name}",
        "bot_admin": "✅ Bot is ADMIN - All permissions OK",
        "bot_not_admin": "❌ Bot is NOT admin\n   → Give the bot role the 'Administrator' permission",
        "role_configured": "✅ Role '{role}' configured",
        "role_permission_error": "❌ Cannot manage roles (missing permission)",
        "role_error": "❌ Role error: {error}",
        "bot_ready": "🔗 Bot ready!",
        "Setup_numbers": "First setup numbers",
        "no_tournament": "❌ No tournament configured.",
        "wrong_guild": "❌ The current tournament is on another server.",
        "no_manager": "❌ No active manager.",
        "full_stop_done": "✅ **Complete stop finished:**\n• Match manager stopped\n• {channels} channels deleted\n• All lists cleared",
        "delete_stations_description": "delete all stations",
        "delete_stations_done": "✅ {num_station} stations deleted",
        "delete_channel_error": "Error deleting channel {name}: {error}",
        "delete_permission_denied": "Permission denied to delete channel {name}.",
        "station_freed": "🔧 Station {number} forcibly freed",
        "station_free_error": "❌ Error: {error}",
        "stations_title": "🎮 Station Status",
        "station_used": "🔴 Occupied",
        "station_free": "🟢 Free",
        "match_info": "📋 {p1} vs {p2}",
        "help_title": "🆘 Tournament Bot Help",
        "help_description": "**Available commands**:",
        "help_config": "`/setup_tournament` - Configure a new tournament\n`/start_matches` - Start automatic handling\n`/stop_matches` - Stop everything and clean up\n`/force_refresh` - Full refresh (if bug)",
        "help_matches": "`/match_status` - Match manager global status\n`/list_stations` - List stations and their state",
        "help_maintenance": "`/force_station_free [n°]` - Free a stuck station",
        "help_footer": "💡 Commands marked require the 'Tournament Admin' role",
        "refresh_done": "🔄 Full match list refresh done",
        "pending_matches_count": "🎯 {count} matches pending processing",
        "bo3_label": "BO3 (standard)",
        "bo5_label": "BO5 (finals)",
        "custom_format_label": "Custom format",
        "all_matches_in": "All matches in {bo}",
        "custom_format_desc": "BO3 before some rounds, BO5 after",
        "match_fetch_error": "❌ Error fetching matches: {error}",
        "new_matches_added": "🔄 {count} new matches detected and added to the queue",
        "refresh_error_log": "Error refreshing matches: {error}",
        "refresh_error": "❌ Error refreshing matches: {error}",
        "match_manager_already_running": "⚠️ Match manager is already running",
        "match_manager_started": "🚀 Match manager started",
        "match_manager_stopped": "⏹️ Match manager stop requested",
        "new_matches_log": "New matches detected: {count}",
        "processing_loop_error_log": "Error in processing loop: {error}",
        "all_matches_processed": "✅ All matches have been processed!",
        "match_assigned": "🎮 Match assigned to station {station}: **{p1}** vs **{p2}**",
        "match_assign_error": "❌ Error assigning match: {error}",
        "no_channel_for_match": "No channel available for the match",
        "match_started": "🎯 **Match started** - <@{p1_id}> vs <@{p2_id}> (BO{bo}) {round}",
        "game_waiting_report": "**Game {game}** - Waiting for report...",
        "game_reported": "✅ Game {game} reported: **{winner}** wins",
        "match_finished": "🏆 **Match finished!** Winner: **{winner}**",
        "channel_delete_soon": "🕐 This channel will be deleted in 1 minute...",
        "help_description": "Displays the complete help menu of the bot",
        "force_refresh_description": "Force a COMPLETE refresh of matches",
        "game_timeout": "⌛ Time expired for this game - Match paused",
        "match_error": "❌ Error during match: {error}",
        "match_error_log": "Match error: {error}",
        "channel_deleted_log": "Channel station-{station} deleted automatically",
        "channel_already_deleted_log": "Channel station-{station} already deleted",
        "channel_delete_permission_error_log": "No permission to delete channel station-{station}",
        "channel_delete_error_log": "Error deleting channel station-{station}: {error}",
        "cleanup_error_log": "Cleanup error: {error}",
        "match_manager_status_title": "📊 Match Manager Status",
        "setup_number_config_title": "Setup Number Configuration",
        "setup_number_invalid": "❌ The setup number must be greater than 0.",
        "status_state_label": "State",
        "status_active": "🟢 Active",
        "status_stopped": "🔴 Stopped",
        "status_pending_matches_label": "Pending matches",
        "status_active_matches_label": "Active matches",
        "status_station_info": "Station {station}: {p1} vs {p2}",
        "status_active_stations_label": "Active stations",
        "status_none": "None",
        "station_freed_message": "🔄 Station {station} freed",
        "error_assigning_match": "❌ Error assigning match: {error}",
        "error_fetching_matches": "❌ Error fetching matches: {error}",
        "error_refreshing_matches": "❌ Error refreshing matches: {error}",
        "new_matches_console_log": "New matches detected: {count}",
        "error_processing_loop": "Error in processing loop: {error}",
        "status_embed_title": "📊 Match Manager Status",
        "status_field_state": "State",
        "status_value_active": "🟢 Active",
        "status_value_stopped": "🔴 Stopped",
        "status_field_pending_matches": "Pending matches",
        "status_field_active_matches": "Active matches",
        "status_field_active_stations": "Active stations",
        "launch_tournament_label": "🚀 Start Tournament",
        "search_modal_title": "Search Character",
        "select_winner": "Select Winner",
        "validate": "Validate",
    }
}

load_dotenv()
current_lang = os.getenv("LANG")  # Default to English if not set
print(f"Detected language from environment: {current_lang}")
if current_lang not in translations:
    current_lang = "en"  # Fallback to English if the specified language is not available
print(f"Current language set to: {current_lang}")

# 3. Fonction de traduction
def translate(key: str, **kwargs) -> str:
    """Récupère la traduction dans la langue actuelle."""
    try:
        return translations[current_lang][key].format(**kwargs)
    except KeyError:
        return f"[ERROR: Key '{key}' not found]"
