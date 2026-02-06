"""Tests for selection and highlight data types."""

import pytest

from pysolitaire.cursor import CursorZone
from pysolitaire.selection import HighlightedDestinations, Selection


class TestSelectionCreation:
    """Tests for Selection data structure."""

    def test_selection_with_zone_only(self):
        sel = Selection(zone=CursorZone.WASTE)
        assert sel.zone == CursorZone.WASTE
        assert sel.pile_index == 0
        assert sel.card_index == 0

    def test_selection_with_all_fields(self):
        sel = Selection(zone=CursorZone.TABLEAU, pile_index=3, card_index=2)
        assert sel.zone == CursorZone.TABLEAU
        assert sel.pile_index == 3
        assert sel.card_index == 2

    @pytest.mark.parametrize("zone", [
        CursorZone.STOCK,
        CursorZone.WASTE,
        CursorZone.FOUNDATION,
        CursorZone.TABLEAU,
    ])
    def test_selection_accepts_all_zones(self, zone: CursorZone):
        sel = Selection(zone=zone)
        assert sel.zone == zone

    def test_selection_equality(self):
        sel1 = Selection(zone=CursorZone.TABLEAU, pile_index=2, card_index=1)
        sel2 = Selection(zone=CursorZone.TABLEAU, pile_index=2, card_index=1)
        assert sel1 == sel2

    def test_selection_inequality_different_zone(self):
        sel1 = Selection(zone=CursorZone.WASTE)
        sel2 = Selection(zone=CursorZone.FOUNDATION)
        assert sel1 != sel2

    def test_selection_inequality_different_pile(self):
        sel1 = Selection(zone=CursorZone.TABLEAU, pile_index=0)
        sel2 = Selection(zone=CursorZone.TABLEAU, pile_index=1)
        assert sel1 != sel2

    def test_selection_inequality_different_card(self):
        sel1 = Selection(zone=CursorZone.TABLEAU, pile_index=0, card_index=0)
        sel2 = Selection(zone=CursorZone.TABLEAU, pile_index=0, card_index=1)
        assert sel1 != sel2


class TestHighlightedDestinationsCreation:
    """Tests for HighlightedDestinations data structure."""

    def test_empty_highlights(self):
        highlights = HighlightedDestinations(
            tableau_piles=set(),
            foundation_piles=set(),
        )
        assert len(highlights.tableau_piles) == 0
        assert len(highlights.foundation_piles) == 0

    def test_highlights_with_tableau_only(self):
        highlights = HighlightedDestinations(
            tableau_piles={0, 3, 5},
            foundation_piles=set(),
        )
        assert highlights.tableau_piles == {0, 3, 5}
        assert len(highlights.foundation_piles) == 0

    def test_highlights_with_foundation_only(self):
        highlights = HighlightedDestinations(
            tableau_piles=set(),
            foundation_piles={1, 2},
        )
        assert len(highlights.tableau_piles) == 0
        assert highlights.foundation_piles == {1, 2}

    def test_highlights_with_both(self):
        highlights = HighlightedDestinations(
            tableau_piles={0, 6},
            foundation_piles={0},
        )
        assert 0 in highlights.tableau_piles
        assert 6 in highlights.tableau_piles
        assert 0 in highlights.foundation_piles

    def test_membership_checks(self):
        highlights = HighlightedDestinations(
            tableau_piles={1, 3, 5},
            foundation_piles={2},
        )
        assert 1 in highlights.tableau_piles
        assert 2 not in highlights.tableau_piles
        assert 2 in highlights.foundation_piles
        assert 0 not in highlights.foundation_piles


class TestHighlightedDestinationsEmpty:
    """Tests for HighlightedDestinations.empty() factory method."""

    def test_empty_creates_empty_sets(self):
        highlights = HighlightedDestinations.empty()
        assert highlights.tableau_piles == set()
        assert highlights.foundation_piles == set()

    def test_empty_returns_new_instance_each_call(self):
        h1 = HighlightedDestinations.empty()
        h2 = HighlightedDestinations.empty()
        h1.tableau_piles.add(1)
        assert 1 not in h2.tableau_piles


class TestHighlightedDestinationsHasAny:
    """Tests for HighlightedDestinations.has_any() method."""

    def test_has_any_false_when_empty(self):
        highlights = HighlightedDestinations.empty()
        assert highlights.has_any() is False

    def test_has_any_true_with_tableau(self):
        highlights = HighlightedDestinations(
            tableau_piles={3},
            foundation_piles=set(),
        )
        assert highlights.has_any() is True

    def test_has_any_true_with_foundation(self):
        highlights = HighlightedDestinations(
            tableau_piles=set(),
            foundation_piles={0},
        )
        assert highlights.has_any() is True

    def test_has_any_true_with_both(self):
        highlights = HighlightedDestinations(
            tableau_piles={1, 2},
            foundation_piles={3},
        )
        assert highlights.has_any() is True


class TestHighlightedDestinationsCount:
    """Tests for HighlightedDestinations.count() method."""

    def test_count_zero_when_empty(self):
        highlights = HighlightedDestinations.empty()
        assert highlights.count() == 0

    def test_count_tableau_only(self):
        highlights = HighlightedDestinations(
            tableau_piles={0, 2, 4},
            foundation_piles=set(),
        )
        assert highlights.count() == 3

    def test_count_foundation_only(self):
        highlights = HighlightedDestinations(
            tableau_piles=set(),
            foundation_piles={0, 1},
        )
        assert highlights.count() == 2

    def test_count_combined(self):
        highlights = HighlightedDestinations(
            tableau_piles={1, 3, 5},
            foundation_piles={0, 2},
        )
        assert highlights.count() == 5


class TestHighlightedDestinationsEquality:
    """Tests for HighlightedDestinations equality."""

    def test_equal_when_same_contents(self):
        h1 = HighlightedDestinations(tableau_piles={1, 2}, foundation_piles={0})
        h2 = HighlightedDestinations(tableau_piles={1, 2}, foundation_piles={0})
        assert h1 == h2

    def test_not_equal_different_tableau(self):
        h1 = HighlightedDestinations(tableau_piles={1}, foundation_piles=set())
        h2 = HighlightedDestinations(tableau_piles={2}, foundation_piles=set())
        assert h1 != h2

    def test_not_equal_different_foundation(self):
        h1 = HighlightedDestinations(tableau_piles=set(), foundation_piles={0})
        h2 = HighlightedDestinations(tableau_piles=set(), foundation_piles={1})
        assert h1 != h2
