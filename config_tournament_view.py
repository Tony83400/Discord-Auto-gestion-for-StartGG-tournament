import discord
from discord.ext import commands

from tournament import Tournament

class TournamentModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Configuration du Tournoi")
        
        self.tournament_link = discord.ui.TextInput(
            label="Lien du tournoi",
            placeholder="https://start.gg/tournament/mon-tournoi",
            required=True,
            max_length=200
        )
        self.add_item(self.tournament_link)

    async def on_submit(self, interaction: discord.Interaction):
        """Appelé quand l'utilisateur soumet le modal"""
        # try:
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
        print(link_parts)
        if len(link_parts) >= 7:
            tournament.select_event_by_name(link_parts[6].strip())
        if len(link_parts) >= 9:
            tournament.select_event_phase(link_parts[8].strip())
        if len(link_parts) >= 10:
            tournament.select_pool(link_parts[9].strip())
        print(link_parts)
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
        
        # Créer la vue avec le tournoi
        view = TournamentView(tournament)
        
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
            
        # except Exception as e:
        #     await interaction.followup.send(
        #         f"❌ Erreur lors de la configuration : {str(e)}", 
        #         ephemeral=True
        #     )

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
        new_view = TournamentView(self.tournament)
        
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
            # print(tournament.selectedEvent)
            # print(f"Phases disponibles pour l'événement {tournament.selectedEvent['name']}: {len(tournament.selectedEvent['phases'])}")
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
            
        new_view = TournamentView(self.tournament)
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
        print(selectedPhase.get('phaseGroups', []))
        for pool in selectedPhase.get('phaseGroups', [])['nodes']:
            print("Pool:", pool)
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
            selected_pool = next((pool for pool in self.tournament.selectedPools if str(pool['id']) == selected_pool_id), None)
            if selected_pool:
                self.tournament.selectedPool = selected_pool
            
            await interaction.response.send_message(
                f"✅ Poule sélectionnée ", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Aucune poule disponible", ephemeral=True)


class TournamentView(discord.ui.View):
    def __init__(self, tournament: Tournament):
        super().__init__(timeout=300)  # 5 minutes de timeout
        self.tournament = tournament

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
        """Valide la configuration finale du tournoi"""
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

        embed = discord.Embed(
            title="🎯 Configuration validée !",
            description="\n".join(config_summary),
            color=0x00ff00
        )
        
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    async def on_timeout(self):
        """Appelé quand la vue expire"""
        # Désactiver tous les composants
        for item in self.children:
            item.disabled = True