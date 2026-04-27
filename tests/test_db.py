"""Unit tests for discord_brackets.db module."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from discord_brackets import db, models, types


class TestReadOnly:
    """Tests for read-only database queries."""

    async def test_tournament_exists_returns_true(self):
        """Test tournament_exists_in_channel returns True for active tournament."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )

        exists = await db.tournament_exists_in_channel(guild_id=1, channel_id=100)

        assert exists is True

    async def test_tournament_exists_returns_false_no_tournament(self):
        """Test tournament_exists_in_channel returns False when no tournament exists."""
        exists = await db.tournament_exists_in_channel(guild_id=1, channel_id=100)

        assert exists is False

    async def test_tournament_exists_returns_false_finished(self):
        """Test tournament_exists_in_channel returns False for finished tournament."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )

        # Mark tournament as finished
        async with AsyncSession(db.get_engine()) as session, session.begin():
            result = await session.execute(
                select(models.Tournament).where(models.Tournament.id == tournament_id)
            )
            tournament = result.scalar_one()
            tournament.finished = True

        exists = await db.tournament_exists_in_channel(guild_id=1, channel_id=100)

        assert exists is False

    async def test_tournament_exists_different_guild(self):
        """Test tournament_exists_in_channel returns False for different guild."""
        await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )

        exists = await db.tournament_exists_in_channel(guild_id=2, channel_id=100)

        assert exists is False

    async def test_tournament_exists_different_channel(self):
        """Test tournament_exists_in_channel returns False for different channel."""
        await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )

        exists = await db.tournament_exists_in_channel(guild_id=1, channel_id=200)

        assert exists is False

    async def test_get_tournament_by_channel_exists(self):
        """Test get_tournament_by_channel returns tournament when it exists."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )

        tournament = await db.get_tournament_by_channel(channel_id=100)

        assert tournament is not None
        assert tournament.id == tournament_id
        assert tournament.title == "Test Tournament"
        assert tournament.guild_id == 1
        assert tournament.channel_id == 100
        assert tournament.creator_id == 1

    async def test_get_tournament_by_channel_none(self):
        """Test get_tournament_by_channel returns None when no tournament exists."""
        tournament = await db.get_tournament_by_channel(channel_id=100)

        assert tournament is None

    async def test_get_tournament_by_channel_ignores_finished(self):
        """Test get_tournament_by_channel ignores finished tournaments."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )

        # Mark tournament as finished
        async with AsyncSession(db.get_engine()) as session, session.begin():
            result = await session.execute(
                select(models.Tournament).where(models.Tournament.id == tournament_id)
            )
            tournament = result.scalar_one()
            tournament.finished = True

        tournament = await db.get_tournament_by_channel(channel_id=100)

        assert tournament is None

    async def test_get_tournament_by_channel_loads_pins(self):
        """Test get_tournament_by_channel loads pins relationship."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )
        await db.pin(tournament_id=tournament_id, pin_id=12345)

        tournament = await db.get_tournament_by_channel(channel_id=100)

        assert tournament is not None
        assert len(tournament.pins) == 1
        assert tournament.pins[0].message_id == 12345

    async def test_get_options_text_with_options(self):
        """Test get_options_text returns formatted text with options."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="My Tournament"
        )
        await db.add_option(tournament_id=tournament_id, name="Option A")
        await db.add_option(tournament_id=tournament_id, name="Option B")

        text = await db.get_options_text(tournament_id=tournament_id)

        assert "My Tournament" in text
        assert "Option A" in text
        assert "Option B" in text
        assert ":crossed_swords:" in text

    async def test_get_options_text_no_options(self):
        """Test get_options_text returns 'No options yet' when empty."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="My Tournament"
        )

        text = await db.get_options_text(tournament_id=tournament_id)

        assert "My Tournament" in text
        assert "No options yet" in text

    async def test_get_options_text_ordering(self):
        """Test get_options_text orders by place then created_at."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="My Tournament"
        )
        await db.add_option(tournament_id=tournament_id, name="First")
        await db.add_option(tournament_id=tournament_id, name="Second")
        await db.add_option(tournament_id=tournament_id, name="Third")

        # Set places
        async with AsyncSession(db.get_engine()) as session, session.begin():
            result = await session.execute(
                select(models.Option)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Option.created_at)
            )
            options = list(result.scalars().all())
            options[0].place = 2
            options[1].place = 0
            options[2].place = 1

        text = await db.get_options_text(tournament_id=tournament_id)

        # Should be ordered by place: Second (0), Third (1), First (2)
        second_idx = text.index("Second")
        third_idx = text.index("Third")
        first_idx = text.index("First")
        assert second_idx < third_idx < first_idx

    async def test_get_option_names_ordered(self):
        """Test get_option_names returns names in created_at order."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="My Tournament"
        )
        await db.add_option(tournament_id=tournament_id, name="First")
        await db.add_option(tournament_id=tournament_id, name="Second")
        await db.add_option(tournament_id=tournament_id, name="Third")

        names = await db.get_option_names(tournament_id=tournament_id)

        assert names == ["First", "Second", "Third"]

    async def test_get_option_names_empty(self):
        """Test get_option_names returns empty list for tournament with no options."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="My Tournament"
        )

        names = await db.get_option_names(tournament_id=tournament_id)

        assert names == []


class TestTournamentLifecycle:
    """Tests for tournament creation and option management."""

    async def test_create_tournament_returns_id(self):
        """Test create_tournament returns a valid tournament ID."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )

        assert isinstance(tournament_id, int)
        assert tournament_id > 0

    async def test_create_tournament_sets_fields(self):
        """Test create_tournament correctly stores all fields."""
        tournament_id = await db.create_tournament(
            creator_id=123, guild_id=456, channel_id=789, title="My Title"
        )

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Tournament).where(models.Tournament.id == tournament_id)
            )
            tournament = result.scalar_one()

            assert tournament.creator_id == 123
            assert tournament.guild_id == 456
            assert tournament.channel_id == 789
            assert tournament.title == "My Title"

    async def test_create_tournament_default_finished_false(self):
        """Test create_tournament sets finished to False by default."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Tournament).where(models.Tournament.id == tournament_id)
            )
            tournament = result.scalar_one()

            assert tournament.finished is False

    async def test_create_multiple_tournaments(self):
        """Test multiple tournaments can coexist."""
        id1 = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Tournament 1"
        )
        id2 = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=200, title="Tournament 2"
        )

        assert id1 != id2

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Tournament))
            tournaments = list(result.scalars().all())

            assert len(tournaments) == 2

    async def test_add_option_success(self):
        """Test add_option successfully adds an option."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        await db.add_option(tournament_id=tournament_id, name="Option A")

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Option).where(models.Option.tournament_id == tournament_id)
            )
            options = list(result.scalars().all())

            assert len(options) == 1
            assert options[0].name == "Option A"

    async def test_add_option_sets_created_at(self):
        """Test add_option sets created_at timestamp."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        await db.add_option(tournament_id=tournament_id, name="Option A")

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Option).where(models.Option.tournament_id == tournament_id)
            )
            option = result.scalar_one()

            assert option.created_at is not None

    async def test_add_option_duplicate_name_silent(self):
        """Test add_option silently ignores duplicate names in same tournament."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        await db.add_option(tournament_id=tournament_id, name="Duplicate")
        await db.add_option(tournament_id=tournament_id, name="Duplicate")

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Option).where(models.Option.tournament_id == tournament_id)
            )
            options = list(result.scalars().all())

            assert len(options) == 1

    async def test_add_option_multiple_tournaments(self):
        """Test same option name allowed in different tournaments."""
        id1 = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Tournament 1"
        )
        id2 = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=200, title="Tournament 2"
        )

        await db.add_option(tournament_id=id1, name="Same Name")
        await db.add_option(tournament_id=id2, name="Same Name")

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Option))
            options = list(result.scalars().all())

            assert len(options) == 2

    async def test_add_option_ordering(self):
        """Test options are ordered by created_at."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        await db.add_option(tournament_id=tournament_id, name="First")
        await db.add_option(tournament_id=tournament_id, name="Second")
        await db.add_option(tournament_id=tournament_id, name="Third")

        names = await db.get_option_names(tournament_id=tournament_id)

        assert names == ["First", "Second", "Third"]

    async def test_edit_options_add_new(self):
        """Test edit_options adds new options."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="Existing")

        await db.edit_options(tournament_id=tournament_id, options={"Existing", "New"})

        names = await db.get_option_names(tournament_id=tournament_id)
        assert set(names) == {"Existing", "New"}

    async def test_edit_options_remove_existing(self):
        """Test edit_options removes options not in set."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="Keep")
        await db.add_option(tournament_id=tournament_id, name="Remove")

        await db.edit_options(tournament_id=tournament_id, options={"Keep"})

        names = await db.get_option_names(tournament_id=tournament_id)
        assert names == ["Keep"]

    async def test_edit_options_mix_add_remove(self):
        """Test edit_options can add and remove in same call."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="Keep")
        await db.add_option(tournament_id=tournament_id, name="Remove")

        await db.edit_options(tournament_id=tournament_id, options={"Keep", "New"})

        names = await db.get_option_names(tournament_id=tournament_id)
        assert set(names) == {"Keep", "New"}

    async def test_edit_options_no_change(self):
        """Test edit_options with matching set is a no-op."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="A")
        await db.add_option(tournament_id=tournament_id, name="B")

        await db.edit_options(tournament_id=tournament_id, options={"A", "B"})

        names = await db.get_option_names(tournament_id=tournament_id)
        assert set(names) == {"A", "B"}

    async def test_edit_options_empty_set(self):
        """Test edit_options with empty set removes all options."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="A")
        await db.add_option(tournament_id=tournament_id, name="B")

        await db.edit_options(tournament_id=tournament_id, options=set())

        names = await db.get_option_names(tournament_id=tournament_id)
        assert names == []

    async def test_edit_options_preserves_others(self):
        """Test edit_options doesn't affect other tournaments."""
        id1 = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Tournament 1"
        )
        id2 = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=200, title="Tournament 2"
        )
        await db.add_option(tournament_id=id1, name="T1 Option")
        await db.add_option(tournament_id=id2, name="T2 Option")

        await db.edit_options(tournament_id=id1, options={"New Option"})

        names1 = await db.get_option_names(tournament_id=id1)
        names2 = await db.get_option_names(tournament_id=id2)
        assert names1 == ["New Option"]
        assert names2 == ["T2 Option"]


class TestBracketSeeding:
    """Tests for tournament start and seeding algorithm."""

    async def test_start_4_options_perfect_bracket(self):
        """Test start() with 4 options creates perfect bracket (no play-in)."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B", "C", "D"]:
            await db.add_option(tournament_id=tournament_id, name=name)

        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Match)
                .join(models.Match.left)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Match.id)
            )
            matches = list(result.scalars().all())

            assert len(matches) == 2
            assert all(match.round == 1 for match in matches)

    async def test_start_2_options_minimum(self):
        """Test start() with 2 options creates single match."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="A")
        await db.add_option(tournament_id=tournament_id, name="B")

        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Match)
                .join(models.Match.left)
                .where(models.Option.tournament_id == tournament_id)
            )
            matches = list(result.scalars().all())

            assert len(matches) == 1
            assert matches[0].round == 1

    async def test_start_5_options_play_in(self):
        """Test start() with 5 options creates play-in round."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B", "C", "D", "E"]:
            await db.add_option(tournament_id=tournament_id, name=name)

        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Match)
                .join(models.Match.left)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Match.round, models.Match.id)
            )
            matches = list(result.scalars().all())

            # 5 options: tournament_size=4, play_in_size=(5-4)*2=2, matches=2/2=1
            assert len(matches) == 1
            assert matches[0].round == 0

    async def test_start_8_options_seeding(self):
        """Test start() with 8 options uses correct seeding (#1 vs #8, #2 vs #7, etc.)."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for i in range(8):
            await db.add_option(tournament_id=tournament_id, name=f"Option{i + 1}")

        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Match, models.Option)
                .join(models.Match.left)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Match.id)
            )
            matches_with_options = list(result.all())

            # Load all matches with their left and right options
            result = await session.execute(
                select(models.Match)
                .join(models.Match.left)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Match.id)
            )
            matches = list(result.scalars().all())

            # Fetch options to check places
            result = await session.execute(
                select(models.Option)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Option.place)
            )
            options = list(result.scalars().all())

            # Verify 4 matches in round 1
            assert len(matches) == 4
            assert all(match.round == 1 for match in matches)

            # Verify seeding: option at place 0 plays option at place 7, etc.
            for match in matches:
                result_left = await session.execute(
                    select(models.Option).where(models.Option.id == match.left_id)
                )
                result_right = await session.execute(
                    select(models.Option).where(models.Option.id == match.right_id)
                )
                left = result_left.scalar_one()
                right = result_right.scalar_one()

                # Places should sum to 7 (0+7, 1+6, 2+5, 3+4)
                assert left.place + right.place == 7

    async def test_start_sets_place_values(self):
        """Test start() sets place field on all options."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B", "C", "D"]:
            await db.add_option(tournament_id=tournament_id, name=name)

        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Option)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Option.place)
            )
            options = list(result.scalars().all())

            places = [opt.place for opt in options]
            assert places == [0, 1, 2, 3]

    async def test_start_rankings_high_to_low(self):
        """Test start() seeds higher ranked options first."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="Low")
        await db.add_option(tournament_id=tournament_id, name="High")
        await db.add_option(tournament_id=tournament_id, name="Medium")
        await db.add_option(tournament_id=tournament_id, name="VeryHigh")

        rankings = {"VeryHigh": 10, "High": 8, "Medium": 5, "Low": 2}
        await db.start(tournament_id=tournament_id, rankings=rankings)

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Option)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Option.place)
            )
            options = list(result.scalars().all())

            # Should be ordered by ranking (high to low)
            names = [opt.name for opt in options]
            assert names == ["VeryHigh", "High", "Medium", "Low"]

    async def test_start_unranked_default_5(self):
        """Test start() assigns default rank 5 to unranked options."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="Ranked")
        await db.add_option(tournament_id=tournament_id, name="Unranked1")
        await db.add_option(tournament_id=tournament_id, name="Unranked2")
        await db.add_option(tournament_id=tournament_id, name="HighRanked")

        rankings = {"Ranked": 3, "HighRanked": 8}
        await db.start(tournament_id=tournament_id, rankings=rankings)

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Option)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Option.place)
            )
            options = list(result.scalars().all())

            # HighRanked (8), then Unranked1 and Unranked2 (both 5, shuffled), then Ranked (3)
            names = [opt.name for opt in options]
            assert names[0] == "HighRanked"
            assert names[3] == "Ranked"
            # Middle two are the unranked ones (order determined by random.seed(42))
            assert set(names[1:3]) == {"Unranked1", "Unranked2"}

    async def test_start_less_than_2_options_raises(self):
        """Test start() raises ValueError with fewer than 2 options."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        await db.add_option(tournament_id=tournament_id, name="Only One")

        with pytest.raises(ValueError, match="Not enough options"):
            await db.start(tournament_id=tournament_id, rankings={})

    async def test_start_zero_options_raises(self):
        """Test start() raises ValueError with zero options."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        with pytest.raises(ValueError, match="Not enough options"):
            await db.start(tournament_id=tournament_id, rankings={})


class TestVotingAndAdvancement:
    """Tests for voting and tournament advancement."""

    async def test_vote_creates_new(self):
        """Test vote() creates a new vote record."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Match).limit(1))
            match = result.scalar_one()

        await db.vote(user_id=1001, match_id=match.id, direction="left")

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Vote).where(models.Vote.match_id == match.id)
            )
            votes = list(result.scalars().all())

            assert len(votes) == 1
            assert votes[0].user_id == 1001
            assert votes[0].direction == "left"

    async def test_vote_updates_existing(self):
        """Test vote() updates existing vote from same user."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Match).limit(1))
            match = result.scalar_one()

        await db.vote(user_id=1001, match_id=match.id, direction="left")
        await db.vote(user_id=1001, match_id=match.id, direction="right")

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Vote).where(
                    models.Vote.match_id == match.id, models.Vote.user_id == 1001
                )
            )
            votes = list(result.scalars().all())

            assert len(votes) == 1
            assert votes[0].direction == "right"

    async def test_vote_multiple_users(self):
        """Test multiple users can vote on same match."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Match).limit(1))
            match = result.scalar_one()

        await db.vote(user_id=1001, match_id=match.id, direction="left")
        await db.vote(user_id=1002, match_id=match.id, direction="left")
        await db.vote(user_id=1003, match_id=match.id, direction="right")

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Vote).where(models.Vote.match_id == match.id)
            )
            votes = list(result.scalars().all())

            assert len(votes) == 3

    async def test_advance_simple_4_options(self):
        """Test advance() progresses 4-option tournament correctly."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B", "C", "D"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        # Get matches and vote
        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Match)
                .join(models.Match.left)
                .where(models.Option.tournament_id == tournament_id)
                .order_by(models.Match.id)
            )
            matches = list(result.scalars().all())

        # Vote on both matches
        await db.vote(user_id=1001, match_id=matches[0].id, direction="left")
        await db.vote(user_id=1002, match_id=matches[1].id, direction="right")

        finished = await db.advance(tournament_id=tournament_id)

        assert finished is False

        # Should have created 1 new match (final)
        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Match)
                .join(models.Match.left)
                .where(models.Option.tournament_id == tournament_id)
            )
            all_matches = list(result.scalars().all())

            assert len(all_matches) == 3  # 2 original + 1 final

    async def test_advance_sets_winner(self):
        """Test advance() sets winner field on matches."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Match).limit(1))
            match = result.scalar_one()

        await db.vote(user_id=1001, match_id=match.id, direction="left")
        await db.vote(user_id=1002, match_id=match.id, direction="left")

        await db.advance(tournament_id=tournament_id)

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Match).where(models.Match.id == match.id))
            updated_match = result.scalar_one()

            assert updated_match.winner == "left"

    async def test_advance_final_returns_true(self):
        """Test advance() returns True and sets finished when tournament ends."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Match).limit(1))
            match = result.scalar_one()

        await db.vote(user_id=1001, match_id=match.id, direction="left")

        finished = await db.advance(tournament_id=tournament_id)

        assert finished is True

        # Verify tournament marked as finished
        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Tournament).where(models.Tournament.id == tournament_id)
            )
            tournament = result.scalar_one()

            assert tournament.finished is True

    async def test_advance_finished_tournament_raises(self):
        """Test advance() raises ValueError for already finished tournament."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        # Mark as finished
        async with AsyncSession(db.get_engine()) as session, session.begin():
            result = await session.execute(
                select(models.Tournament).where(models.Tournament.id == tournament_id)
            )
            tournament = result.scalar_one()
            tournament.finished = True

        with pytest.raises(ValueError, match="Tournament not found"):
            await db.advance(tournament_id=tournament_id)

    async def test_advance_nonexistent_tournament_raises(self):
        """Test advance() raises ValueError for non-existent tournament."""
        with pytest.raises(ValueError, match="Tournament not found"):
            await db.advance(tournament_id=99999)


class TestPinManagement:
    """Tests for pin creation and management."""

    async def test_pin_creates_new(self):
        """Test pin() creates a new pin record."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        await db.pin(tournament_id=tournament_id, pin_id=12345)

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Pin).where(models.Pin.tournament_id == tournament_id)
            )
            pins = list(result.scalars().all())

            assert len(pins) == 1
            assert pins[0].message_id == 12345

    async def test_pin_removes_old_pins(self):
        """Test pin() removes old pins before creating new one."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        await db.pin(tournament_id=tournament_id, pin_id=11111)
        await db.pin(tournament_id=tournament_id, pin_id=22222)

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Pin).where(models.Pin.tournament_id == tournament_id)
            )
            pins = list(result.scalars().all())

            assert len(pins) == 1
            assert pins[0].message_id == 22222

    async def test_pin_with_none_removes_all(self):
        """Test pin() with None removes all pins."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )

        await db.pin(tournament_id=tournament_id, pin_id=12345)
        await db.pin(tournament_id=tournament_id, pin_id=None)

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Pin).where(models.Pin.tournament_id == tournament_id)
            )
            pins = list(result.scalars().all())

            assert len(pins) == 0

    async def test_pin_different_tournaments(self):
        """Test pin() doesn't affect pins from other tournaments."""
        id1 = await db.create_tournament(creator_id=1, guild_id=1, channel_id=100, title="T1")
        id2 = await db.create_tournament(creator_id=1, guild_id=1, channel_id=200, title="T2")

        await db.pin(tournament_id=id1, pin_id=11111)
        await db.pin(tournament_id=id2, pin_id=22222)
        await db.pin(tournament_id=id1, pin_id=33333)

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(
                select(models.Pin).where(models.Pin.tournament_id == id2)
            )
            pins = list(result.scalars().all())

            assert len(pins) == 1
            assert pins[0].message_id == 22222


class TestDataIntegrity:
    """Tests for full lifecycle and data integrity."""

    async def test_full_lifecycle_4_options(self):
        """Test complete tournament lifecycle with 4 options."""
        # Create tournament and add options
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test Tournament"
        )
        for name in ["Alice", "Bob", "Charlie", "Diana"]:
            await db.add_option(tournament_id=tournament_id, name=name)

        # Start tournament
        await db.start(tournament_id=tournament_id, rankings={})

        # Get first round matches
        state = await db.get_state(tournament_id=tournament_id)
        assert len(state.rounds) == 1
        assert len(state.rounds[0].matches) == 2

        # Cast votes on both matches
        match1_id = state.rounds[0].matches[0].id
        match2_id = state.rounds[0].matches[1].id

        await db.vote(user_id=1001, match_id=match1_id, direction="left")
        await db.vote(user_id=1002, match_id=match1_id, direction="left")
        await db.vote(user_id=1003, match_id=match2_id, direction="right")

        # Advance to final
        finished = await db.advance(tournament_id=tournament_id)
        assert finished is False

        # Get final match
        state = await db.get_state(tournament_id=tournament_id)
        assert len(state.rounds) == 2
        assert len(state.rounds[1].matches) == 1

        final_match_id = state.rounds[1].matches[0].id
        await db.vote(user_id=1001, match_id=final_match_id, direction="left")

        # Finish tournament
        finished = await db.advance(tournament_id=tournament_id)
        assert finished is True

        # Verify final state
        state = await db.get_state(tournament_id=tournament_id)
        assert len(state.rounds) == 2
        final_match = state.rounds[1].matches[0]
        assert final_match.left.winner or final_match.right.winner

    async def test_get_state_simple(self):
        """Test get_state() returns correct structure for simple tournament."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B", "C", "D"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        state = await db.get_state(tournament_id=tournament_id)

        assert isinstance(state, types.Tournament)
        assert state.id == tournament_id
        assert len(state.rounds) == 1
        assert state.rounds[0].name == "Round 1"
        assert len(state.rounds[0].matches) == 2

        for match in state.rounds[0].matches:
            assert isinstance(match, types.Match)
            assert isinstance(match.left, types.Option)
            assert isinstance(match.right, types.Option)
            assert match.left.votes == 0
            assert match.right.votes == 0

    async def test_get_state_with_votes(self):
        """Test get_state() correctly tallies votes."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Match).limit(1))
            match = result.scalar_one()

        # Cast votes: 2 left, 1 right
        await db.vote(user_id=1001, match_id=match.id, direction="left")
        await db.vote(user_id=1002, match_id=match.id, direction="left")
        await db.vote(user_id=1003, match_id=match.id, direction="right")

        state = await db.get_state(tournament_id=tournament_id)

        match_state = state.rounds[0].matches[0]
        assert match_state.left.votes == 2
        assert match_state.right.votes == 1

    async def test_get_state_play_in_round_naming(self):
        """Test get_state() names play-in round correctly."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B", "C", "D", "E"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        state = await db.get_state(tournament_id=tournament_id)

        assert state.rounds[0].name == "Play-in round"

    async def test_get_state_final_naming(self):
        """Test get_state() names final round correctly."""
        tournament_id = await db.create_tournament(
            creator_id=1, guild_id=1, channel_id=100, title="Test"
        )
        for name in ["A", "B", "C", "D"]:
            await db.add_option(tournament_id=tournament_id, name=name)
        await db.start(tournament_id=tournament_id, rankings={})

        # Vote and advance to final
        async with AsyncSession(db.get_engine()) as session:
            result = await session.execute(select(models.Match).order_by(models.Match.id))
            matches = list(result.scalars().all())

        await db.vote(user_id=1001, match_id=matches[0].id, direction="left")
        await db.vote(user_id=1002, match_id=matches[1].id, direction="right")
        await db.advance(tournament_id=tournament_id)

        state = await db.get_state(tournament_id=tournament_id)

        assert state.rounds[-1].name == "Final"
