import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tournament(Base):
    __tablename__ = "tournament"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    creator_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column()
    finished: Mapped[bool] = mapped_column(default=False)

    options: Mapped[list["Option"]] = relationship(back_populates="tournament")
    pins: Mapped[list["Pin"]] = relationship(back_populates="tournament")


class Option(Base):
    __tablename__ = "option"
    __table_args__ = (UniqueConstraint("tournament_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"))
    name: Mapped[str] = mapped_column()
    place: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    tournament: Mapped["Tournament"] = relationship(back_populates="options")


class Match(Base):
    __tablename__ = "match"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round: Mapped[int] = mapped_column(Integer)
    left_id: Mapped[int] = mapped_column(ForeignKey("option.id"))
    right_id: Mapped[int] = mapped_column(ForeignKey("option.id"))
    winner: Mapped[str | None] = mapped_column()
    place: Mapped[int] = mapped_column()

    left: Mapped["Option"] = relationship(foreign_keys=[left_id])
    right: Mapped["Option"] = relationship(foreign_keys=[right_id])
    votes: Mapped[list["Vote"]] = relationship(back_populates="match")


class Vote(Base):
    __tablename__ = "vote"
    __table_args__ = (UniqueConstraint("match_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"))
    direction: Mapped[str] = mapped_column()
    user_id: Mapped[int] = mapped_column(BigInteger)

    match: Mapped["Match"] = relationship(back_populates="votes")


class Pin(Base):
    __tablename__ = "pin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"))
    message_id: Mapped[int] = mapped_column(BigInteger)

    tournament: Mapped["Tournament"] = relationship(back_populates="pins")
