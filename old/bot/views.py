from typing import cast

import discord
from database import models


class SubmitContestantModal(discord.ui.Modal):
    def __init__(self, bracket_id: int, collection_message: discord.Message):
        super().__init__(title="Submit Contestant")
        self.bracket_id = bracket_id
        self.collection_message = collection_message

        self.add_item(
            discord.ui.InputText(
                label="Contestant Name",
                placeholder="Enter the contestant name...",
                max_length=100,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user:
            return

        value = self.children[0].value
        if not value:
            await interaction.response.send_message(
                "Contestant name cannot be empty!", ephemeral=True
            )
            return

        contestant_name = value.strip()
        if contestant_name:
            await models.add_contestant(self.bracket_id, contestant_name, interaction.user.id)
            await interaction.response.send_message(
                f"Added contestant: **{contestant_name}** (submitted by {interaction.user.mention})",
                ephemeral=True,
            )

            # Update the collection message with the current contestant list
            bracket = await models.get_bracket(self.bracket_id)
            if bracket:
                contestants = await models.get_contestants(self.bracket_id)
                contestant_list = (
                    "\n".join(f"• {c['name']}" for c in contestants)
                    if contestants
                    else "No contestants yet."
                )

                await self.collection_message.edit(
                    content=f"**{bracket['title']}** - Tournament Bracket\n\n"
                    f"Created by <@{bracket['creator_id']}>\n"
                    f"Phase: **Collecting Contestants**\n\n"
                    f"**Current Contestants ({len(contestants)}):**\n{contestant_list}\n\n"
                    f"Click the button below to submit contestants!"
                )
        else:
            await interaction.response.send_message(
                "Contestant name cannot be empty!", ephemeral=True
            )


class CollectionView(discord.ui.View):
    def __init__(self, bracket_id: int, creator_id: int):
        super().__init__(timeout=None)
        self.bracket_id = bracket_id
        self.creator_id = creator_id

    @discord.ui.button(
        label="Submit Contestant", style=discord.ButtonStyle.primary, custom_id="submit"
    )
    async def submit_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Get the message this view is attached to
        if interaction.message:
            modal = SubmitContestantModal(self.bracket_id, interaction.message)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message(
                "Error: Could not update message", ephemeral=True
            )

    @discord.ui.button(
        label="Edit Contestants", style=discord.ButtonStyle.secondary, custom_id="edit"
    )
    async def edit_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not interaction.user or interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "Only the bracket creator can edit contestants!", ephemeral=True
            )
            return

        if interaction.message:
            contestants = await models.get_contestants(self.bracket_id)
            modal = EditContestantsModal(self.bracket_id, contestants, interaction.message)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message(
                "Error: Could not update message", ephemeral=True
            )

    @discord.ui.button(
        label="Start Tournament", style=discord.ButtonStyle.success, custom_id="start_tournament"
    )
    async def start_tournament_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if not interaction.user or interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "Only the bracket creator can end the collection phase!", ephemeral=True
            )
            return

        # Check if we have at least 2 contestants
        contestants = await models.get_contestants(self.bracket_id)
        if len(contestants) < 2:
            await interaction.response.send_message(
                "You need at least 2 contestants to start a bracket!", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Disable buttons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                btn = cast(discord.ui.Button, item)
                btn.disabled = True

        await interaction.edit_original_response(view=self)

        # Import here to avoid circular imports
        from bracket import generate_bracket

        # Generate bracket
        try:
            await generate_bracket(self.bracket_id)
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        # Get the cog to start voting
        from .cog import BracketsCog

        bot = cast(discord.Bot, interaction.client)
        cog = bot.get_cog("BracketsCog") if hasattr(bot, "get_cog") else None
        if cog:
            brackets_cog = cast(BracketsCog, cog)
            await brackets_cog.start_voting(interaction, self.bracket_id)


class EditContestantsModal(discord.ui.Modal):
    def __init__(
        self,
        bracket_id: int,
        current_contestants: list,
        collection_message: discord.Message | None = None,
    ):
        super().__init__(title="Edit Contestants")
        self.bracket_id = bracket_id
        self.collection_message = collection_message

        contestant_text = "\n".join(c["name"] for c in current_contestants)

        self.add_item(
            discord.ui.InputText(
                label="Contestants (one per line)",
                placeholder="Contestant 1\nContestant 2\nContestant 3",
                value=contestant_text,
                style=discord.InputTextStyle.long,
                max_length=2000,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user:
            return

        value = self.children[0].value
        if not value:
            await interaction.response.send_message("No contestants provided!", ephemeral=True)
            return

        text = value.strip()
        names = [line.strip() for line in text.split("\n") if line.strip()]

        if len(names) < 2:
            await interaction.response.send_message(
                "You need at least 2 contestants!", ephemeral=True
            )
            return

        await models.update_contestants(self.bracket_id, names, interaction.user.id)
        await interaction.response.send_message(
            f"Updated contestants! Total: {len(names)}", ephemeral=True
        )

        # Update the collection message if provided
        if self.collection_message:
            bracket = await models.get_bracket(self.bracket_id)
            if bracket:
                contestants = await models.get_contestants(self.bracket_id)
                contestant_list = (
                    "\n".join(f"• {c['name']}" for c in contestants)
                    if contestants
                    else "No contestants yet."
                )

                await self.collection_message.edit(
                    content=f"**{bracket['title']}** - Tournament Bracket\n\n"
                    f"Created by <@{bracket['creator_id']}>\n"
                    f"Phase: **Collecting Contestants**\n\n"
                    f"**Current Contestants ({len(contestants)}):**\n{contestant_list}\n\n"
                    f"Click the button below to submit contestants!"
                )


class VoteView(discord.ui.View):
    def __init__(
        self,
        match_id: int,
        contestant_1_name: str,
        contestant_2_name: str,
        contestant_1_id: int,
        contestant_2_id: int,
    ):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.message: discord.Message | None = None

        # Add buttons for each contestant
        self.add_item(VoteButton(contestant_1_name, contestant_1_id, match_id, row=0))
        self.add_item(VoteButton(contestant_2_name, contestant_2_id, match_id, row=0))

    async def update_vote_counts(self, interaction: discord.Interaction | None = None):
        """Update button labels with current vote counts."""
        # Get message from interaction if not cached
        if not self.message and interaction and interaction.message:
            self.message = interaction.message

        if not self.message:
            return

        vote_counts = await models.get_vote_counts(self.match_id)

        for item in self.children:
            if isinstance(item, VoteButton):
                votes = vote_counts.get(item.contestant_id, 0)
                item.label = f"{item.base_name} ({votes})"

        await self.message.edit(view=self)


class VoteButton(discord.ui.Button):
    def __init__(self, name: str, contestant_id: int, match_id: int, row: int):
        super().__init__(label=f"{name} (0)", style=discord.ButtonStyle.primary, row=row)
        self.base_name = name
        self.contestant_id = contestant_id
        self.match_id = match_id

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user:
            return

        # Check if user has already voted
        existing_vote = await models.get_user_vote(self.match_id, interaction.user.id)

        if existing_vote:
            # User already voted - update their vote
            if existing_vote["contestant_id"] == self.contestant_id:
                # Clicking same option - just acknowledge
                await interaction.response.defer()
                return

            await models.update_vote(self.match_id, interaction.user.id, self.contestant_id)
        else:
            # New vote
            success = await models.add_vote(self.match_id, interaction.user.id, self.contestant_id)
            if not success:
                await interaction.response.send_message("Failed to record vote!", ephemeral=True)
                return

        # Acknowledge the interaction
        await interaction.response.defer()

        # Update vote counts on the original message
        if self.view and isinstance(self.view, VoteView):
            await self.view.update_vote_counts(interaction)


class RoundControlView(discord.ui.View):
    def __init__(self, bracket_id: int, creator_id: int):
        super().__init__(timeout=None)
        self.bracket_id = bracket_id
        self.creator_id = creator_id

    @discord.ui.button(label="End Round", style=discord.ButtonStyle.danger, custom_id="end_round")
    async def end_round_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not interaction.user or interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "Only the bracket creator can end the round!", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Import here to avoid circular imports
        from bracket import advance_round, generate_bracket_image

        # Advance to next round
        await advance_round(self.bracket_id)

        # Disable button
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                button = cast(discord.ui.Button, item)
                button.disabled = True

        await interaction.edit_original_response(view=self)

        # Clear round control message ID since this round is ending
        await models.update_bracket(self.bracket_id, round_control_message_id=None)

        # Check if bracket is completed
        from .cog import BracketsCog

        bracket = await models.get_bracket(self.bracket_id)
        if bracket is None:
            await interaction.followup.send("Bracket not found!", ephemeral=True)
            return

        bot = cast(discord.Bot, interaction.client)
        cog = bot.get_cog("BracketsCog") if hasattr(bot, "get_cog") else None

        if bracket["phase"] == "completed":
            # Tournament is complete - announce_winner will show the image
            if cog:
                brackets_cog = cast(BracketsCog, cog)
                await brackets_cog.announce_winner(interaction, self.bracket_id)
        else:
            # More rounds to go - show bracket image and start next round
            bracket_image = await generate_bracket_image(self.bracket_id)
            await interaction.followup.send("**Round Complete!**", file=bracket_image)

            if cog:
                brackets_cog = cast(BracketsCog, cog)
                await brackets_cog.start_voting(interaction, self.bracket_id)
