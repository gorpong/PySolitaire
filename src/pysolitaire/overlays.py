"""UI overlay rendering functions for Solitaire.

This module contains pure functions for generating overlay text content
(help screens, dialogs, leaderboards) without terminal-specific rendering.
"""

from typing import Any, Dict, List


def format_time(seconds: float) -> str:
    """Format elapsed time as MM:SS.

    Args:
        seconds: Time in seconds (will be truncated to integer).

    Returns:
        Formatted string like "05:30".
    """
    total_seconds = int(seconds)
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def render_help_lines() -> List[str]:
    """Generate help overlay content lines.

    Returns:
        List of strings forming the help box.
    """
    return [
        "╔══════════════════════════════════════╗",
        "║           SOLITAIRE HELP             ║",
        "╠══════════════════════════════════════╣",
        "║  Arrow Keys : Navigate the board     ║",
        "║  Enter      : Select / Place card    ║",
        "║  Tab        : Show valid placements  ║",
        "║  Space      : Draw from stock        ║",
        "║  Escape     : Cancel selection       ║",
        "║  U          : Undo last move         ║",
        "║  L          : View leaderboard       ║",
        "║  R          : Restart game           ║",
        "║  H / ?      : Toggle this help       ║",
        "║  Q          : Quit (auto-saves)      ║",
        "╠══════════════════════════════════════╣",
        "║  Goal: Move all cards to foundations ║",
        "║  Build foundations A→K by suit       ║",
        "║  Build tableau K→A alternating color ║",
        "╚══════════════════════════════════════╝",
    ]


def render_resume_prompt_lines(move_count: int, elapsed_time: float) -> List[str]:
    """Generate resume game prompt content lines.

    Args:
        move_count: Number of moves in the saved game.
        elapsed_time: Elapsed time in seconds.

    Returns:
        List of strings forming the prompt box.
    """
    time_str = format_time(elapsed_time)
    info_line = f"            Moves: {move_count}    Time: {time_str}"
    # f-string width must match the box border width or the line will overflow
    info_line = f"║{info_line:<58}║"

    return [
        "╔══════════════════════════════════════════════════════════╗",
        "║                                                          ║",
        "║            A saved game was found!                       ║",
        info_line,
        "║                                                          ║",
        "║            Press R to RESUME                             ║",
        "║            Press N to start NEW game                     ║",
        "║                                                          ║",
        "╚══════════════════════════════════════════════════════════╝",
    ]


def render_leaderboard_overlay_lines(draw_mode: int, entries: List[Dict[str, Any]]) -> List[str]:
    """Generate leaderboard overlay content lines.

    Args:
        draw_mode: 1 or 3 for draw mode.
        entries: List of entry dicts with 'initials', 'moves', 'time_seconds'.

    Returns:
        List of strings forming the leaderboard box.
    """
    if not entries:
        return [
            "╔══════════════════════════════════════╗",
            f"║     LEADERBOARD - DRAW {draw_mode}             ║",
            "╠══════════════════════════════════════╣",
            "║                                      ║",
            "║         No entries yet!              ║",
            "║                                      ║",
            "╚══════════════════════════════════════╝",
        ]

    lines = [
        "╔══════════════════════════════════════╗",
        f"║     LEADERBOARD - DRAW {draw_mode}             ║",
        "╠═══╦═════╦════════╦══════════════════╣",
        "║ # ║ INI ║ MOVES  ║ TIME             ║",
        "╠═══╬═════╬════════╬══════════════════╣",
    ]

    for i, entry in enumerate(entries, 1):
        initials = entry.get('initials', '???')
        moves = entry.get('moves', 0)
        time_secs = entry.get('time_seconds', 0)
        time_str = format_time(time_secs)
        line = f"║{i:2d} ║ {initials} ║  {moves:4d}  ║ {time_str:16s}║"
        lines.append(line)

    lines.append("╚═══╩═════╩════════╩══════════════════╝")

    return lines


def render_win_leaderboard_lines(
    draw_mode: int,
    entries: List[Dict[str, Any]],
    position: int,
) -> List[str]:
    """Generate leaderboard display for after winning.

    Args:
        draw_mode: 1 or 3 for draw mode.
        entries: List of entry dicts.
        position: Player's position (1-indexed), or -1 if not in top 20.

    Returns:
        List of strings for the full win leaderboard display.
    """
    lines = render_leaderboard_overlay_lines(draw_mode, entries)

    if position > 0:
        msg = f"You placed #{position} on the leaderboard!"
    else:
        msg = "You didn't make the top 20, but great job!"

    lines.append("")
    lines.append(msg)
    lines.append("")
    lines.append("Press any key to exit.")

    return lines


def render_save_slot_list(slots: Dict[str, Any], mode: str = "resume") -> List[str]:
    """Generate the save slot selection list.

    Renders a box showing all 10 slots.  Occupied slots show their
    draw type, move count, elapsed time, and save timestamp.  Empty
    slots are shown as available.

    Args:
        slots: Dict keyed by slot number (int) → summary dict with keys
            ``draw_count``, ``move_count``, ``elapsed_time``, ``saved_at``.
        mode: ``"resume"`` for the resume-game screen, or ``"overwrite"``
            when all slots are full and the player must pick one to replace.

    Returns:
        List of strings forming the slot selection box.
    """
    if mode == "overwrite":
        title = "SELECT SLOT TO OVERWRITE/REPLACE"
    else:
        title = "SAVED GAMES"

    width = 58  # interior width between the outer box borders
    border_top = "\u2554" + "\u2550" * width + "\u2557"
    border_sep = "\u2560" + "\u2550" * width + "\u2563"
    border_bot = "\u255a" + "\u2550" * width + "\u255d"

    def box_line(text: str) -> str:
        return f"\u2551{text:{width}}\u2551"

    lines = [
        border_top,
        box_line(f"  {title}"),
        border_sep,
    ]

    if not slots and mode != "overwrite":
        lines.append(box_line("  No saved games found."))
        lines.append(box_line(""))
    else:
        for slot_num in range(1, 11):
            if slot_num in slots:
                entry = slots[slot_num]
                draw_label = f"Draw-{entry['draw_count']}"
                moves = entry['move_count']
                time_str = format_time(entry['elapsed_time'])
                saved_at = entry.get('saved_at', '')
                # Trim saved_at to date + HH:MM for compact display
                if 'T' in saved_at:
                    date_part, time_part = saved_at.split('T', 1)
                    saved_display = f"{date_part} {time_part[:5]}"
                else:
                    saved_display = saved_at[:16]
                row = (
                    f"  [{slot_num:2d}]  {draw_label:<6}  "
                    f"{moves:>4} moves  {time_str}  {saved_display}"
                )
            else:
                row = f"  [{slot_num:2d}]  (empty)"
            lines.append(box_line(row))

    lines.append(border_sep)
    if mode == "overwrite":
        lines.append(box_line("  Press slot number (1-9, 0=10) to overwrite, N to cancel"))
    else:
        lines.append(box_line("  Press slot number (1-9, 0=10) to resume, N for new game"))
    lines.append(border_bot)
    return lines


def render_initials_prompt(current_initials: str) -> str:
    """Generate the initials prompt string.

    Args:
        current_initials: Currently entered initials.

    Returns:
        Prompt string to display.
    """
    return f"Enter your initials (3 letters, ESC to skip): {current_initials}_"
