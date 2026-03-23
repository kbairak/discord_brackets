import discord
from discord.ext import commands
from database import models
from bracket import generate_bracket_image, get_winner
from .views import CollectionView, VoteView, RoundControlView


class BracketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Called when the cog is loaded - restore persistent views."""
        print("[BracketsCog] Restoring persistent views...")
        await self.restore_views()

    async def restore_views(self):
        """Restore views for active brackets and matches."""
        from database import get_db

        pool = await get_db()

        # Restore collection phase views
        async with pool.acquire() as conn:
            collection_brackets = await conn.fetch(
                "SELECT id, creator_id, message_id FROM brackets WHERE phase = 'collection' AND message_id IS NOT NULL"
            )

        for bracket in collection_brackets:
            bracket_id = bracket["id"]
            creator_id = bracket["creator_id"]
            message_id = bracket["message_id"]

            view = CollectionView(bracket_id, creator_id)
            self.bot.add_view(view, message_id=message_id)
            print(f"[BracketsCog] Restored CollectionView for bracket {bracket_id}, message {message_id}")

        # Restore voting views for active rounds
        async with pool.acquire() as conn:
            active_matches = await conn.fetch(
                """SELECT m.id, m.message_id, m.contestant_1_id, m.contestant_2_id, c1.name as c1_name, c2.name as c2_name
                   FROM matches m
                   JOIN brackets b ON m.bracket_id = b.id
                   LEFT JOIN contestants c1 ON m.contestant_1_id = c1.id
                   LEFT JOIN contestants c2 ON m.contestant_2_id = c2.id
                   WHERE b.phase LIKE 'round_%' AND m.message_id IS NOT NULL AND m.winner_id IS NULL"""
            )

        for match in active_matches:
            match_id = match["id"]
            message_id = match["message_id"]
            c1_id = match["contestant_1_id"]
            c2_id = match["contestant_2_id"]
            c1_name = match["c1_name"]
            c2_name = match["c2_name"]

            if c1_id and c2_id and c1_name and c2_name:
                view = VoteView(match_id, c1_name, c2_name, c1_id, c2_id)
                self.bot.add_view(view, message_id=message_id)
                print(f"[BracketsCog] Restored VoteView for match {match_id}, message {message_id}")

        # Restore round control views
        async with pool.acquire() as conn:
            active_rounds = await conn.fetch(
                "SELECT id, creator_id, round_control_message_id FROM brackets WHERE phase LIKE 'round_%' AND round_control_message_id IS NOT NULL"
            )

        for bracket in active_rounds:
            bracket_id = bracket["id"]
            creator_id = bracket["creator_id"]
            message_id = bracket["round_control_message_id"]

            view = RoundControlView(bracket_id, creator_id)
            self.bot.add_view(view, message_id=message_id)
            print(f"[BracketsCog] Restored RoundControlView for bracket {bracket_id}, message {message_id}")

        print(f"[BracketsCog] Restored {len(collection_brackets)} collection views, {len(active_matches)} vote views, and {len(active_rounds)} round control views")

    @discord.slash_command(
        name="brackets", description="Create a new tournament bracket"
    )
    async def create_bracket(self, ctx: discord.ApplicationContext, title: str):
        """Create a new tournament bracket."""
        if not ctx.guild or not ctx.channel:
            await ctx.respond(
                "This command can only be used in a server channel.", ephemeral=True
            )
            return

        # Check if there's already an active bracket in this channel
        existing = await models.get_active_bracket(ctx.channel.id)
        if existing:
            await ctx.respond(
                "There's already an active bracket in this channel! Complete or cancel it first.",
                ephemeral=True,
            )
            return

        # Create the bracket
        bracket_id = await models.create_bracket(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            creator_id=ctx.user.id,
            title=title,
        )

        # Send message with all buttons
        view = CollectionView(bracket_id, ctx.user.id)
        message = await ctx.respond(
            f"**{title}** - Tournament Bracket\n\n"
            f"Created by {ctx.user.mention}\n"
            f"Phase: **Collecting Contestants**\n\n"
            f"**Current Contestants (0):**\nNo contestants yet.\n\n"
            f"Click the buttons below to submit contestants!",
            view=view,
        )

        # Store message ID
        try:
            public_message = await message.original_response()  # type: ignore
            message_id = public_message.id
        except (AttributeError, discord.HTTPException):
            # Fallback - don't store message ID
            message_id = None

        if message_id is not None:
            await models.update_bracket(bracket_id, message_id=message_id)

    async def start_voting(self, interaction: discord.Interaction, bracket_id: int):
        """Start voting for the current round."""
        bracket = await models.get_bracket(bracket_id)
        if bracket is None:
            await interaction.followup.send("Bracket not found!", ephemeral=True)
            return

        current_round = bracket["current_round"]

        round_name = "Play-in Round" if current_round == 0 else f"Round {current_round}"

        await interaction.followup.send(
            f"**{round_name} begins!**\nVote on the matches below:"
        )

        # Get all matches for current round
        matches = await models.get_round_matches(bracket_id, current_round)

        for match in matches:
            c1_id = match["contestant_1_id"]
            c2_id = match["contestant_2_id"]

            # Skip empty matches or byes
            if c1_id is None and c2_id is None:
                continue

            # Handle byes
            if c1_id is None:
                c2 = await models.get_contestant(c2_id)
                if c2 is None:
                    continue
                await interaction.followup.send(f"**{c2['name']}** advances (bye)")
                await models.update_match(match["id"], winner_id=c2_id)
                continue

            if c2_id is None:
                c1 = await models.get_contestant(c1_id)
                if c1 is None:
                    continue
                await interaction.followup.send(f"**{c1['name']}** advances (bye)")
                await models.update_match(match["id"], winner_id=c1_id)
                continue

            # Both contestants present - create voting message
            c1 = await models.get_contestant(c1_id)
            c2 = await models.get_contestant(c2_id)
            if c1 is None or c2 is None:
                continue

            view = VoteView(match["id"], c1["name"], c2["name"], c1_id, c2_id)
            msg = await interaction.followup.send(
                f"**{c1['name']}** vs **{c2['name']}**", view=view
            )

            # Store the message reference so the view can update it
            view.message = msg

            # Store message ID for the match
            msg_id = getattr(msg, "id", None)
            if msg_id is not None:
                await models.update_match(match["id"], message_id=msg_id)

        # Send round control message
        control_view = RoundControlView(bracket_id, bracket["creator_id"])
        control_msg = await interaction.followup.send(
            f"When voting is complete, click below to end {round_name}:",
            view=control_view,
        )

        # Store round control message ID
        control_msg_id = getattr(control_msg, "id", None)
        if control_msg_id is not None:
            await models.update_bracket(bracket_id, round_control_message_id=control_msg_id)

    async def announce_winner(self, interaction: discord.Interaction, bracket_id: int):
        """Announce the winner of the bracket."""
        winner = await get_winner(bracket_id)
        bracket = await models.get_bracket(bracket_id)
        if bracket is None:
            await interaction.followup.send("Bracket not found!", ephemeral=True)
            return

        if winner:
            # Generate final bracket image
            bracket_image = await generate_bracket_image(bracket_id)

            await interaction.followup.send(
                f"**{bracket['title']} - COMPLETE!**\n\n"
                f"🏆 **Winner: {winner['name']}** 🏆\n\n"
                f"Congratulations!",
                file=bracket_image,
            )
        else:
            await interaction.followup.send(
                f"**{bracket['title']} - COMPLETE!**\n\nNo winner could be determined."
            )


def setup(bot):
    bot.add_cog(BracketsCog(bot))
