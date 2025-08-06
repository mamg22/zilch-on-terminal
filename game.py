from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterable, Generator
from dataclasses import dataclass
from enum import Enum, auto
from itertools import compress
import random
from typing import Any


@dataclass(frozen=True)
class ScoringCombo(ABC):
    @abstractmethod
    def score(self) -> int: ...


@dataclass(frozen=True)
class NoScoringDice(ScoringCombo):
    def score(self) -> int:
        return 500


@dataclass(frozen=True)
class ThreePairs(ScoringCombo):
    def score(self) -> int:
        return 1500


@dataclass(frozen=True)
class OneOfEach(ScoringCombo):
    def score(self) -> int:
        return 1500


@dataclass(frozen=True)
class Group(ScoringCombo):
    number: int
    count: int

    def score(self) -> int:
        if self.number != 1:
            base = self.number * 100
        else:
            base = 1000

        return base * 2 ** (self.count - 3)


@dataclass(frozen=True)
class Singles(ScoringCombo):
    number: int
    count: int

    def score(self) -> int:
        if self.number == 1:
            return 100 * self.count
        elif self.number == 5:
            return 50 * self.count
        else:
            raise ValueError(f"Invalid number for singles: {self.number}")


@dataclass(frozen=True)
class Scoring:
    combos: list[ScoringCombo]
    unused: int = 0

    def score(self) -> int:
        return sum(combo.score() for combo in self.combos)


def score_hand(hand: Iterable[int]) -> Scoring:
    counts = Counter(hand)
    combos = []

    if len(counts) == 6:
        return Scoring([OneOfEach()])
    elif len(counts) == 3 and all(num == 2 for num in counts.values()):
        return Scoring([ThreePairs()])
    for num, count in filter(lambda it: it[1] >= 3, counts.items()):
        combos.append(Group(num, count))
    if 1 in counts and counts[1] <= 2:
        combos.append(Singles(1, counts[1]))
    if 5 in counts and counts[5] <= 2:
        combos.append(Singles(5, counts[5]))
    if not combos and counts.total() == 6:
        return Scoring([NoScoringDice()])

    used_dice = sum(
        combo.count for combo in combos if isinstance(combo, Group | Singles)
    )

    return Scoring(combos, counts.total() - used_dice)


class Player:
    name: str
    scores: list[int]
    zilch_streak: int

    def __init__(self, name: str) -> None:
        self.name = name
        self.scores = []
        self.zilch_streak = 0

    def add_score(self, score: int) -> bool:
        if score == 0:
            self.zilch_streak += 1
        else:
            self.zilch_streak = 0

        if self.zilch_streak < 3:
            self.scores.append(score)
            return False
        else:
            self.scores.append(-300)
            self.zilch_streak = 0
            return True


class State(Enum):
    TurnStart = auto()
    TurnSelect = auto()
    TurnResult = auto()


class Game:
    dice: list[int]
    used: set[int]
    picks: set[int]
    state: State
    cumulative_score: int

    players: list[Player]
    current_player: Player
    previous_player: Player

    SCORE_LIMIT = 10000
    BANK_MIN = 300

    def __init__(self, players: Iterable[Player]) -> None:
        self.dice = [1] * 6
        self.used = set()
        self.picks = set()
        self.state = State.TurnStart

        self.cumulative_score = 0
        self.players = list(players)
        self.current_player = self.players[0]
        self.previous_player = self.players[-1]

    def roll(self) -> None:
        for idx, die in enumerate(self.dice):
            if idx in self.used:
                continue
            self.dice[idx] = random.randint(1, 6)

    def step(self, data: dict[str, Any] = {}) -> dict[str, Any]:
        results = {}

        match self.state:
            case State.TurnStart:
                self.roll()
                self.state = State.TurnSelect

            case State.TurnSelect:
                if (
                    self.used
                    and not score_hand(map(lambda e: e[1], self.usable_dice())).combos
                ):
                    results["zilch"] = True
                    results["score"] = self.cumulative_score
                    results["player_switch"] = True
                    self.used = set()
                    self.picks = set()
                    self.state = State.TurnStart
                    self.cumulative_score = 0

                    if self.current_player.add_score(0):
                        results["triple_zilch"] = True
                    self.next_player()

                    return results

                self.state = State.TurnResult

            case State.TurnResult:
                hand = score_hand(
                    compress(
                        self.dice, [n in self.picks for n in range(len(self.dice))]
                    )
                )
                score = hand.score()

                if hand.unused > 0:
                    results["unused"] = hand.unused
                    self.state = State.TurnSelect
                elif data.get("bank"):
                    new_score = self.cumulative_score + score
                    if new_score < self.BANK_MIN:
                        results["banked"] = None
                        self.state = State.TurnSelect
                    else:
                        self.cumulative_score = new_score

                        results["banked"] = self.cumulative_score
                        results["player_switch"] = True
                        self.current_player.add_score(self.cumulative_score)
                        self.next_player()

                        self.picks = set()
                        self.used = set()
                        self.cumulative_score = 0
                        self.state = State.TurnStart
                else:
                    if score == 0:
                        results["score"] = None
                        self.state = State.TurnSelect
                    else:
                        results["score"] = score
                        self.cumulative_score += score
                        self.used |= self.picks
                        self.picks = set()

                        if len(self.used) == 6:
                            results["freeroll"] = True
                            self.used = set()

                        self.state = State.TurnStart

        return results

    def usable_dice(self) -> Generator[tuple[int, int]]:
        for idx, die in enumerate(self.dice):
            if idx not in self.used:
                yield idx, die

    def pick(self, pick: int) -> None:
        self.picks.add(pick)

    def unpick(self, pick: int) -> None:
        self.picks.remove(pick)

    def toggle_pick(self, pick: int) -> None:
        if pick in self.picks:
            self.picks.remove(pick)
        else:
            self.picks.add(pick)

    def next_player(self):
        current_idx = self.players.index(self.current_player)
        self.previous_player = self.current_player
        self.current_player = self.players[(current_idx + 1) % len(self.players)]
