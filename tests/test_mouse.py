"""Tests for mouse input handling."""

import pytest
from src.model import Card, Suit, Rank, GameState
from src.cursor import CursorZone
from src.renderer import LAYOUT_LARGE, LAYOUT_COMPACT
from src.mouse import (
    ClickableRegion,
    MouseEvent,
    translate_mouse_coords,
    calculate_clickable_regions,
    find_clicked_region,
    parse_mouse_event,
    is_mouse_event,
)


class TestTranslateMouseCoords:
    """Tests for coordinate translation."""

    def test_no_padding(self):
        canvas_x, canvas_y = translate_mouse_coords(10, 20, pad_left=0)
        assert canvas_x == 10
        assert canvas_y == 20

    def test_with_padding(self):
        canvas_x, canvas_y = translate_mouse_coords(50, 20, pad_left=30)
        assert canvas_x == 20
        assert canvas_y == 20

    def test_negative_result(self):
        """Click left of the board should give negative x."""
        canvas_x, canvas_y = translate_mouse_coords(10, 20, pad_left=30)
        assert canvas_x == -20
        assert canvas_y == 20


class TestCalculateClickableRegions:
    """Tests for clickable region generation."""

    def create_empty_state(self) -> GameState:
        """Create a state with no cards."""
        return GameState()

    def create_standard_state(self) -> GameState:
        """Create a state with cards in various positions."""
        state = GameState()
        state.stock = [Card(Rank.ACE, Suit.HEARTS, face_up=False)]
        state.waste = [Card(Rank.TWO, Suit.HEARTS, face_up=True)]
        state.foundations = [
            [Card(Rank.ACE, Suit.HEARTS, face_up=True)],
            [],
            [],
            [],
        ]
        state.tableau = [
            [Card(Rank.KING, Suit.HEARTS, face_up=True)],
            [
                Card(Rank.KING, Suit.SPADES, face_up=False),
                Card(Rank.QUEEN, Suit.HEARTS, face_up=True),
            ],
            [],
            [],
            [],
            [],
            [],
        ]
        return state

    def test_always_has_stock_region(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)
        stock_regions = [r for r in regions if r.zone == CursorZone.STOCK]
        assert len(stock_regions) == 1

    def test_always_has_waste_region(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)
        waste_regions = [r for r in regions if r.zone == CursorZone.WASTE]
        assert len(waste_regions) == 1

    def test_has_four_foundation_regions(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)
        foundation_regions = [r for r in regions if r.zone == CursorZone.FOUNDATION]
        assert len(foundation_regions) == 4
        indices = {r.pile_index for r in foundation_regions}
        assert indices == {0, 1, 2, 3}

    def test_has_seven_tableau_regions_when_empty(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)
        tableau_regions = [r for r in regions if r.zone == CursorZone.TABLEAU]
        assert len(tableau_regions) == 7
        indices = {r.pile_index for r in tableau_regions}
        assert indices == {0, 1, 2, 3, 4, 5, 6}

    def test_tableau_with_cards_has_multiple_regions_per_pile(self):
        state = self.create_standard_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        pile1_regions = [
            r for r in regions if r.zone == CursorZone.TABLEAU and r.pile_index == 1
        ]
        assert len(pile1_regions) == 2
        card_indices = {r.card_index for r in pile1_regions}
        assert card_indices == {0, 1}

    def test_stock_position_large_layout(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)
        stock = [r for r in regions if r.zone == CursorZone.STOCK][0]
        assert stock.x == 2
        assert stock.y == 2
        assert stock.width == 7
        assert stock.height == 5

    def test_stock_position_compact_layout(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_COMPACT)
        stock = [r for r in regions if r.zone == CursorZone.STOCK][0]
        assert stock.x == 2
        assert stock.y == 2
        assert stock.width == 5
        assert stock.height == 3

    def test_foundation_positions_large_layout(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)
        foundations = sorted(
            [r for r in regions if r.zone == CursorZone.FOUNDATION],
            key=lambda r: r.pile_index,
        )
        expected_x = [58, 67, 76, 85]
        for i, region in enumerate(foundations):
            assert region.x == expected_x[i], f"Foundation {i} x mismatch"
            assert region.y == 2

    def test_foundation_positions_compact_layout(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_COMPACT)
        foundations = sorted(
            [r for r in regions if r.zone == CursorZone.FOUNDATION],
            key=lambda r: r.pile_index,
        )
        expected_x = [58, 65, 72, 79]
        for i, region in enumerate(foundations):
            assert region.x == expected_x[i], f"Foundation {i} x mismatch"
            assert region.y == 2

    def test_tableau_positions_large_layout(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)
        tableau = sorted(
            [r for r in regions if r.zone == CursorZone.TABLEAU],
            key=lambda r: r.pile_index,
        )
        expected_x = [2, 12, 22, 32, 42, 52, 62]
        for i, region in enumerate(tableau):
            assert region.x == expected_x[i], f"Tableau {i} x mismatch"
            assert region.y == 8

    def test_tableau_positions_compact_layout(self):
        state = self.create_empty_state()
        regions = calculate_clickable_regions(state, LAYOUT_COMPACT)
        tableau = sorted(
            [r for r in regions if r.zone == CursorZone.TABLEAU],
            key=lambda r: r.pile_index,
        )
        for region in tableau:
            assert region.y == 7

    def test_overlapped_card_height(self):
        """Cards that are overlapped should only have overlap height."""
        state = self.create_standard_state()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        pile1_regions = sorted(
            [r for r in regions if r.zone == CursorZone.TABLEAU and r.pile_index == 1],
            key=lambda r: r.card_index,
        )

        assert pile1_regions[0].height == LAYOUT_LARGE.card_overlap_y
        assert pile1_regions[1].height == LAYOUT_LARGE.card_height


class TestFindClickedRegion:
    """Tests for hit detection."""

    def test_click_inside_region(self):
        regions = [
            ClickableRegion(
                x=10, y=10, width=7, height=5, zone=CursorZone.STOCK, pile_index=0, card_index=0
            )
        ]
        result = find_clicked_region(12, 12, regions)
        assert result is not None
        assert result.zone == CursorZone.STOCK

    def test_click_outside_all_regions(self):
        regions = [
            ClickableRegion(
                x=10, y=10, width=7, height=5, zone=CursorZone.STOCK, pile_index=0, card_index=0
            )
        ]
        result = find_clicked_region(0, 0, regions)
        assert result is None

    def test_click_on_boundary_left(self):
        """Click on left edge should hit."""
        regions = [
            ClickableRegion(
                x=10, y=10, width=7, height=5, zone=CursorZone.STOCK, pile_index=0, card_index=0
            )
        ]
        result = find_clicked_region(10, 12, regions)
        assert result is not None

    def test_click_on_boundary_right_exclusive(self):
        """Click on right edge (x + width) should miss."""
        regions = [
            ClickableRegion(
                x=10, y=10, width=7, height=5, zone=CursorZone.STOCK, pile_index=0, card_index=0
            )
        ]
        result = find_clicked_region(17, 12, regions)
        assert result is None

    def test_click_on_boundary_top(self):
        """Click on top edge should hit."""
        regions = [
            ClickableRegion(
                x=10, y=10, width=7, height=5, zone=CursorZone.STOCK, pile_index=0, card_index=0
            )
        ]
        result = find_clicked_region(12, 10, regions)
        assert result is not None

    def test_click_on_boundary_bottom_exclusive(self):
        """Click on bottom edge (y + height) should miss."""
        regions = [
            ClickableRegion(
                x=10, y=10, width=7, height=5, zone=CursorZone.STOCK, pile_index=0, card_index=0
            )
        ]
        result = find_clicked_region(12, 15, regions)
        assert result is None

    def test_overlapping_regions_prefer_higher_card_index(self):
        """When cards overlap, prefer the topmost (highest index) card."""
        regions = [
            ClickableRegion(
                x=10, y=10, width=7, height=1, zone=CursorZone.TABLEAU, pile_index=0, card_index=0
            ),
            ClickableRegion(
                x=10, y=10, width=7, height=5, zone=CursorZone.TABLEAU, pile_index=0, card_index=1
            ),
        ]
        result = find_clicked_region(12, 10, regions)
        assert result is not None
        assert result.card_index == 1

    def test_non_overlapping_regions(self):
        """Clicking different regions should return the correct one."""
        regions = [
            ClickableRegion(
                x=2, y=2, width=7, height=5, zone=CursorZone.STOCK, pile_index=0, card_index=0
            ),
            ClickableRegion(
                x=10, y=2, width=7, height=5, zone=CursorZone.WASTE, pile_index=0, card_index=0
            ),
        ]

        stock_click = find_clicked_region(5, 4, regions)
        assert stock_click is not None
        assert stock_click.zone == CursorZone.STOCK

        waste_click = find_clicked_region(13, 4, regions)
        assert waste_click is not None
        assert waste_click.zone == CursorZone.WASTE

    def test_empty_regions_list(self):
        result = find_clicked_region(10, 10, [])
        assert result is None


class TestMouseEventParsing:
    """Tests for mouse event parsing using blessed's actual format."""

    class MockKey:
        """Mock blessed key object for mouse events."""

        def __init__(self, name: str, mouse_xy: tuple = (0, 0)):
            self.name = name
            self.mouse_xy = mouse_xy

    def test_parse_left_click_pressed(self):
        """MOUSE_LEFT means left button pressed."""
        key = self.MockKey("MOUSE_LEFT", mouse_xy=(10, 20))
        event = parse_mouse_event(key)
        assert event is not None
        assert event.button == "left"
        assert event.action == "pressed"
        assert event.x == 10
        assert event.y == 20

    def test_parse_left_click_released(self):
        """MOUSE_LEFT_RELEASED means left button released."""
        key = self.MockKey("MOUSE_LEFT_RELEASED", mouse_xy=(15, 25))
        event = parse_mouse_event(key)
        assert event is not None
        assert event.button == "left"
        assert event.action == "released"
        assert event.x == 15
        assert event.y == 25

    def test_parse_right_click_pressed(self):
        """MOUSE_RIGHT means right button pressed."""
        key = self.MockKey("MOUSE_RIGHT", mouse_xy=(5, 15))
        event = parse_mouse_event(key)
        assert event is not None
        assert event.button == "right"
        assert event.action == "pressed"
        assert event.x == 5
        assert event.y == 15

    def test_parse_right_click_released(self):
        """MOUSE_RIGHT_RELEASED means right button released."""
        key = self.MockKey("MOUSE_RIGHT_RELEASED", mouse_xy=(8, 18))
        event = parse_mouse_event(key)
        assert event is not None
        assert event.button == "right"
        assert event.action == "released"
        assert event.x == 8
        assert event.y == 18

    def test_parse_middle_click_pressed(self):
        """MOUSE_MIDDLE means middle button pressed."""
        key = self.MockKey("MOUSE_MIDDLE", mouse_xy=(30, 40))
        event = parse_mouse_event(key)
        assert event is not None
        assert event.button == "middle"
        assert event.action == "pressed"
        assert event.x == 30
        assert event.y == 40

    def test_parse_middle_click_released(self):
        """MOUSE_MIDDLE_RELEASED means middle button released."""
        key = self.MockKey("MOUSE_MIDDLE_RELEASED", mouse_xy=(35, 45))
        event = parse_mouse_event(key)
        assert event is not None
        assert event.button == "middle"
        assert event.action == "released"
        assert event.x == 35
        assert event.y == 45

    def test_parse_non_mouse_key(self):
        key = self.MockKey("KEY_UP", mouse_xy=(0, 0))
        event = parse_mouse_event(key)
        assert event is None

    def test_parse_regular_key(self):
        key = self.MockKey("a", mouse_xy=(0, 0))
        event = parse_mouse_event(key)
        assert event is None

    def test_parse_no_name_attribute(self):
        class NoNameKey:
            pass

        event = parse_mouse_event(NoNameKey())
        assert event is None

    def test_parse_none_name(self):
        key = self.MockKey(None)
        key.name = None
        event = parse_mouse_event(key)
        assert event is None

    def test_parse_no_mouse_xy_attribute(self):
        """If mouse_xy is missing, should return None."""
        class PartialKey:
            name = "MOUSE_LEFT"

        event = parse_mouse_event(PartialKey())
        assert event is None

    def test_parse_invalid_coordinates(self):
        """Coordinates of -1, -1 indicate non-mouse event."""
        key = self.MockKey("MOUSE_LEFT", mouse_xy=(-1, -1))
        event = parse_mouse_event(key)
        assert event is None


class TestIsMouseEvent:
    """Tests for mouse event detection."""

    class MockKey:
        def __init__(self, name):
            self.name = name

    def test_is_mouse_event_left(self):
        key = self.MockKey("MOUSE_LEFT")
        assert is_mouse_event(key) is True

    def test_is_mouse_event_left_released(self):
        key = self.MockKey("MOUSE_LEFT_RELEASED")
        assert is_mouse_event(key) is True

    def test_is_mouse_event_right(self):
        key = self.MockKey("MOUSE_RIGHT")
        assert is_mouse_event(key) is True

    def test_is_mouse_event_right_released(self):
        key = self.MockKey("MOUSE_RIGHT_RELEASED")
        assert is_mouse_event(key) is True

    def test_is_mouse_event_middle(self):
        key = self.MockKey("MOUSE_MIDDLE")
        assert is_mouse_event(key) is True

    def test_is_mouse_event_false_regular_key(self):
        key = self.MockKey("KEY_UP")
        assert is_mouse_event(key) is False

    def test_is_mouse_event_false_letter(self):
        key = self.MockKey("a")
        assert is_mouse_event(key) is False

    def test_is_mouse_event_no_name(self):
        class NoNameKey:
            pass

        assert is_mouse_event(NoNameKey()) is False

    def test_is_mouse_event_none_name(self):
        key = self.MockKey(None)
        assert is_mouse_event(key) is False


class TestClickableRegionIntegration:
    """Integration tests for full click workflow."""

    def test_click_stock_area(self):
        """Clicking in stock area should return stock region."""
        state = GameState()
        state.stock = [Card(Rank.ACE, Suit.HEARTS)]
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        result = find_clicked_region(5, 4, regions)
        assert result is not None
        assert result.zone == CursorZone.STOCK

    def test_click_foundation_area(self):
        """Clicking in foundation area should return correct foundation."""
        state = GameState()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        result = find_clicked_region(60, 4, regions)
        assert result is not None
        assert result.zone == CursorZone.FOUNDATION
        assert result.pile_index == 0

        result = find_clicked_region(78, 4, regions)
        assert result is not None
        assert result.zone == CursorZone.FOUNDATION
        assert result.pile_index == 2

    def test_click_tableau_card(self):
        """Clicking on a tableau card should return correct pile and card."""
        state = GameState()
        state.tableau[0] = [
            Card(Rank.KING, Suit.HEARTS, face_up=False),
            Card(Rank.QUEEN, Suit.SPADES, face_up=True),
        ]
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        result = find_clicked_region(5, 12, regions)
        assert result is not None
        assert result.zone == CursorZone.TABLEAU
        assert result.pile_index == 0
        assert result.card_index == 1

    def test_click_between_piles_misses(self):
        """Clicking in gap between piles should return None."""
        state = GameState()
        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        result = find_clicked_region(10, 10, regions)
        assert result is None

    def test_full_board_click_workflow_large(self):
        """Test clicking various areas on a full board with large layout."""
        state = GameState()
        state.stock = [Card(Rank.ACE, Suit.HEARTS)]
        state.waste = [Card(Rank.TWO, Suit.HEARTS, face_up=True)]
        state.foundations[0] = [Card(Rank.ACE, Suit.HEARTS, face_up=True)]
        state.tableau[3] = [Card(Rank.KING, Suit.SPADES, face_up=True)]

        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        result = find_clicked_region(4, 4, regions)
        assert result.zone == CursorZone.STOCK

        result = find_clicked_region(12, 4, regions)
        assert result.zone == CursorZone.WASTE

        result = find_clicked_region(60, 4, regions)
        assert result.zone == CursorZone.FOUNDATION
        assert result.pile_index == 0

        result = find_clicked_region(34, 10, regions)
        assert result.zone == CursorZone.TABLEAU
        assert result.pile_index == 3

    def test_full_board_click_workflow_compact(self):
        """Test clicking various areas on a full board with compact layout."""
        state = GameState()
        state.stock = [Card(Rank.ACE, Suit.HEARTS)]
        state.waste = [Card(Rank.TWO, Suit.HEARTS, face_up=True)]
        state.foundations[0] = [Card(Rank.ACE, Suit.HEARTS, face_up=True)]
        state.tableau[3] = [Card(Rank.KING, Suit.SPADES, face_up=True)]

        regions = calculate_clickable_regions(state, LAYOUT_COMPACT)

        result = find_clicked_region(4, 3, regions)
        assert result.zone == CursorZone.STOCK

        result = find_clicked_region(12, 3, regions)
        assert result.zone == CursorZone.WASTE

        result = find_clicked_region(60, 3, regions)
        assert result.zone == CursorZone.FOUNDATION
        assert result.pile_index == 0

        result = find_clicked_region(34, 8, regions)
        assert result.zone == CursorZone.TABLEAU
        assert result.pile_index == 3


class TestDragDetection:
    """Tests for drag vs click detection logic."""

    def test_same_region_is_click(self):
        """Press and release on same region should be detected as click."""
        region1 = ClickableRegion(
            x=10, y=10, width=7, height=5, zone=CursorZone.WASTE, pile_index=0, card_index=0
        )
        region2 = ClickableRegion(
            x=10, y=10, width=7, height=5, zone=CursorZone.WASTE, pile_index=0, card_index=0
        )

        same_region = (
            region1.zone == region2.zone and
            region1.pile_index == region2.pile_index and
            region1.card_index == region2.card_index
        )
        assert same_region is True

    def test_different_zone_is_drag(self):
        """Press and release on different zones should be detected as drag."""
        region1 = ClickableRegion(
            x=10, y=10, width=7, height=5, zone=CursorZone.WASTE, pile_index=0, card_index=0
        )
        region2 = ClickableRegion(
            x=20, y=20, width=7, height=5, zone=CursorZone.TABLEAU, pile_index=0, card_index=0
        )

        same_region = (
            region1.zone == region2.zone and
            region1.pile_index == region2.pile_index and
            region1.card_index == region2.card_index
        )
        assert same_region is False

    def test_different_pile_is_drag(self):
        """Press and release on different piles should be detected as drag."""
        region1 = ClickableRegion(
            x=10, y=10, width=7, height=5, zone=CursorZone.TABLEAU, pile_index=0, card_index=0
        )
        region2 = ClickableRegion(
            x=20, y=10, width=7, height=5, zone=CursorZone.TABLEAU, pile_index=1, card_index=0
        )

        same_region = (
            region1.zone == region2.zone and
            region1.pile_index == region2.pile_index and
            region1.card_index == region2.card_index
        )
        assert same_region is False

    def test_different_card_index_is_drag(self):
        """Press and release on different cards in same pile should be detected as drag."""
        region1 = ClickableRegion(
            x=10, y=10, width=7, height=1, zone=CursorZone.TABLEAU, pile_index=0, card_index=0
        )
        region2 = ClickableRegion(
            x=10, y=11, width=7, height=5, zone=CursorZone.TABLEAU, pile_index=0, card_index=1
        )

        same_region = (
            region1.zone == region2.zone and
            region1.pile_index == region2.pile_index and
            region1.card_index == region2.card_index
        )
        assert same_region is False

    def test_drag_waste_to_tableau(self):
        """Simulate drag from waste to tableau."""
        state = GameState()
        state.waste = [Card(Rank.FIVE, Suit.HEARTS, face_up=True)]
        state.tableau[0] = [Card(Rank.SIX, Suit.SPADES, face_up=True)]

        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        # Find waste region (press location)
        press_region = find_clicked_region(12, 4, regions)
        assert press_region is not None
        assert press_region.zone == CursorZone.WASTE

        # Find tableau 0 region (release location)
        release_region = find_clicked_region(5, 10, regions)
        assert release_region is not None
        assert release_region.zone == CursorZone.TABLEAU
        assert release_region.pile_index == 0

        # Should be detected as drag (different regions)
        same_region = (
            press_region.zone == release_region.zone and
            press_region.pile_index == release_region.pile_index and
            press_region.card_index == release_region.card_index
        )
        assert same_region is False

    def test_drag_tableau_to_foundation(self):
        """Simulate drag from tableau to foundation."""
        state = GameState()
        state.tableau[0] = [Card(Rank.ACE, Suit.HEARTS, face_up=True)]

        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        # Find tableau 0 region (press location)
        press_region = find_clicked_region(5, 10, regions)
        assert press_region is not None
        assert press_region.zone == CursorZone.TABLEAU
        assert press_region.pile_index == 0

        # Find foundation 0 region (release location) - Hearts foundation
        release_region = find_clicked_region(60, 4, regions)
        assert release_region is not None
        assert release_region.zone == CursorZone.FOUNDATION
        assert release_region.pile_index == 0

        # Should be detected as drag
        same_region = (
            press_region.zone == release_region.zone and
            press_region.pile_index == release_region.pile_index and
            press_region.card_index == release_region.card_index
        )
        assert same_region is False

    def test_drag_tableau_to_tableau(self):
        """Simulate drag from one tableau pile to another."""
        state = GameState()
        state.tableau[0] = [Card(Rank.QUEEN, Suit.HEARTS, face_up=True)]
        state.tableau[1] = [Card(Rank.KING, Suit.SPADES, face_up=True)]

        regions = calculate_clickable_regions(state, LAYOUT_LARGE)

        # Find tableau 0 region (press location)
        press_region = find_clicked_region(5, 10, regions)
        assert press_region is not None
        assert press_region.zone == CursorZone.TABLEAU
        assert press_region.pile_index == 0

        # Find tableau 1 region (release location)
        release_region = find_clicked_region(15, 10, regions)
        assert release_region is not None
        assert release_region.zone == CursorZone.TABLEAU
        assert release_region.pile_index == 1

        # Should be detected as drag
        same_region = (
            press_region.zone == release_region.zone and
            press_region.pile_index == release_region.pile_index and
            press_region.card_index == release_region.card_index
        )
        assert same_region is False
