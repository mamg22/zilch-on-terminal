from itertools import zip_longest

from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup
from textual.widgets import Static, Footer, Header, DataTable, Log

import game


class Die(Static):
    def __init__(self, number: int) -> None:
        super().__init__()
        self.number = number
        self.styles.border = ("round", "white")
        self.styles.width = 7

    def update_number(
        self,
    ) -> None:
        pips = [
            [
                self.number >= 4,
                self.number >= 8,
                self.number >= 2,
            ],
            [
                self.number >= 6,
                self.number % 2 == 1,
                self.number >= 6,
            ],
            [
                self.number >= 2,
                self.number >= 8,
                self.number >= 4,
            ],
        ]

        result = "\n".join(
            " ".join("●" if value else " " for value in pip_line) for pip_line in pips
        )
        self.update(result)

    def set_number(self, number: int) -> None:
        self.number = number
        self.update_number()

    def on_mount(self):
        self.update_number()


class Zot(App):
    CSS_PATH = "zot.tcss"

    BINDINGS = [
        ("1", "pick(0)", "Pick 1"),
        ("2", "pick(1)", "Pick 2"),
        ("3", "pick(2)", "Pick 3"),
        ("4", "pick(3)", "Pick 4"),
        ("5", "pick(4)", "Pick 5"),
        ("6", "pick(5)", "Pick 6"),
        ("s", "step({'bank': False})", "Step"),
        ("b", "step({'bank': True})", "Bank"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.table = DataTable()
        self.logs = Log()
        self.game = game.Game([game.Player("Player A"), game.Player("Player B")])
        self.game.step()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield HorizontalGroup(*(Die(die) for die in self.game.dice), id="dice")
        yield self.table
        yield self.logs

    def on_mount(self):
        self.table.add_columns("Round", *(player.name for player in self.game.players))
        self.update_dice()

    def action_pick(self, number: int) -> None:
        self.game.toggle_pick(number)
        self.update_dice()

    def action_step(self, arg: dict) -> None:
        result = self.game.step(arg)
        self.update_dice()
        self.update_scores()

        messages = []

        if "unused" in result:
            messages.append(f"You have {result['unused']} non-scoring dice")
        if "banked" in result:
            banked = result["banked"]

            if banked is None:
                messages.append(
                    f"Not enough points to bank out, need at least {self.game.BANK_MIN}"
                )
            else:
                messages.append(
                    f"{self.game.previous_player.name} banks {banked} points"
                )
        if "score" in result:
            score = result["score"]
            if score is None:
                messages.append("Please select some scoring dice")
            elif "zilch" in result:
                msg = "Zilched!"
                if "triple_zilch" in result:
                    msg += " Lost 300 points!"
                messages.append(msg)
            else:
                messages.append(f"Got {score} points")

        if "freeroll" in result:
            messages.append("Free roll!")
        if "player_switch" in result:
            messages.append(f"{self.game.current_player.name}'s turn!")
        self.logs.write_lines(messages, scroll_end=True)

    def update_dice(self):
        dice = self.query_one("#dice", HorizontalGroup).query(Die)

        for child, (idx, die) in zip(dice, enumerate(self.game.dice)):
            child.set_number(
                die,
            )
            child.set_class(idx in self.game.picks - self.game.used, "picked")
            child.set_class(idx in self.game.used, "used")

    def update_scores(self):
        self.table.clear()

        for round, scores in enumerate(
            zip_longest(*(player.scores for player in self.game.players)), start=1
        ):
            self.table.add_row(
                round,
                *(
                    score if score > 0 else "Zilch!"
                    for score in scores
                    if score is not None
                ),
            )


if __name__ == "__main__":
    app = Zot()
    app.run()
