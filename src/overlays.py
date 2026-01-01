"""UI overlay rendering functions for Solitaire.

This module contains pure functions for generating overlay text content
(help screens, dialogs, leaderboards) without terminal-specific rendering.
"""

from typing import List, Dict, Any


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
    # Pad to fit in the box (58 chars inner width)
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

    # Add position message
    if position > 0:
        msg = f"You placed #{position} on the leaderboard!"
    else:
        msg = "You didn't make the top 20, but great job!"

    lines.append("")
    lines.append(msg)
    lines.append("")
    lines.append("Press any key to exit.")

    return lines


def render_initials_prompt(current_initials: str) -> str:
    """Generate the initials prompt string.

    Args:
        current_initials: Currently entered initials.

    Returns:
        Prompt string to display.
    """
    return f"Enter your initials (3 letters, ESC to skip): {current_initials}_"
