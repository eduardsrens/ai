"""Three-ply tactical bot for the 15x15 five-in-a-row game."""

from __future__ import annotations

import time

BOT_NAME = "Klāvs Top 1 (v2)"

BOARD_SIZE = 15
EMPTY = "_"
OTHER = {"X": "O", "O": "X"}
DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1))

_PATTERN_SCORES = (0, 1, 8, 80, 1_600, 2_000_000)
_WIN_SCORE = 1_000_000_000_000
_ROOT_WIDTH = 10
_REPLY_WIDTH = 8
_FOLLOW_WIDTH = 6
_THINK_TIME = 0.80


class _SearchTimeout(Exception):
    pass


def _inside(row: int, col: int) -> bool:
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def _candidate_moves(board: list[list[str]]) -> list[tuple[int, int]]:
    occupied = [
        (row, col)
        for row in range(BOARD_SIZE)
        for col in range(BOARD_SIZE)
        if board[row][col] != EMPTY
    ]
    if not occupied:
        return [(BOARD_SIZE // 2, BOARD_SIZE // 2)]

    candidates: set[tuple[int, int]] = set()
    for row, col in occupied:
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                cell = (row + dr, col + dc)
                if _inside(*cell) and board[cell[0]][cell[1]] == EMPTY:
                    candidates.add(cell)
    return list(candidates)


def _winner_after(
    board: list[list[str]], row: int, col: int, player: str
) -> bool:
    for dr, dc in DIRECTIONS:
        count = 1
        for sign in (-1, 1):
            rr, cc = row + sign * dr, col + sign * dc
            while _inside(rr, cc) and board[rr][cc] == player:
                count += 1
                rr += sign * dr
                cc += sign * dc
        if count >= 5:
            return True
    return False


def _winning_moves(board: list[list[str]], player: str) -> list[tuple[int, int]]:
    wins = []
    for row, col in _candidate_moves(board):
        board[row][col] = player
        won = _winner_after(board, row, col, player)
        board[row][col] = EMPTY
        if won:
            wins.append((row, col))
    return wins


def _move_score(board: list[list[str]], row: int, col: int, player: str) -> int:
    opponent = OTHER[player]
    score = 0

    for dr, dc in DIRECTIONS:
        for offset in range(5):
            start_row = row - offset * dr
            start_col = col - offset * dc
            cells = [
                (start_row + step * dr, start_col + step * dc)
                for step in range(5)
            ]
            if not all(_inside(rr, cc) for rr, cc in cells):
                continue

            own = 1
            blocked = False
            for rr, cc in cells:
                if (rr, cc) == (row, col):
                    continue
                if board[rr][cc] == opponent:
                    blocked = True
                    break
                if board[rr][cc] == player:
                    own += 1
            if not blocked:
                score += _PATTERN_SCORES[own]

    return score


def _move_priority(
    board: list[list[str]], row: int, col: int, player: str
) -> int:
    opponent = OTHER[player]
    attack = _move_score(board, row, col, player)
    defense = _move_score(board, row, col, opponent)
    return attack + defense * 11 // 10


def _ordered_moves(
    board: list[list[str]], player: str, limit: int
) -> list[tuple[int, int]]:
    moves = _candidate_moves(board)
    middle = BOARD_SIZE // 2
    moves.sort(
        key=lambda move: (
            _move_priority(board, move[0], move[1], player),
            -abs(move[0] - middle) - abs(move[1] - middle),
            -move[0],
            -move[1],
        ),
        reverse=True,
    )
    return moves[:limit]


def _position_score(board: list[list[str]], player: str) -> int:
    opponent = OTHER[player]
    totals = {player: 0, opponent: 0}

    for dr, dc in DIRECTIONS:
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                end_row = row + 4 * dr
                end_col = col + 4 * dc
                if not _inside(end_row, end_col):
                    continue

                own_count = 0
                opponent_count = 0
                for step in range(5):
                    cell = board[row + step * dr][col + step * dc]
                    if cell == player:
                        own_count += 1
                    elif cell == opponent:
                        opponent_count += 1

                if opponent_count == 0:
                    totals[player] += _PATTERN_SCORES[own_count]
                if own_count == 0:
                    totals[opponent] += _PATTERN_SCORES[opponent_count]

    return totals[player] - totals[opponent]


def _search(
    board: list[list[str]],
    player: str,
    root_player: str,
    depth: int,
    alpha: int,
    beta: int,
    deadline: float,
) -> int:
    if time.perf_counter() >= deadline:
        raise _SearchTimeout
    if depth == 0:
        return _position_score(board, root_player)

    opponent = OTHER[player]
    if _winning_moves(board, player):
        return _WIN_SCORE if player == root_player else -_WIN_SCORE

    opponent_wins = _winning_moves(board, opponent)
    if len(opponent_wins) > 1:
        return _WIN_SCORE if opponent == root_player else -_WIN_SCORE
    if opponent_wins:
        moves = opponent_wins
    else:
        width = _REPLY_WIDTH if depth >= 2 else _FOLLOW_WIDTH
        moves = _ordered_moves(board, player, width)
    if not moves:
        return 0

    maximizing = player == root_player
    best_score = -_WIN_SCORE * 2 if maximizing else _WIN_SCORE * 2
    for row, col in moves:
        if time.perf_counter() >= deadline:
            raise _SearchTimeout
        board[row][col] = player
        try:
            if _winner_after(board, row, col, player):
                score = _WIN_SCORE if maximizing else -_WIN_SCORE
            else:
                score = _search(
                    board,
                    opponent,
                    root_player,
                    depth - 1,
                    alpha,
                    beta,
                    deadline,
                )
        finally:
            board[row][col] = EMPTY

        if maximizing:
            best_score = max(best_score, score)
            alpha = max(alpha, best_score)
        else:
            best_score = min(best_score, score)
            beta = min(beta, best_score)
        if beta <= alpha:
            break
    return best_score


def get_move(board: list[list[str]], player: str) -> tuple[int, int]:
    """Return a strong legal move without changing the supplied board."""
    deadline = time.perf_counter() + _THINK_TIME
    state = [row[:] for row in board]
    opponent = OTHER[player]
    candidates = _candidate_moves(state)
    if not candidates:
        return (BOARD_SIZE // 2, BOARD_SIZE // 2)

    wins = _winning_moves(state, player)
    if wins:
        return wins[0]

    opponent_wins = _winning_moves(state, opponent)
    if opponent_wins:
        return opponent_wins[0]

    root_moves = _ordered_moves(state, player, _ROOT_WIDTH)
    best_move = root_moves[0]
    best_score = -_WIN_SCORE * 2
    alpha = -_WIN_SCORE * 2

    try:
        for row, col in root_moves:
            if time.perf_counter() >= deadline:
                raise _SearchTimeout
            state[row][col] = player
            try:
                if _winner_after(state, row, col, player):
                    return (row, col)
                score = _search(
                    state,
                    opponent,
                    player,
                    2,
                    alpha,
                    _WIN_SCORE * 2,
                    deadline,
                )
            finally:
                state[row][col] = EMPTY
            if score > best_score:
                best_score = score
                best_move = (row, col)
            alpha = max(alpha, best_score)
    except _SearchTimeout:
        pass

    return best_move


def swap2_propose(board: list[list[str]]) -> list[tuple[int, int, str]]:
    """Place a symmetric three-stone opening for the Swap2 phase."""
    middle = BOARD_SIZE // 2
    return [
        (middle, middle - 1, "X"),
        (middle, middle, "O"),
        (middle, middle + 1, "X"),
    ]


def swap2_respond(board: list[list[str]]) -> dict[str, str]:
    """Take the color with the stronger opening position."""
    return {
        "action": "TAKE_X"
        if _position_score(board, "X") >= _position_score(board, "O")
        else "TAKE_O"
    }


def swap2_final_choice(board: list[list[str]]) -> str:
    """Choose the color with the stronger position after PLACE_TWO."""
    return "X" if _position_score(board, "X") >= _position_score(board, "O") else "O"
