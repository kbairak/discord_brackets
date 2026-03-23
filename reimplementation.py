import itertools
import random

# Tournament:
# - id
# - guild_id
# - channel_id
# - creator_id
# - title
#
# Option:
# - id
# - tournament_id
# - name
# - place
# - UNIQUE(tournament_id, name)
#
# Match:
# - id
# - round
# - left_id
# - right_id
# - winner: left/right/null
#
# Vote:
# - id
# - match_id
# - direction: left/right
# - user_id
# - UNIQUE(match_id, user_id)


async def create_tournament(creator_id: int, guild_id: int, channel_id: int, title: str) -> None:
    async with AsyncSession() as session, session.begin():
        session.add(
            models.Tournament(
                guild_id=guild_id,
                channel_id=channel_id,
                creator_id=creator_id,
                title=title,
            )
        )


async def add_option(tournament_id: int, name: str) -> None:
    async with AsyncSession() as session, session.begin():
        try:
            session.add(models.Option(tournament_id=tournament_id, name=name))
        except IntegrityError:
            pass


async def edit_options(user_id: int, tournament_id: int, options: set[str]) -> None:
    async with AsyncSession() as session, session.begin():
        if not await session.scalar(
            select(
                exists().where(Tournament.id == tournament_id, Tournament.creator_id == user_id)
            )
        ):
            raise ValueError("Tournament not found or user is not the creator")
        existing = {
            option.name: option.id
            for option in await session.execute(
                select(models.Option).where(models.Option.tournament_id == tournament_id)
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


async def start(user_id: int, tournament_id: int) -> None:
    async with AsyncSession() as session, session.begin():
        if not await session.scalar(
            select(
                exists().where(Tournament.id == tournament_id, Tournament.creator_id == user_id)
            )
        ):
            raise ValueError("Tournament not found or user is not the creator")
        options = (
            await session.execute(
                select(models.Option).where(models.Option.tournament_id == tournament_id)
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
        for i in itertools.count():
            if 2**i > len(options):
                tournament_size = 2 ** (i - 1)
                break

        play_in_size = (len(options) - tournament_size) * 2

        if play_in_size:
            for i in range(len(options) - play_in_size, len(options), 2):
                session.add(
                    models.Match(round=0, left_id=options[i].id, right_id=options[i + 1].id)
                )
        else:
            for i in range(0, len(options), 2):
                session.add(
                    models.Match(round=1, left_id=options[i].id, right_id=options[i + 1].id)
                )


async def vote(user_id: int, match_id: int, direction: Literal["left"] | Literal["right"]) -> None:
    async with AsyncSession() as session, session.begin():
        await session.execute(
            insert(models.Vote)
            .values(match_id=match_id, user_id=user_id, direction=direction)
            .on_conflict_do_update(
                index_elements=["match_id", "user_id"], set_={"direction": direction}
            )
        )


async def advance(user_id: int, tournament_id: int) -> None:
    async with AsyncSession() as session, session.begin():
        if not await session.scalar(
            select(
                exists().where(Tournament.id == tournament_id, Tournament.creator_id == user_id)
            )
        ):
            raise ValueError("Tournament not found or user is not the creator")

        # Need to find options that have never been in a match because of potential play-in round
        unplayed_options = (
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
            .scalars()
            .all()
        )

        matches = await session.execute(
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
            return

        for i in range(0, len(new_options), 2):
            session.add(
                models.Match(
                    round=matches[0].round + 1,
                    left_id=new_options[i].id,
                    right_id=new_options[i + 1].id,
                )
            )


# Classes used to render the tournament
@dataclass
class Tournament:
    rounds: list[Round] = []


@dataclass
class Round:
    name: str
    matches: list[Match] = []


@dataclass
class Match:
    left: Option
    right: Option


@dataclass
class Option:
    name: str
    votes: int | None
    winner: bool = False
    advanced_from: Match | None = None


async def get_ui(tournament_id: int):
    ui_tournament = ui.Tournament()
    async with AsyncSession() as session, session.begin():
        db_matches = await session.execute(
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
        ).all()
        last_round_index = db_matches[-1][0].round

        for round_index, round_db_matches in itertools.groupby(db_matches, lambda m: m[0].round):
            current_ui_round = ui.Round(
                name="Play-in round" if round_index == 0 else f"Round {round_index}"
            )
            for db_match, left_vote_count, right_vote_count in round_db_matches:
                is_last = db_match.round == last_round_index
                current_ui_match = ui.Match(
                    left=ui.Option(
                        name=db_match.left.name,
                        votes=left_vote_count if not is_last else None,
                        winner=db_match.winner == "left",
                    ),
                    right=ui.Option(
                        name=db_match.right.name,
                        votes=right_vote_count if not is_last else None,
                        winner=db_match.winner == "right",
                    ),
                )
                try:
                    previous_round = ui_tournament.rounds[-1]
                except IndexError:
                    pass
                else:
                    for previous_match in previous_round.matches:
                        if current_ui_match.left.name in (
                            previous_match.left.name,
                            previous_match.right.name,
                        ):
                            current_ui_match.left.advanced_from = previous_match
                        if current_ui_match.right.name in (
                            previous_match.left.name,
                            previous_match.right.name,
                        ):
                            current_ui_match.right.advanced_from = previous_match
                current_ui_round.matches.append(current_ui_match)
            ui_tournament.rounds.append(current_ui_round)

    return ui_tournament
