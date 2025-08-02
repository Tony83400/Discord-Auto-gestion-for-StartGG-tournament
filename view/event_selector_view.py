

import discord
from models.lang import translate
from models.tournament import Tournament
from view.Setup_and_bestOf_config import SetupAndBestOfConfig


class EventSelector(discord.ui.Select):
    def __init__(self, tournament: Tournament , pool_number: int):
        # Créer les options avec gestion des valeurs par défaut
        options = []
        for i, event in enumerate(tournament.events):
            is_default = (hasattr(tournament, 'selectedEvent') and tournament.selectedEvent and str(event['id']) == str(tournament.selectedEvent['id']))
            options.append(discord.SelectOption(
                label=translate("event_option_label", name=event['name'], numEntrants=event['numEntrants']),
                value=str(event['id']),
                default=is_default
            ))
        super().__init__(
            placeholder=translate("event_select_placeholder"),
            options=options
        )
        self.tournament = tournament
        self.pool_number = pool_number

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
        new_view = TournamentView(tournament=self.tournament, bot=self.view.bot , pool_number=self.pool_number)  # Passer le bot
        
        await interaction.response.edit_message(
            content=translate("event_selected", name=selected_event['name']),
            view=new_view
        )


class PhaseSelector(discord.ui.Select):
    def __init__(self, tournament: Tournament , pool_number: int):
        self.tournament = tournament
        self.pool_number = pool_number
        if not tournament.selectedEvent :
            print(translate("no_phase_available"))
            options = [discord.SelectOption(label=translate("no_phase_available"), value="none")]
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
            placeholder=translate("phase_select_placeholder"),
            options=options,
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        selected_phase_id = self.values[0]
        self.tournament.select_event_phase(selected_phase_id)        
            
        new_view = TournamentView(tournament= self.tournament,bot= self.view.bot , pool_number= self.pool_number)  # Passer le bot
        await interaction.response.edit_message(
            view=new_view
        )


class PoolSelector(discord.ui.Select):
    def __init__(self, tournament: Tournament ):
        self.tournament = tournament
        selectedPhase = self.tournament.selectedPhase
        options = []
        if selectedPhase is None:
            print(translate("no_pool_available"))
            options = [discord.SelectOption(label=translate("no_pool_available"), value="none")]
            disabled = True
            super().__init__(placeholder=translate("no_pool_available"), options=options, disabled=disabled)
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
            placeholder=translate("pool_select_placeholder"),
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
            await interaction.response.send_message(translate("no_pool_available"), ephemeral=True)


class TournamentView(discord.ui.View):
    def __init__(self, tournament: Tournament,pool_number : int, bot=None):
        super().__init__(timeout=300)  # 5 minutes de timeout
        self.tournament = tournament
        self.pool_number = pool_number
        self.bot = bot  # Stocker la référence du bot

        # Ajouter les sélecteurs
        self.add_item(EventSelector(tournament , pool_number))
        self.add_item(PhaseSelector(tournament , pool_number))
        self.add_item(PoolSelector(tournament ))

        # Bouton de validation
        validate_button = discord.ui.Button(
            label=translate("validate_config_label"),
            style=discord.ButtonStyle.success,
            custom_id="validate_tournament"
        )
        validate_button.callback = self.validate_configuration
        self.add_item(validate_button)

    async def validate_configuration(self, interaction: discord.Interaction):
        
        config_summary = []
        
        if hasattr(self.tournament, 'selectedEvent') and self.tournament.selectedEvent:
            config_summary.append(translate("config_event_summary", name=self.tournament.selectedEvent['name']))

        if hasattr(self.tournament, 'selectedPhase') and self.tournament.selectedPhase:
            config_summary.append(translate("config_phase_summary", name=self.tournament.selectedPhase['name']))

        if hasattr(self.tournament, 'selectedPool') and self.tournament.selectedPool:
            config_summary.append(translate("config_pool_summary", displayIdentifier=self.tournament.selectedPool['displayIdentifier']))

        if not config_summary:
            await interaction.response.send_message(
                translate("select_event_before_validate"),
                ephemeral=True
            )
            return
        
        # Mettre à jour la liste des joueurs
        tournament = self.tournament
        tournament._set_player_list()
        
        embed = discord.Embed(
            title=translate("tournament_validated_title"),
            description="\n".join(config_summary),
            color=0x00ff00
        )
        embed.add_field(
            name=translate("next_step_label"),
            value=translate("next_step_value"),
            inline=False
        )
        
        # Créer la vue de configuration des matchs
        match_config_view = SetupAndBestOfConfig(tournament, self.bot, pool_number=self.pool_number)
        
        await interaction.response.send_message(
            embed=embed,
            view=match_config_view,
            ephemeral=True
        )
        