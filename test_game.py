import pytest

import game


class TestScoring:
    def test_one_of_each(self):
        hand = [3, 5, 1, 4, 2, 6]
        assert game.score_hand(hand).combos == [game.OneOfEach()]

    def test_three_pairs(self):
        hand = [2, 2, 4, 4, 6, 6]
        assert game.score_hand(hand).combos == [game.ThreePairs()]

        hand = [4, 4, 4, 4, 6, 6]
        assert game.score_hand(hand).combos != [game.ThreePairs()]

    def test_no_scoring(self):
        hand = [2, 3, 4, 6, 2, 6]
        assert game.score_hand(hand).combos == [game.NoScoringDice()]

        hand = [2, 3, 4, 6, 2]
        assert game.score_hand(hand).combos != [game.NoScoringDice()]

    def test_combos(self):
        hand = [2, 2, 2, 3, 4, 6]
        assert game.score_hand(hand).combos == [game.Group(2, 3)]

        hand = [3, 3, 3, 3, 3, 3]
        assert game.score_hand(hand).combos == [game.Group(3, 6)]

        score = game.score_hand([1, 1, 1, 6, 6, 6]).combos
        assert game.Group(1, 3) in score
        assert game.Group(6, 3) in score

    def test_singles(self):
        score = game.score_hand([1, 1, 5, 4, 3, 2]).combos
        assert game.Singles(1, 2) in score
        assert game.Singles(5, 1) in score

        score = game.score_hand([3, 1, 1, 1, 5, 5]).combos
        assert game.Singles(5, 2) in score
        assert game.Singles(1, 3) not in score

    def test_multiple(self):
        score = game.score_hand([6, 6, 6, 1, 5, 5]).combos

        assert game.Group(6, 3) in score
        assert game.Singles(1, 1) in score
        assert game.Singles(5, 2) in score

    def test_simple_scoring(self):
        assert game.OneOfEach().score() == 1500
        assert game.ThreePairs().score() == 1500
        assert game.NoScoringDice().score() == 500

    def test_group_scoring(self):
        for n in range(3, 7):
            assert game.Group(1, n).score() == 1000 * 2 ** (n - 3)

        for num in range(2, 7):
            for n in range(3, 7):
                assert game.Group(num, n).score() == num * 100 * 2 ** (n - 3)

    def test_single_scoring(self):
        assert game.Singles(1, 1).score() == 100
        assert game.Singles(1, 2).score() == 200
        assert game.Singles(5, 1).score() == 50
        assert game.Singles(5, 2).score() == 100

        with pytest.raises(ValueError):
            game.Singles(3, 1).score()
