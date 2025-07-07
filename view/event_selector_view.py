
import discord

from models.tournament import Tournament
from view.Setup_and_bestOf_config import SetupAndBestOfConfig


class EventSelector(discord.ui.Select):
    def __init__(self, tournament: Tournament):
        # Créer les options avec gestion des valeurs par défaut
        options = []
        for i, event in enumerate(tournament.events):
            is_default = (hasattr(tournament, 'selectedEvent') and tournament.selectedEvent and str(event['id']) == str(tournament.selectedEvent['id']))
            
            options.append(discord.SelectOption(
                label=f"{event['name']} ({event['numEntrants']} participants)",
                value=str(event['id']),
                default=is_default
            ))
            
        super().__init__(
            placeholder="Sélectionnez un événement", 
            options=options
        )
        self.tournament = tournament

    async def callback(self, interaction: discord.Interaction):
        selected_event_id = self.values[0]
        
        # Trouver l'événement sélectionné
        selected_event = next((event for event in self.tournament.events if str(event['id']) == selected_event_id), None)
        if selected_event:
            self.tournament.selectedEvent = selected_event
            self.tournament.select_event(selected_event['id'])
            # Réinitialiser les sélections dépendantes
            self.tournament.selectedPhase = None
            self.tournament.selectedPools = []
            self.tournament.selectedPool = None
        
        # Créer une nouvelle vue avec les données mises à jour
        new_view = TournamentView(self.tournament, self.view.bot)  # Passer le bot
        
        await interaction.response.edit_message(
            content=f"✅ Événement sélectionné : **{selected_event['name']}**", 
            view=new_view
        )


class PhaseSelector(discord.ui.Select):
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        
        if not tournament.selectedEvent :
            print("Aucune phase disponible pour l'événement sélectionné.")
            options = [discord.SelectOption(label="Aucune phase disponible", value="none")]
            disabled = True
        else:
            options = []
            for i, phase in enumerate(tournament.selectedEvent['phases']):
                is_default = bool(
                    hasattr(tournament, 'selectedPhase') and 
                    tournament.selectedPhase and 
                    str(phase['id']) == str(tournament.selectedPhase['id'])
                )
                options.append(discord.SelectOption(
                    label=phase['name'], 
                    value=str(phase['id']),
                    default=is_default
                ))
            disabled = False
        
        super().__init__(
            placeholder="Sélectionnez une phase", 
            options=options,
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        selected_phase_id = self.values[0]
        self.tournament.select_event_phase(selected_phase_id)        
            
        new_view = TournamentView(self.tournament, self.view.bot)  # Passer le bot
        await interaction.response.edit_message(
            view=new_view
        )


class PoolSelector(discord.ui.Select):
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        selectedPhase = self.tournament.selectedPhase
       
        options = []
        if selectedPhase is None:
            print("Aucune poule disponible pour la phase sélectionnée.")
            options = [discord.SelectOption(label="Aucune poule disponible", value="none")]
            disabled = True
            super().__init__(placeholder="Aucune poule disponible", options=options, disabled=disabled)
            return
        for pool in selectedPhase.get('phaseGroups', [])['nodes']:
            is_default = bool(
                hasattr(tournament, 'selectedPoolId') and 
                tournament.selectedPoolId and 
                str(pool['id']) == str(tournament.selectedPoolId)
            )
            options.append(discord.SelectOption(
                label=pool['displayIdentifier'], 
                value=str(pool['id']),
                default=is_default
            ))
        disabled = False
    
        super().__init__(
            placeholder="Sélectionnez une poule", 
            options=options, 
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        selected_pool_id = self.values[0]
        
        if selected_pool_id != "none":
            # Trouver et stocker la pool sélectionnée
            selected_pool = next((pool for pool in self.tournament.selectedPhase['phaseGroups']['nodes'] if str(pool['id']) == selected_pool_id), None)
            if selected_pool:
                self.tournament.selectedPool = selected_pool
                self.tournament.select_pool(selected_pool_id)
            
            await interaction.response.defer(ephemeral=True)
        else:
            await interaction.response.send_message("Aucune poule disponible", ephemeral=True)


class TournamentView(discord.ui.View):
    def __init__(self, tournament: Tournament, bot=None):
        super().__init__(timeout=300)  # 5 minutes de timeout
        self.tournament = tournament
        self.bot = bot  # Stocker la référence du bot

        # Ajouter les sélecteurs
        self.add_item(EventSelector(tournament))
        self.add_item(PhaseSelector(tournament))
        self.add_item(PoolSelector(tournament))

        # Bouton de validation
        validate_button = discord.ui.Button(
            label="✅ Valider la configuration", 
            style=discord.ButtonStyle.success,
            custom_id="validate_tournament"
        )
        validate_button.callback = self.validate_configuration
        self.add_item(validate_button)

    async def validate_configuration(self, interaction: discord.Interaction):
        print("Validation de la configuration du tournoi")
        
        config_summary = []
        
        if hasattr(self.tournament, 'selectedEvent') and self.tournament.selectedEvent:
            config_summary.append(f"🎮 **Événement** : {self.tournament.selectedEvent['name']}")
        
        if hasattr(self.tournament, 'selectedPhase') and self.tournament.selectedPhase:
            config_summary.append(f"📊 **Phase** : {self.tournament.selectedPhase['name']}")
            
        if hasattr(self.tournament, 'selectedPool') and self.tournament.selectedPool:
            config_summary.append(f"🏊 **Poule** : {self.tournament.selectedPool['displayIdentifier']}")

        if not config_summary:
            await interaction.response.send_message(
                "❌ Veuillez sélectionner au moins un événement avant de valider.", 
                ephemeral=True
            )
            return
        
        # Mettre à jour la liste des joueurs
        tournament = self.tournament
        tournament._set_player_list()
        
        embed = discord.Embed(
            title="✅ Configuration du tournoi validée !",
            description="\n".join(config_summary),
            color=0x00ff00
        )
        embed.add_field(
            name="➡️ Étape suivante",
            value="Configurez maintenant les paramètres de match",
            inline=False
        )
        
        # Créer la vue de configuration des matchs
        match_config_view = SetupAndBestOfConfig(tournament, self.bot)
        
        await interaction.response.send_message(
            embed=embed,
            view=match_config_view,
            ephemeral=True
        )
        print("Configuration du tournoi validée, passage à la configuration des matchs")