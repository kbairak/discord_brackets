import discord

from . import db, types, visualization


class CollectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Submit Option", style=discord.ButtonStyle.primary, custom_id="submit_option"
    )
    async def submit_option(self, _: discord.ui.Button, interaction: discord.Interaction) -> None:
        assert interaction.message is not None
        await interaction.response.send_modal(AddOptionModal(interaction.message))

    @discord.ui.button(
        label="Edit Options (creator only)",
        style=discord.ButtonStyle.danger,
        custom_id="edit_options",
    )
    async def edit_options(self, _: discord.ui.Button, interaction: discord.Interaction) -> None:
        assert interaction.channel_id is not None
        tournament = await db.get_tournament_by_channel(interaction.channel_id)
        if tournament is None:
            await interaction.response.defer()
            return
        assert interaction.user is not None
        if tournament.creator_id != interaction.user.id:
            await interaction.response.send_message(
                "Only the tournament creator can edit options.", ephemeral=True
            )
            return

        current_options = await db.get_option_names(tournament.id)
        assert interaction.message is not None
        await interaction.response.send_modal(
            EditOptionsModal(tournament.id, current_options, interaction.message)
        )

    @discord.ui.button(
        label="Start tournament (creator only)",
        style=discord.ButtonStyle.danger,
        custom_id="start_tournament",
    )
    async def start_tournament(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        assert interaction.channel_id is not None
        tournament = await db.get_tournament_by_channel(interaction.channel_id)
        if tournament is None:
            await interaction.response.defer()
            return
        assert interaction.user is not None
        if tournament.creator_id != interaction.user.id:
            await interaction.response.send_message(
                "Only the tournament creator can start the tournament.", ephemeral=True
            )
            return

        options = await db.get_option_names(tournament.id)
        assert interaction.message is not None
        await interaction.response.send_modal(
            RankOptionsModal(options, tournament.id, interaction.message)
        )


class AddOptionModal(discord.ui.Modal):
    def __init__(self, message: discord.Message):
        super().__init__(title="Add option")
        self.message = message
        self.add_item(discord.ui.InputText(label="Name"))

    async def callback(self, interaction: discord.Interaction):
        name = (self.children[0].value or "").strip()
        if not name:
            await interaction.response.defer()
            return
        assert interaction.channel_id is not None
        tournament = await db.get_tournament_by_channel(interaction.channel_id)
        if tournament is None:
            await interaction.response.defer()
            return
        await db.add_option(tournament.id, name)
        await self.message.edit(content=await db.get_options_text(tournament.id))
        await interaction.response.defer()


class EditOptionsModal(discord.ui.Modal):
    def __init__(self, tournament_id: int, current_options: list[str], message: discord.Message):
        super().__init__(title="Edit Options")
        self.tournament_id = tournament_id
        self.message = message

        initial_value = "\n".join(current_options) if current_options else ""

        self.add_item(
            discord.ui.InputText(
                label="Options (one per line)",
                placeholder="Option 1\nOption 2\nOption 3",
                style=discord.InputTextStyle.long,
                max_length=2000,
                value=initial_value,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        text = (self.children[0].value or "").strip()
        option_names = [line.strip() for line in text.split("\n") if line.strip()]
        await db.edit_options(self.tournament_id, set(option_names))
        await self.message.edit(content=await db.get_options_text(self.tournament_id))
        await interaction.response.defer()


class RankOptionsModal(discord.ui.Modal):
    def __init__(self, options: list[str], tournament_id: int, message: discord.Message):
        super().__init__(title="Rank options")
        self.tournament_id = tournament_id
        self.message = message

        self.add_item(
            discord.ui.InputText(
                label="Rankings (higher=better seed, default 5)",
                placeholder="5: Option 1\n5: Option 2\n5: Option 3",
                style=discord.InputTextStyle.long,
                max_length=2000,
                value="\n".join(f"5: {option}" for option in options) if options else "",
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        # Defer immediately - starting tournament takes time
        await interaction.response.defer()

        rankings: dict[str, int] = {}
        for line in (self.children[0].value or "").split("\n"):
            if ":" not in line:
                continue
            rank_str, option_name = line.split(":", 1)
            option_name = option_name.strip()
            try:
                rank = int(rank_str.strip())
            except ValueError:
                continue
            rankings[option_name] = rank

        await db.start(self.tournament_id, rankings)
        await self.message.edit(view=None)  # Remove the buttons
        state = await db.get_state(self.tournament_id)
        poll_ids = []
        await interaction.followup.send(
            f":tada: Tournament started! {state.rounds[-1].name}", view=RoundView(state, poll_ids)
        )
        for match in state.rounds[-1].matches:
            message = await interaction.followup.send(
                poll=discord.Poll(
                    f"{match.left.name} vs {match.right.name}",
                    answers=[
                        discord.PollAnswer(match.left.name, "1️⃣"),
                        discord.PollAnswer(match.right.name, "2️⃣"),
                    ],
                    duration=24 * 30,
                )
            )
            assert message is not None
            # We are mutating this list so RoundView will be able to retrieve the mesage IDs
            poll_ids.append(message.id)


class RoundView(discord.ui.View):
    def __init__(self, state: types.Tournament, poll_ids: list[int]) -> None:
        super().__init__(timeout=None)
        self.state = state
        self.poll_ids = poll_ids

    @discord.ui.button(
        label="End round (creator only)", style=discord.ButtonStyle.danger, custom_id="end_round"
    )
    async def end_round(self, _: discord.ui.Button, interaction: discord.Interaction) -> None:
        assert interaction.channel_id is not None
        tournament = await db.get_tournament_by_channel(interaction.channel_id)
        if (
            tournament is None
            or interaction.user is None
            or tournament.creator_id != interaction.user.id
        ):
            await interaction.response.send_message(
                "Only the tournament creator can end the round.", ephemeral=True
            )
            return

        # Defer immediately - this work takes more than 3 seconds
        await interaction.response.defer()

        for match, poll_id in zip(self.state.rounds[-1].matches, self.poll_ids):
            assert isinstance(interaction.channel, discord.abc.Messageable)
            message = await interaction.channel.fetch_message(poll_id)
            assert message.poll is not None
            for answer in message.poll.answers:
                async for user in answer.voters():
                    await db.vote(
                        user.id, match.id, "left" if answer.text == match.left.name else "right"
                    )
            await message.poll.end()
        finished = await db.advance(self.state.id)
        assert interaction.message is not None
        await interaction.message.edit(view=None)  # Remove the button

        state = await db.get_state(self.state.id)

        # Generate bracket image
        bracket_image = await visualization.generate_bracket_image(self.state.id)

        if finished:
            (last_match,) = state.rounds[-1].matches
            if last_match.left.winner:
                winner = last_match.left.name
            else:
                winner = last_match.right.name
            await interaction.followup.send(
                f":tada: :tada: :tada: Tournament finished! Winner: **{winner}** :tada: :tada: "
                ":tada:",
                file=bracket_image,
            )
        else:
            poll_ids = []
            await interaction.followup.send(
                f"Next round: {state.rounds[-1].name}, options remaining: "
                f"{len(state.rounds[-1].matches) * 2}",
                view=RoundView(state, poll_ids),
                file=bracket_image,
            )
            for match in state.rounds[-1].matches:
                message = await interaction.followup.send(
                    poll=discord.Poll(
                        f"{match.left.name} vs {match.right.name}",
                        answers=[
                            discord.PollAnswer(match.left.name, "1️⃣"),
                            discord.PollAnswer(match.right.name, "2️⃣"),
                        ],
                        duration=24 * 30,
                    )
                )
                assert message is not None
                # We are mutating this list so RoundView will be able to retrieve the mesage IDs
                poll_ids.append(message.id)
