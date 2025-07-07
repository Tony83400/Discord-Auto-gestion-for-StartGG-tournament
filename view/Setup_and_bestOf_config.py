
import discord

from models.tournament import Tournament


class BoSelector(discord.ui.Select):
    def __init__(self, tournament: 'Tournament'):
        # Détermine la valeur sélectionnée par défaut
        
        options = [
            discord.SelectOption(
                label="Best of 3 (tous les matchs)",
                value="3",
                description="Tous les matchs en BO3",
                emoji="3️⃣",
                default=True
            ),
            discord.SelectOption(
                label="Best of 5 (tous les matchs)",
                value="5",
                description="Tous les matchs en BO5",
                emoji="5️⃣",
                default=False
            ),
            discord.SelectOption(
                label="Format personnalisé (par round)",
                value="custom",
                description="BO3 avant certains rounds, BO5 après",
                emoji="⚙️",
                default=False
            )
        ]
        
        super().__init__(
            placeholder="Sélectionnez le format de match",
            options=options,
            custom_id="bo_selector",
            min_values=1,
            max_values=1
        )
        self.tournament = tournament

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        self.view.selected_bo = selected_value
        
        # Mettre à jour les options pour refléter la sélection
        for option in self.options:
            option.default = (option.value == selected_value)
        
        if selected_value == "custom":
            # Mode custom - afficher les sélecteurs pour winner/loser
            self.view.show_custom_selectors()
            
            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send(
                "⚙️ Configurez les rounds à partir desquels le format passe en BO5:",
                ephemeral=True
            )
        else:
            # Mode simple BO3 ou BO5 pour tous les matchs
            self.view.hide_custom_selectors()
            
            # Sauvegarde du format dans le tournoi
            self.tournament.default_bo = int(selected_value)
            self.tournament.bo_custom = False
            self.tournament.round_where_bo5_start_winner = None
            self.tournament.round_where_bo5_start_loser = None
            
            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send(
                f"✅ Format sélectionné: **Best of {selected_value}** pour tous les matchs",
                ephemeral=True
            )


class RoundBoSelector(discord.ui.Select):
    def __init__(self, tournament: 'Tournament', bracket_type: str):
        self.tournament = tournament
        self.bracket_type = bracket_type  # "winner" ou "loser"
        
        matches = tournament.get_round_of_match()
        options = []
        
        # Récupère la valeur actuellement configurée
        current_round = (tournament.round_where_bo5_start_winner if bracket_type == "winner" 
                        else tournament.round_where_bo5_start_loser)
        
        # Génère les options pour les rounds
        for match in matches:
            round_num = match['round']
            
            # Filtre selon le type de bracket
            if (bracket_type == "winner" and round_num > 0) or \
               (bracket_type == "loser" and round_num < 0):
                
                # Pour le bracket winner, on montre les rounds dans l'ordre croissant
                # Pour le loser, dans l'ordre décroissant (car rounds négatifs)
                options.append(discord.SelectOption(
                    label=match['fullRoundText'],
                    value=str(round_num),
                    description=f"À partir de ce round: BO5",
                    default=(round_num == current_round)
                ))
        
        # Option pour ne jamais passer en BO5 dans ce bracket
        never_option = discord.SelectOption(
            label=f"Toujours BO3 ({bracket_type} bracket)",
            value="0",
            description=f"Ne jamais passer en BO5 dans le {bracket_type} bracket",
            emoji="❌",
            default=(current_round is None)
        )
        
        # Insère en première position
        options.insert(0, never_option)
        
        # Trie les options selon le bracket
        if bracket_type == "winner":
            options[1:] = sorted(options[1:], key=lambda x: int(x.value))
        else:
            options[1:] = sorted(options[1:], key=lambda x: -int(x.value))
        
        super().__init__(
            placeholder=f"Round ({bracket_type}) pour BO5",
            options=options,
            custom_id=f"bo_round_{bracket_type}"
        )

    async def callback(self, interaction: discord.Interaction):
        selected_round = int(self.values[0]) if self.values[0] != "0" else None
        
        # Sauvegarde de la configuration
        if self.bracket_type == "winner":
            self.tournament.round_where_bo5_start_winner = selected_round
        else:
            self.tournament.round_where_bo5_start_loser = selected_round
        
        # Active le mode custom
        self.tournament.bo_custom = True
        self.tournament.default_bo = 3  # Par défaut BO3 avant les rounds spécifiés
        
        # Met à jour les sélections
        for option in self.options:
            option.default = ((option.value == "0" and selected_round is None) or 
                             (option.value != "0" and int(option.value) == selected_round))
        
        await interaction.response.edit_message(view=self.view)
        
        # Message de confirmation
        if selected_round is None:
            message = f"✅ Tous les matchs en {self.bracket_type} bracket resteront en BO3"
        else:
            round_name = next((m['fullRoundText'] for m in self.tournament.get_round_of_match() 
                             if m['round'] == selected_round), f"Round {abs(selected_round)}")
            message = (f"✅ Les matchs en {self.bracket_type} bracket seront en:\n"
                      f"- BO3 avant le {round_name}\n"
                      f"- BO5 à partir du {round_name} (inclus)")
        
        await interaction.followup.send(message, ephemeral=True)


class SetupCountSelector(discord.ui.Select):
    def __init__(self):
        options = []
        for i in range(1, 11):  # De 1 à 10 setups
            options.append(discord.SelectOption(
                label=f"{i} setup{'s' if i > 1 else ''}",
                value=str(i),
                default=(i == 2)  # 2 setups par défaut
            ))
        
        # Ajouter l'option personnalisée
        options.append(discord.SelectOption(
            label="Nombre personnalisé",
            value="custom",
            description="Choisir un nombre spécifique"
        ))
        
        super().__init__(
            placeholder="Nombre de setups",
            options=options,
            custom_id="setup_count_selector"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "custom":
            # Ouvrir le modal pour choisir un nombre personnalisé
            modal = CustomSetupCountModal(self.view)
            await interaction.response.send_modal(modal)
        else:
            self.view.num_setups = int(self.values[0])
            
            # Mettre à jour les options pour refléter la sélection
            for option in self.options:
                option.default = (option.value == self.values[0])
            
            await interaction.response.send_message(
                f"✅ Nombre de setups: **{self.values[0]}**",
                ephemeral=True
            )

class CustomSetupCountModal(discord.ui.Modal):
    def __init__(self, match_config_view):
        super().__init__(title="Nombre de setups personnalisé")
        self.match_config_view = match_config_view
        
        self.setup_count_input = discord.ui.TextInput(
            label="Nombre de setups",
            placeholder="Entrez le nombre de setups souhaité",
            default=str(match_config_view.num_setups),
            required=True,
            max_length=3
        )
        self.add_item(self.setup_count_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_count = int(self.setup_count_input.value)
            if new_count < 1:
                await interaction.response.send_message(
                    "❌ Le nombre de setups doit être supérieur à 0.",
                    ephemeral=True
                )
                return
            
            if new_count > 100:  # Limite raisonnable
                await interaction.response.send_message(
                    "❌ Le nombre de setups ne peut pas dépasser 100.",
                    ephemeral=True
                )
                return
            
            self.match_config_view.num_setups = new_count
            
            # Créer une nouvelle vue pour mettre à jour l'affichage
            new_view = SetupAndBestOfConfig(
                self.match_config_view.tournament,
                self.match_config_view.bot
            )
            new_view.selected_bo = self.match_config_view.selected_bo
            new_view.num_setups = self.match_config_view.num_setups
            new_view.first_setup_number = self.match_config_view.first_setup_number
            
            await interaction.response.edit_message(view=new_view)
            await interaction.followup.send(
                f"✅ Nombre de setups personnalisé: **{new_count}**",
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Veuillez entrer un nombre valide.",
                ephemeral=True
            )


class SetupNumberModal(discord.ui.Modal):
    def __init__(self, match_config_view):
        super().__init__(title="Configuration du premier setup")
        self.match_config_view = match_config_view
        
        self.setup_number_input = discord.ui.TextInput(
            label="Numéro du premier setup",
            placeholder="1",
            default=str(match_config_view.first_setup_number),
            required=True,
            max_length=3
        )
        self.add_item(self.setup_number_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_number = int(self.setup_number_input.value)
            if new_number < 1:
                await interaction.response.send_message(
                    "❌ Le numéro du setup doit être supérieur à 0.",
                    ephemeral=True
                )
                return
            
            self.match_config_view.first_setup_number = new_number
            self.match_config_view.update_setup_button_label()
            
            # Recréer la vue pour mettre à jour l'affichage
            new_view = SetupAndBestOfConfig(
                self.match_config_view.tournament,
                self.match_config_view.bot
            )
            new_view.selected_bo = self.match_config_view.selected_bo
            new_view.num_setups = self.match_config_view.num_setups
            new_view.first_setup_number = self.match_config_view.first_setup_number
            
            await interaction.response.edit_message(view=new_view)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Veuillez entrer un nombre valide.",
                ephemeral=True
            )

class SetupAndBestOfConfig(discord.ui.View):
    def __init__(self, tournament, bot):
        super().__init__(timeout=300)  # 5 minutes de timeout
        self.tournament = tournament
        self.bot = bot
        
        # Valeurs par défaut
        self.selected_bo = "3"
        self.num_setups = 2
        self.first_setup_number = 1
        self.custom_selectors_visible = False
        
        # Ajouter les composants - CHANGEMENT ICI
        self.bo_selector = BoSelector(self.tournament)
        self.winner_selector = RoundBoSelector(self.tournament, "winner")
        self.loser_selector = RoundBoSelector(self.tournament, "loser")
        
        # Ajouter seulement le sélecteur principal au départ
        self.add_item(self.bo_selector)
        self.add_item(SetupCountSelector())
        
        # Afficher les sélecteurs custom si c'est déjà configuré
        if getattr(tournament, 'bo_custom', False):
            self.show_custom_selectors()
        
        # Bouton pour configurer le numéro de premier setup
        setup_number_button = discord.ui.Button(
            label=f"Premier setup: #{self.first_setup_number}",
            style=discord.ButtonStyle.secondary,
            custom_id="setup_number_config"
        )
        setup_number_button.callback = self.configure_setup_number
        self.add_item(setup_number_button)
        
        # Bouton de validation finale
        validate_button = discord.ui.Button(
            label="🚀 Lancer le tournoi",
            style=discord.ButtonStyle.success,
            custom_id="launch_tournament"
        )
        validate_button.callback = self.launch_tournament
        self.add_item(validate_button)

    def show_custom_selectors(self):
        """Affiche les sélecteurs pour la configuration par round"""
        if not self.custom_selectors_visible:
            # Ajouter les sélecteurs après le BO selector
            self.add_item(self.winner_selector)
            self.add_item(self.loser_selector)
            self.custom_selectors_visible = True
    
    def hide_custom_selectors(self):
        """Cache les sélecteurs pour la configuration par round"""
        if self.custom_selectors_visible:
            # Supprimer les sélecteurs custom
            try:
                self.remove_item(self.winner_selector)
                self.remove_item(self.loser_selector)
                self.custom_selectors_visible = False
            except ValueError:
                # Les items ne sont pas dans la vue
                pass

    async def configure_setup_number(self, interaction: discord.Interaction):
        """Ouvre un modal pour configurer le numéro du premier setup"""
        modal = SetupNumberModal(self)
        await interaction.response.send_modal(modal)

    def update_setup_button_label(self):
        """Met à jour le label du bouton de configuration du setup"""
        for item in self.children:
            if hasattr(item, 'custom_id') and item.custom_id == "setup_number_config":
                item.label = f"Premier setup: #{self.first_setup_number}"
                break
                
    async def launch_tournament(self, interaction: discord.Interaction):
        """Lance le tournoi avec la configuration choisie"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Supprimer les anciennes stations s'il y en a
            if hasattr(self.tournament, 'stations'):
                self.tournament.stations.clear()
            
            # Créer les nouvelles stations selon la configuration
            for i in range(self.num_setups):
                setup_number = self.first_setup_number + i
                self.tournament.create_station(setup_number)
                print(f"Station {setup_number} créée avec succès")
            
            # Créer le gestionnaire de matchs avec la configuration BO
            from models.match_manager import MatchManager
            match_manager = MatchManager(self.bot, self.tournament)
            match_manager.player_list = self.tournament.DiscordIdForPlayer
            
            # Configurer le BO dans le gestionnaire (à adapter selon votre implémentation)
            if hasattr(match_manager, 'bo_format'):
                if self.selected_bo != "custom":
                    self.tournament.set_best_of(int(self.selected_bo))

                
            
            # Assigner aux variables globales du bot
            if hasattr(self.bot, 'current_tournament'):
                self.bot.current_tournament = self.tournament
            if hasattr(self.bot, 'match_manager'):
                self.bot.match_manager = match_manager
            
            # Créer l'embed de confirmation
            embed = discord.Embed(
                title="🚀 Tournoi lancé avec succès !",
                color=0x00ff00
            )
            
            embed.add_field(
                name="⚔️ Format de match",
                value=f"Bo{self.selected_bo}" if self.selected_bo != "custom" else "Format personnalisé",
                inline=True
            )
            
            embed.add_field(
                name="🖥️ Setups",
                value=f"{self.num_setups} setup(s)",
                inline=True
            )
            
            embed.add_field(
                name="🔢 Numérotation",
                value=f"Setup #{self.first_setup_number} à #{self.first_setup_number + self.num_setups - 1}",
                inline=True
            )
            
            embed.add_field(
                name="🎮 Tournoi",
                value=f"{self.tournament.name}",
                inline=False
            )
            
            if hasattr(self.tournament, 'selectedEvent') and self.tournament.selectedEvent:
                embed.add_field(
                    name="📊 Événement",
                    value=f"{self.tournament.selectedEvent['name']} ({self.tournament.selectedEvent['numEntrants']} participants)",
                    inline=False
                )
            
            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )
            
            print(f"Tournoi lancé: Bo{self.selected_bo}, {self.num_setups} setups (#{self.first_setup_number}-#{self.first_setup_number + self.num_setups - 1})")
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erreur lors du lancement du tournoi: {str(e)}",
                ephemeral=True
            )
            print(f"Erreur lors du lancement: {e}")
