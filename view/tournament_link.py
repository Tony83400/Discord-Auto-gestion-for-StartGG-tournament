import discord
from models.lang import translate
from models.tournament import Tournament
from view.event_selector_view import TournamentView


class TournamentNumberSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 6)
        ]
        super().__init__(
            placeholder=translate("select_number_of_tournaments"),
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        self.view.number_of_tournaments = int(self.values[0])
        self.view.stop()
    # Modifier le message original pour le faire disparaître
        try:
            await interaction.delete_original_response()
        except (discord.NotFound, discord.Forbidden):
            pass


class TournamentNumberView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.number_of_tournaments = 1  # Valeur par défaut
        self.add_item(TournamentNumberSelect())


class TournamentModal(discord.ui.Modal):
    def __init__(self, bot=None):
        title = translate("tournament_config_title")
        label = translate("tournament_link_label")
        super().__init__(title=title)
        self.bot = bot
        self.tournament_link = discord.ui.TextInput(
            label=label,
            placeholder="https://start.gg/tournament/mon-tournoi",
            required=True,
            max_length=200
        )
        self.add_item(self.tournament_link)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        link = self.tournament_link.value.strip()
        link_parts = link.split("/")
        
        if not self._is_valid_startgg_link(link_parts):
            await interaction.followup.send(
                translate("invalid_link_format"),
                ephemeral=True
            )
            return
        
        tournament_slug = self._extract_tournament_slug(link_parts)
        
        if not tournament_slug:
            await interaction.followup.send(
                translate("extract_slug_error"),
                ephemeral=True
            )
            return
        
        tournament = Tournament(tournament_slug)
        if len(link_parts) >= 7:
            tournament.select_event_by_name(link_parts[6].strip())
        if len(link_parts) >= 9:
            tournament.select_event_phase(link_parts[8].strip())
        if len(link_parts) >= 10:
            tournament.select_pool(link_parts[9].strip())
            
        if tournament.id is None:
            await interaction.followup.send(
                translate("tournament_not_found", slug=tournament_slug),
                ephemeral=True
            )
            return
            
        if not tournament.IsAdmin:
            await interaction.followup.send(
                translate("admin_rights_required"),
                ephemeral=True
            )
            return
        
        self._initialize_tournament_defaults(tournament)
        
        # Étape 1: Demander le nombre de tournois
        number_view = TournamentNumberView()
        await interaction.followup.send(
            translate("select_number_of_tournaments_prompt"),
            view=number_view,
            ephemeral=True
        )
        await number_view.wait()
        number_of_tournaments = number_view.number_of_tournaments
        
        # Étape 2: Créer la vue de configuration avec le nombre choisi
        config_view = TournamentView(
            tournament=tournament,
            pool_number=number_of_tournaments,
            bot=self.bot
        )
        
        embed = discord.Embed(
            title=translate("tournament_config_success"),
            description=f"**{tournament.name}**",
            color=0x00ff00
        )
        embed.add_field(
            name=translate("events_label"),
            value=len(tournament.events),
            inline=True
        )
        embed.add_field(
            name=translate("number_of_tournaments"),
            value=number_of_tournaments,
            inline=True
        )
        
        await interaction.followup.send(
            embed=embed,
            view=config_view, 
            ephemeral=True
        )

    def _is_valid_startgg_link(self, link_parts):
        if len(link_parts) < 5:
            return False
        if link_parts[0] not in ['https:', 'http:']:
            return False
        domain = link_parts[2].lower()
        if domain not in ['start.gg', 'www.start.gg', 'smash.gg', 'www.smash.gg']:
            return False
        if link_parts[3] != 'tournament':
            return False
        if not link_parts[4] or link_parts[4].strip() == '':
            return False
        return True

    def _extract_tournament_slug(self, link_parts):
        try:
            return link_parts[4].strip()
        except (IndexError, AttributeError):
            return None

    def _initialize_tournament_defaults(self, tournament):
        if hasattr(tournament, 'events') and tournament.events:
            tournament.select_event(tournament.events[0]['id'])
            if hasattr(tournament.selectedEvent, 'phases') and tournament.selectedEvent.get('phases'):
                tournament.selectedPhase = tournament.selectedEvent['phases'][0]
                if 'pools' in tournament.selectedPhase:
                    tournament.selectedPools = tournament.selectedPhase['pools']
                elif hasattr(tournament.selectedEvent, 'pools'):
                    tournament.selectedPools = [
                        pool for pool in tournament.selectedEvent.get('pools', []) 
                        if pool.get('phaseId') == tournament.selectedPhase['id']
                    ]
                else:
                    tournament.selectedPools = []