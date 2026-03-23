import functools
import itertools
import os
import random
from collections.abc import Awaitable, Callable
from typing import Concatenate, Literal

from sqlalchemy import case, delete, exists, func, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import aliased, joinedload

from . import models, types

# Database setup
engine = create_async_engine(os.environ["DATABASE_URL"])


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


def with_session[**P, R](
    func: Callable[Concatenate[AsyncSession, P], Awaitable[R]],
) -> Callable[P, Awaitable[R]]:

    @functools.wraps(func)
    async def decorated(*args: P.args, **kwargs: P.kwargs) -> R:
        async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
            return await func(session, *args, **kwargs)

    return decorated


# Read-only
@with_session
async def tournament_exists_in_channel(
    session: AsyncSession, guild_id: int, channel_id: int
) -> bool:
    return bool(
        await session.scalar(
            select(
                exists().where(
                    models.Tournament.guild_id == guild_id,
                    models.Tournament.channel_id == channel_id,
                    models.Tournament.finished.is_(False),
                )
            )
        )
    )


@with_session
async def get_tournament_by_channel(
    session: AsyncSession, channel_id: int
) -> models.Tournament | None:
    return (
        (
            await session.execute(
                select(models.Tournament).where(
                    models.Tournament.channel_id == channel_id,
                    models.Tournament.finished.is_(False),
                )
            )
        )
        .scalars()
        .one_or_none()
    )


@with_session
async def get_options_text(session: AsyncSession, tournament_id: int) -> str:
    tournament = (
        (
            await session.execute(
                select(models.Tournament).where(
                    models.Tournament.id == tournament_id, models.Tournament.finished.is_(False)
                )
            )
        )
        .scalars()
        .one()
    )
    options = (
        await session.execute(
            select(models.Option)
            .where(models.Option.tournament_id == tournament_id)
            .order_by(models.Option.place, models.Option.created_at)
        )
    ).scalars()
    options_text = (
        "Options:\n" + "\n".join(f"- {option.name}" for option in options)
        if options
        else "No options yet."
    )
    return (
        f":crossed_swords: :crossed_swords: :crossed_swords: Tournament started: "
        f"**{tournament.title} :crossed_swords: :crossed_swords: :crossed_swords:**\n\n"
        f"{options_text}\n"
    )


@with_session
async def get_option_names(session: AsyncSession, tournament_id: int) -> list[str]:
    """Get list of option names for a tournament, ordered by creation time."""
    options = await session.execute(
        select(models.Option.name)
        .where(models.Option.tournament_id == tournament_id)
        .order_by(models.Option.created_at)
    )
    return list(options.scalars().all())


@with_session
async def get_state(session: AsyncSession, tournament_id: int) -> types.Tournament:
    db_matches = (
        await session.execute(
            select(
                models.Match,
                func.count(case((models.Vote.direction == "left", 1))).label("left_vote_count"),
                func.count(case((models.Vote.direction == "right", 1))).label("right_vote_count"),
            )
            .outerjoin(models.Vote)
            .options(joinedload(models.Match.left), joinedload(models.Match.right))
            .join(models.Match.left)
            .where(models.Option.tournament_id == tournament_id)
            .group_by(models.Match.id)
            .order_by(models.Match.round)
        )
    ).all()
    last_round_index = db_matches[-1][0].round

    ui_tournament = types.Tournament(id=tournament_id)
    for round_index, round_db_matches in itertools.groupby(db_matches, lambda m: m[0].round):
        is_last = round_index == last_round_index
        if round_index == 0:
            round_name = "Play-in round"
        elif is_last:
            round_name = "Final"
        else:
            round_name = f"Round {round_index}"

        ui_tournament.rounds.append(ui_round := types.Round(name=round_name))

        for db_match, left_vote_count, right_vote_count in round_db_matches:
            ui_round.matches.append(
                ui_match := types.Match(
                    id=db_match.id,
                    left=types.Option(
                        name=db_match.left.name,
                        votes=left_vote_count if not is_last else None,
                        winner=db_match.winner == "left",
                    ),
                    right=types.Option(
                        name=db_match.right.name,
                        votes=right_vote_count if not is_last else None,
                        winner=db_match.winner == "right",
                    ),
                )
            )

            try:
                previous_round = ui_tournament.rounds[-2]
            except IndexError:
                pass
            else:
                for i, previous_match in enumerate(previous_round.matches):
                    previous_match_names = (previous_match.left.name, previous_match.right.name)
                    if ui_match.left.name in previous_match_names:
                        ui_match.left.advanced_from = i
                    if ui_match.right.name in previous_match_names:
                        ui_match.right.advanced_from = i

    return ui_tournament


# Mutations
@with_session
async def create_tournament(
    session: AsyncSession, creator_id: int, guild_id: int, channel_id: int, title: str
) -> int:
    session.add(
        result := models.Tournament(
            guild_id=guild_id,
            channel_id=channel_id,
            creator_id=creator_id,
            title=title,
        )
    )
    print(
        f"Tournament created: {title} in guild {guild_id}, channel {channel_id} by user "
        f"{creator_id}"
    )
    await session.flush()  # Ensure ID is generated before commit
    return result.id


@with_session
async def add_option(session: AsyncSession, tournament_id: int, name: str) -> None:
    try:
        session.add(models.Option(tournament_id=tournament_id, name=name))
        print(f"Option added: {name} to tournament {tournament_id}")
    except IntegrityError:
        pass


@with_session
async def edit_options(session: AsyncSession, tournament_id: int, options: set[str]) -> None:
    existing = {
        option.name: option.id
        for option in (
            await session.execute(
                select(models.Option).where(models.Option.tournament_id == tournament_id)
            )
        )
        .scalars()
        .all()
    }

    to_delete = [option_id for name, option_id in existing.items() if name not in options]
    await session.execute(delete(models.Option).where(models.Option.id.in_(to_delete)))

    to_add = [
        models.Option(tournament_id=tournament_id, name=name)
        for name in options
        if name not in existing
    ]
    session.add_all(to_add)
    print("Mass-edited options")


@with_session
async def start(session: AsyncSession, tournament_id: int) -> None:
    options = list(
        (
            await session.execute(
                select(models.Option).where(models.Option.tournament_id == tournament_id)
            )
        )
        .scalars()
        .all()
    )

    if len(options) < 2:
        raise ValueError("Not enough options to start the tournament")

    random.shuffle(options)
    for i, option in enumerate(options):
        option.place = i

    # need to find the largest power of two less or equal to the number of options
    tournament_size = 0
    for i in itertools.count():
        if 2**i > len(options):
            tournament_size = 2 ** (i - 1)
            break

    play_in_size = (len(options) - tournament_size) * 2

    if play_in_size:
        for i in range(len(options) - play_in_size, len(options), 2):
            session.add(models.Match(round=0, left_id=options[i].id, right_id=options[i + 1].id))
    else:
        for i in range(0, len(options), 2):
            session.add(models.Match(round=1, left_id=options[i].id, right_id=options[i + 1].id))
    print("Tournament started")


@with_session
async def vote(
    session: AsyncSession,
    user_id: int,
    match_id: int,
    direction: Literal["left"] | Literal["right"],
) -> None:
    await session.execute(
        insert(models.Vote)
        .values(match_id=match_id, user_id=user_id, direction=direction)
        .on_conflict_do_update(
            index_elements=["match_id", "user_id"], set_={"direction": direction}
        )
    )


@with_session
async def advance(session: AsyncSession, tournament_id: int) -> bool:
    if not await session.scalar(
        select(
            exists().where(
                models.Tournament.id == tournament_id, models.Tournament.finished.is_(False)
            )
        )
    ):
        raise ValueError("Tournament not found")

    # Need to find options that have never been in a match because of potential play-in round
    unplayed_options = list(
        (
            await session.execute(
                select(models.Option)
                .outerjoin(
                    left_match := aliased(models.Match),
                    left_match.left_id == models.Option.id,
                )
                .outerjoin(
                    right_match := aliased(models.Match),
                    right_match.right_id == models.Option.id,
                )
                .where(
                    models.Option.tournament_id == tournament_id,
                    left_match.id.is_(None),
                    right_match.id.is_(None),
                )
                .order_by(models.Option.place)
            )
        )
        .scalars()
        .all()
    )

    matches = (
        await session.execute(
            select(
                models.Match,
                func.count(case((models.Vote.direction == "left", 1))).label("left_vote_count"),
                func.count(case((models.Vote.direction == "right", 1))).label("right_vote_count"),
            )
            .outerjoin(models.Vote)
            .options(joinedload(models.Match.left), joinedload(models.Match.right))
            .join(models.Match.left)
            .where(
                models.Option.tournament_id == tournament_id,
                models.Match.winner.is_(None),
            )
            .group_by(models.Match.id)
            .order_by(models.Option.place)
        )
    ).all()

    winners: list[models.Option] = []
    for match, left_vote_count, right_vote_count in matches:
        if left_vote_count > right_vote_count:
            match.winner = "left"
        elif right_vote_count > left_vote_count:
            match.winner = "right"
        else:
            match.winner = random.choice(["left", "right"])

        if match.winner == "left":
            winners.append(match.left)
        else:
            winners.append(match.right)

    new_options = unplayed_options + winners

    if len(new_options) <= 1:
        await session.execute(
            update(models.Tournament)
            .where(models.Tournament.id == tournament_id)
            .values(finished=True)
        )
        print("Tournament finished")
        return True

    for i in range(0, len(new_options), 2):
        session.add(
            models.Match(
                round=matches[0][0].round + 1,
                left_id=new_options[i].id,
                right_id=new_options[i + 1].id,
            )
        )
        print("Tournament advanced")
    return False
