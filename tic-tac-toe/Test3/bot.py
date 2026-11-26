"""Beginner-level opponent for the five-in-a-row game."""

import random

BOT_NAME = "IQ 1"
BOARD_SIZE = 15
EMPTY = "_"
DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1))


def _would_win(board: list[list[str]], row: int, col: int, player: str) -> bool:
    for row_step, col_step in DIRECTIONS:
        count = 1
        for direction in (-1, 1):
            current_row = row + direction * row_step
            current_col = col + direction * col_step
            while (
                0 <= current_row < BOARD_SIZE
                and 0 <= current_col < BOARD_SIZE
                and board[current_row][current_col] == player
            ):
                count += 1
                current_row += direction * row_step
                current_col += direction * col_step
        if count >= 5:
            return True
    return False


def _winning_moves(board: list[list[str]], player: str) -> list[tuple[int, int]]:
    return [
        (row, col)
        for row in range(BOARD_SIZE)
        for col in range(BOARD_SIZE)
        if board[row][col] == EMPTY and _would_win(board, row, col, player)
    ]


def get_move(board: list[list[str]], player: str) -> tuple[int, int]:
    opponent = "O" if player == "X" else "X"
    winning = _winning_moves(board, player)
    if winning:
        return winning[0]

    opponent_wins = _winning_moves(board, opponent)
    if opponent_wins:
        return opponent_wins[0]

    candidates = []
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] != EMPTY:
                continue
            if any(
                board[near_row][near_col] != EMPTY
                for near_row in range(max(0, row - 2), min(BOARD_SIZE, row + 3))
                for near_col in range(max(0, col - 2), min(BOARD_SIZE, col + 3))
            ):
                candidates.append((row, col))

    if not candidates:
        if all(cell != EMPTY for line in board for cell in line):
            raise ValueError("No legal move remains on the board.")
        return (BOARD_SIZE // 2, BOARD_SIZE // 2)
    return random.choice(candidates)


def swap2_propose(board: list[list[str]]) -> list[tuple[int, int, str]]:
    return [(7, 6, "X"), (7, 7, "X"), (8, 7, "O")]


def swap2_respond(board: list[list[str]]) -> dict[str, str]:
    return {"action": "TAKE_O"}


def swap2_final_choice(board: list[list[str]]) -> str:
    return "O"
