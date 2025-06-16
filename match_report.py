from discord.ui import Select, View, Button, TextInput, Modal
import discord

import asyncio
class WinnerSelectView(View):
    """Vue pour sélectionner le vainqueur (même pattern que les persos)"""
    def __init__(self, parent_view):
        super().__init__(timeout=60)
        self.parent_view = parent_view
        
        select = Select(
            placeholder="Qui a gagné le match ?",
            options=[
                discord.SelectOption(label=self.parent_view.player1, value="p1"),
                discord.SelectOption(label=self.parent_view.player2, value="p2")
            ]
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction):
        self.parent_view.winner = interaction.data['values'][0]
        winner_name = self.parent_view.player1 if self.parent_view.winner == "p1" else self.parent_view.player2
        
        await interaction.response.edit_message(
            content=f"✅ {winner_name} désigné comme vainqueur",
            view=None
        )
        await self.parent_view.update_main_message()

class CharacterSelector:
    def __init__(self, characters, page_size=25):
        self.all_characters = sorted(characters)
        self.page_size = page_size
        self.current_page = 0
        self.filtered_chars = self.all_characters
        
    def get_current_page(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.filtered_chars[start:end]
    
    def max_page(self):
        return (len(self.filtered_chars) // self.page_size)
    
    def apply_search(self, search_term):
        self.filtered_chars = [c for c in self.all_characters 
                             if search_term.lower() in c.lower()]
        self.current_page = 0

class CharacterSelectView(View):
    def __init__(self, selector, player_name, is_player1, parent_view):
        super().__init__(timeout=120)
        self.selector = selector
        self.player_name = player_name
        self.is_player1 = is_player1
        self.parent_view = parent_view
        self.update_view()
    
    def update_view(self):
        self.clear_items()
    
        # Modifier cette partie pour gérer le cas 0 résultat
        if not self.selector.filtered_chars:
            select = Select(
                placeholder="0 personnage disponible",
                options=[discord.SelectOption(label="Aucun résultat", value="none", default=True)],
                disabled=True  # Désactive la sélection
            )
        else:
            select = Select(
                placeholder=f"Personnage ({len(self.selector.filtered_chars)} disponibles)",
                options=[discord.SelectOption(label=c, value=c) 
                    for c in self.selector.get_current_page()]
            )
            select.callback = self.on_select
        
        self.add_item(select)
        
        # Boutons de pagination
        if self.selector.max_page() > 0:
            prev_btn = Button(emoji="⬅️", disabled=self.selector.current_page == 0)
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)
            
            page_counter = Button(
                label=f"{self.selector.current_page + 1}/{self.selector.max_page() + 1}",
                disabled=True
            )
            self.add_item(page_counter)
            
            next_btn = Button(
                emoji="➡️", 
                disabled=self.selector.current_page >= self.selector.max_page()
            )
            next_btn.callback = self.next_page
            self.add_item(next_btn)
        
        # Bouton de recherche
        search_btn = Button(emoji="🔍", style=discord.ButtonStyle.grey)
        search_btn.callback = self.show_search
        self.add_item(search_btn)

    async def on_select(self, interaction):
        selected = interaction.data['values'][0]
        if self.is_player1:
            self.parent_view.p1_char = selected
        else:
            self.parent_view.p2_char = selected
        
        # Solution corrigée :
        await interaction.response.edit_message(
                content=f"✅ {selected} sélectionné pour {self.player_name}",
                view=None,
                embed=None
            )        
        # Mettre à jour le message principal
        if hasattr(self.parent_view, 'main_message'):
            await self.parent_view.update_main_message()

    async def prev_page(self, interaction):
        self.selector.current_page = max(0, self.selector.current_page - 1)
        self.update_view()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction):
        self.selector.current_page = min(
            self.selector.max_page(), 
            self.selector.current_page + 1
        )
        self.update_view()
        await interaction.response.edit_message(view=self)

    async def show_search(self, interaction):
        modal = SearchModal(self.selector)
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.update_view()
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            view=self
        )

class SearchModal(Modal, title="Recherche de personnage"):
    search = TextInput(label="Tapez une partie du nom", required=False)

    def __init__(self, selector):
        super().__init__()
        self.selector = selector

    async def on_submit(self, interaction):
        self.selector.apply_search(self.search.value)
            
        await interaction.response.defer()


async def send_match_report(channel, player1, player2, characters):
    class MatchReportView(View):
        def __init__(self, player1, player2):
            super().__init__(timeout=3600)
            self.player1 = player1
            self.player2 = player2
            self.winner = None
            self.p1_char = None
            self.p2_char = None
            self.main_message = None
            self.completed = asyncio.Event()  # Nouveau: événement de complétion
            self.final_result = None  # Nouveau: stockage du résultat final

        async def update_main_message(self):
            """Mise à jour unique de l'embed principal"""
            if not hasattr(self, 'main_message'):
                return
            
            embed = discord.Embed(
                title=f"⚔ {self.player1} vs {self.player2}",
                color=0x00ff00 if self.winner else 0xf1c40f
            )
            
            # Personnages
            embed.add_field(name=self.player1, value=self.p1_char or "❌ Non sélectionné", inline=True)
            embed.add_field(name=self.player2, value=self.p2_char or "❌ Non sélectionné", inline=True)
            
            # Vainqueur
            if self.winner:
                winner = self.player1 if self.winner == "p1" else self.player2
                embed.add_field(name="🏆 VAINQUEUR", value=winner, inline=False)
            
            await self.main_message.edit(embed=embed)

        async def show_selector(self, interaction, player_name, is_player1):
            """Affiche le sélecteur de personnage"""
            selector = CharacterSelector(characters)
            view = CharacterSelectView(selector, player_name, is_player1, self)
            await interaction.response.send_message(
                f"Sélection du personnage pour {player_name}",
                view=view,
                ephemeral=False
            )

        async def show_winner_selector(self, interaction):
            """Affiche le sélecteur de vainqueur"""
            view = WinnerSelectView(self)
            await interaction.response.send_message(
                "Sélectionnez le gagnant du match :",
                view=view,
                ephemeral=False
            )

        @discord.ui.button(label=f"Perso {player1}", style=discord.ButtonStyle.green)
        async def select_p1(self, interaction, button):
            await self.show_selector(interaction, player1, True)

        @discord.ui.button(label=f"Perso {player2}", style=discord.ButtonStyle.red)
        async def select_p2(self, interaction, button):
            await self.show_selector(interaction, player2, False)

        @discord.ui.button(label="Choisir vainqueur", style=discord.ButtonStyle.blurple)
        async def select_winner(self, interaction, button):
            await self.show_winner_selector(interaction)
        @discord.ui.button(label="Valider", style=discord.ButtonStyle.success)
        async def submit(self, interaction, button):
            if None in [self.winner, self.p1_char, self.p2_char]:
                await interaction.response.send_message(
                    "Veuillez compléter toutes les sélections",
                    ephemeral=True
                )
                return
                
            # Préparation du résultat final
            self.final_result = {
                "p1_char": self.p1_char,
                "p2_char": self.p2_char,
                "winner": self.player1 if self.winner == "p1" else self.player2
            }
            
            # Confirmation visuelle
            embed = discord.Embed(
                title="🎉 Résultat enregistré !",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
            
            # Déclencher l'événement de complétion
            self.completed.set()
            self.stop()

    # Création de la vue
    view = MatchReportView(player1, player2)
    
    # Envoi du message initial
    embed = discord.Embed(
        title=f"⚔ {player1} vs {player2}",
        description="Configurez le match:",
        color=0x3498db
    )
    view.main_message = await channel.send(embed=embed, view=view)
    
    # Attente active de la complétion
    await view.completed.wait()
    
    # Retourne les résultats finaux
    return view.final_result
       


