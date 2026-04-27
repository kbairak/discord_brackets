from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Tournament:
    id: int
    rounds: list[Round] = field(default_factory=list)


@dataclass
class Round:
    name: str
    matches: list[Match] = field(default_factory=list)


@dataclass
class Match:
    id: int
    left: Option
    right: Option
    place: int


@dataclass
class Option:
    name: str
    votes: int | None
    winner: bool = False
    advanced_from: int | None = None
