import discord

from models.tournament import Tournament
from view.event_selector_view import TournamentView


class TournamentModal(discord.ui.Modal):
    def __init__(self, bot=None):
        super().__init__(title="Configuration du Tournoi")
        self.bot = bot  # Stocker la référence du bot
        
        self.tournament_link = discord.ui.TextInput(
            label="Lien du tournoi",
            placeholder="https://start.gg/tournament/mon-tournoi",
            required=True,
            max_length=200
        )
        self.add_item(self.tournament_link)

    async def on_submit(self, interaction: discord.Interaction):
        """Appelé quand l'utilisateur soumet le modal"""
        await interaction.response.defer(ephemeral=True)
        
        # Récupérer et nettoyer le lien
        link = self.tournament_link.value.strip()
        link_parts = link.split("/")
        
        # Validation du lien start.gg
        if not self._is_valid_startgg_link(link_parts):
            await interaction.followup.send(
                "❌ Le lien doit être au format : `https://start.gg/tournament/nom-du-tournoi`\n"
                "Exemple : `https://start.gg/tournament/evo-2024`", 
                ephemeral=True
            )
            return
        
        # Extraire le slug du tournoi
        tournament_slug = self._extract_tournament_slug(link_parts)
        
        if not tournament_slug:
            await interaction.followup.send(
                "❌ Impossible d'extraire le nom du tournoi depuis le lien.", 
                ephemeral=True
            )
            return
        
        # Créer l'objet tournament
        tournament = Tournament(tournament_slug)
        if len(link_parts) >= 7:
            tournament.select_event_by_name(link_parts[6].strip())
        if len(link_parts) >= 9:
            tournament.select_event_phase(link_parts[8].strip())
        if len(link_parts) >= 10:
            tournament.select_pool(link_parts[9].strip())
        # Vérifications
        if tournament.id is None:
            await interaction.followup.send(
                f"❌ Tournoi '{tournament_slug}' non trouvé. Vérifiez le lien et réessayez.", 
                ephemeral=True
            )
            return
            
        if not tournament.IsAdmin:
            await interaction.followup.send(
                "❌ La clé start.gg associée doit avoir les droits admin pour gérer ce tournoi.", 
                ephemeral=True
            )
            return
        
        # Initialiser les valeurs par défaut
        self._initialize_tournament_defaults(tournament)
        
        # Créer la vue avec le tournoi ET le bot
        view = TournamentView(tournament, self.bot)
        
        # Message de succès avec informations du tournoi
        embed = discord.Embed(
            title="✅ Tournoi configuré avec succès !",
            description=f"**{tournament.name}**",
            color=0x00ff00
        )
        embed.add_field(name="🎮 Événements", value=len(tournament.events), inline=True)
        
        await interaction.followup.send(
            embed=embed,
            view=view, 
            ephemeral=True
        )

    def _is_valid_startgg_link(self, link_parts):
        """Valide le format du lien start.gg"""
        if len(link_parts) < 5:
            return False
            
        # Vérifier le protocole
        if link_parts[0] not in ['https:', 'http:']:
            return False
            
        # Vérifier le domaine (avec ou sans www)
        domain = link_parts[2].lower()
        if domain not in ['start.gg', 'www.start.gg', 'smash.gg', 'www.smash.gg']:
            return False
            
        # Vérifier la structure /tournament/
        if link_parts[3] != 'tournament':
            return False
            
        # Vérifier qu'il y a bien un slug de tournoi
        if not link_parts[4] or link_parts[4].strip() == '':
            return False
            
        return True

    def _extract_tournament_slug(self, link_parts):
        """Extrait le slug du tournoi depuis les parties du lien"""
        try:
            # Le slug est à l'index 4 : https://start.gg/tournament/MON-SLUG
            return link_parts[4].strip()
        except (IndexError, AttributeError):
            return None

    def _initialize_tournament_defaults(self, tournament):
        """Initialise les valeurs par défaut du tournoi"""
        if hasattr(tournament, 'events') and tournament.events:
            # Sélectionner le premier événement par défaut
            tournament.select_event(tournament.events[0]['id'])
            
            # Sélectionner la première phase si disponible
            if hasattr(tournament.selectedEvent, 'phases') and tournament.selectedEvent.get('phases'):
                tournament.selectedPhase = tournament.selectedEvent['phases'][0]
                
                # Initialiser les pools
                if 'pools' in tournament.selectedPhase:
                    tournament.selectedPools = tournament.selectedPhase['pools']
                elif hasattr(tournament.selectedEvent, 'pools'):
                    tournament.selectedPools = [
                        pool for pool in tournament.selectedEvent.get('pools', []) 
                        if pool.get('phaseId') == tournament.selectedPhase['id']
                    ]
                else:
                    tournament.selectedPools = []

