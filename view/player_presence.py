from discord.ui import View, Button
import discord
import asyncio
from models.lang import translate

class PlayerPresenceView(View):
    """Vue pour vérifier la présence des joueurs avant le match"""
    
    def __init__(self, p1_name, p2_name, p1_discord_id, p2_discord_id, match_manager, match_info, station_number):
        super().__init__(timeout=300)  # 5 minutes
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.p1_discord_id = p1_discord_id
        self.p2_discord_id = p2_discord_id
        self.match_manager = match_manager
        self.match_info = match_info
        self.station_number = station_number
        
        # État de présence
        self.p1_present = False
        self.p2_present = False
        self.completed = asyncio.Event()
        self.result = None  # 'continue', 'dq_p1', 'dq_p2', 'dq_both'
        
        # Référence au message pour le mettre à jour
        self.message = None
        
        # Créer les boutons
        self.create_buttons()
    
    def create_buttons(self):
        """Crée les boutons de présence pour chaque joueur"""
        # Bouton pour le joueur 1
        self.p1_button = Button(
            label=translate("present_button", player=self.p1_name),
            style=discord.ButtonStyle.green,
            emoji="✅",
            custom_id="p1_present"
        )
        self.p1_button.callback = self.p1_present_callback
        self.add_item(self.p1_button)
        
        # Bouton pour le joueur 2
        self.p2_button = Button(
            label=translate("present_button", player=self.p2_name),
            style=discord.ButtonStyle.green,
            emoji="✅",
            custom_id="p2_present"
        )
        self.p2_button.callback = self.p2_present_callback
        self.add_item(self.p2_button)
    
    def update_embed(self):
        """Met à jour l'embed avec le statut actuel des joueurs"""
        embed = discord.Embed(
            title=translate("presence_check_title"),
            description=translate("presence_check_description", p1=self.p1_name, p2=self.p2_name),
            color=0xffa500  # Orange par défaut
        )
        embed.add_field(
            name=translate("time_limit_label"),
            value=translate("time_limit_value"),
            inline=False
        )
        
        # Status des joueurs avec émojis
        p1_status = "✅" if self.p1_present else "❌"
        p2_status = "✅" if self.p2_present else "❌"
        
        embed.add_field(
            name=translate("players_status_label"),
            value=f"{self.p1_name}: {p1_status}\n{self.p2_name}: {p2_status}",
            inline=False
        )
        
        # Changer la couleur si les deux joueurs sont présents
        if self.p1_present and self.p2_present:
            embed.color = 0x00ff00  # Vert
            embed.description = translate("both_players_present")
        
        return embed
    
    async def p1_present_callback(self, interaction):
        """Callback quand le joueur 1 indique sa présence"""
        # Vérifier que c'est bien le joueur 1 qui clique
        if not self.match_manager.player_can_check_presence_of_other_player:
            if interaction.user.id != self.p1_discord_id:
                await interaction.response.send_message(
                    translate("not_your_button"), 
                    ephemeral=True
                )
                return
        
        self.p1_present = True
        
        # Retirer le bouton du joueur 1
        self.remove_item(self.p1_button)
        
        # Mettre à jour l'embed et la vue
        embed = self.update_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Message de confirmation éphémère
        await interaction.followup.send(
            translate("player_confirmed_present", player=self.p1_name), 
            ephemeral=True
        )
        
        # Vérifier si les deux joueurs sont présents
        await self.check_both_present()
    
    async def p2_present_callback(self, interaction):
        """Callback quand le joueur 2 indique sa présence"""
        # Vérifier que c'est bien le joueur 2 qui clique
        if not self.match_manager.player_can_check_presence_of_other_player:
            if interaction.user.id != self.p2_discord_id :
                await interaction.response.send_message(
                    translate("not_your_button"), 
                    ephemeral=True
                )
                return
        
        self.p2_present = True
        
        # Retirer le bouton du joueur 2
        self.remove_item(self.p2_button)
        
        # Mettre à jour l'embed et la vue
        embed = self.update_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Message de confirmation éphémère
        await interaction.followup.send(
            translate("player_confirmed_present", player=self.p2_name), 
            ephemeral=True
        )
        
        # Vérifier si les deux joueurs sont présents
        await self.check_both_present()
    
    async def check_both_present(self):
        """Vérifie si les deux joueurs sont présents"""
        if self.p1_present and self.p2_present:
            self.result = 'continue'
            self.completed.set()
            self.stop()
    
    async def on_timeout(self):
        """Appelé quand le timeout de 5 minutes est atteint"""
        if self.p1_present and not self.p2_present:
            self.result = 'dq_p2'
        elif not self.p1_present and self.p2_present:
            self.result = 'dq_p1'
        else:
            # Aucun des deux n'a répondu, on DQ le joueur 2
            self.result = 'dq_p2'
        
        self.completed.set()
        self.stop()

async def check_player_presence(channel, my_match, match_manager, station_number):
    """
    Vérifie la présence des joueurs avant de commencer le match
    
    Returns:
        str: 'continue' si les deux joueurs sont présents
             'dq_p1' si le joueur 1 doit être disqualifié
             'dq_p2' si le joueur 2 doit être disqualifié
    """
    p1_id_sgg = my_match.p1['id']
    p2_id_sgg = my_match.p2['id']
    p1_name = my_match.p1['name']
    p2_name = my_match.p2['name']
    
    # Récupérer les IDs Discord
    p1_discord_id = match_manager.tournament.DiscordIdForPlayer.get(p1_id_sgg, p1_id_sgg)
    p2_discord_id = match_manager.tournament.DiscordIdForPlayer.get(p2_id_sgg, p2_id_sgg)
    
    if p1_discord_id is not None:
        p1_discord_id = int(p1_discord_id)
    if p2_discord_id is not None:   
        p2_discord_id = int(p2_discord_id)
    await channel.send(translate("match_started", p1_id=p1_discord_id, p2_id=p2_discord_id, bo=my_match.bestOf_N , round=my_match.round, eventName=match_manager.tournament.selectedEvent['name']))

    # Créer la vue de vérification de présence
    presence_view = PlayerPresenceView(
        p1_name, p2_name, 
        p1_discord_id, p2_discord_id,
        match_manager, my_match, station_number
    )
    
    # Créer l'embed initial
    embed = presence_view.update_embed()
    
    # Envoyer le message
    message = await channel.send(embed=embed, view=presence_view)
    presence_view.message = message
    
    # Attendre la complétion (présence ou timeout)
    await presence_view.completed.wait()
    
    # Mettre à jour le message final selon le résultat
    if presence_view.result == 'continue':
        embed.color = 0x00ff00  # Vert
        embed.description = translate("both_players_present")
        embed.set_field_at(1, 
            name=translate("players_status_label"),
            value=f"{p1_name}: ✅\n{p2_name}: ✅",
            inline=False
        )
    elif presence_view.result == 'dq_p1':
        embed.color = 0xff0000  # Rouge
        embed.description = translate("player_disqualified", player=p1_name)
    elif presence_view.result == 'dq_p2':
        embed.color = 0xff0000  # Rouge
        embed.description = translate("player_disqualified", player=p2_name)
    
    await message.edit(embed=embed, view=None)
    
    return presence_view.result