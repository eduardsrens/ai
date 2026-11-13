import colorsys
import json
import logging
import math
import queue
import random
import secrets
import socket
import socketserver
import threading
import time
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk


PORT = 50505
GAME_TIME_LIMIT_SECONDS = 15 * 60
ROUND_TIME_LIMIT_SECONDS = 15
MAX_SETUP_CELLS = 20
MIN_SETUP_CELLS = 1
MAX_STARTING_CELLS = 100
MAX_TURN_CELLS = 20
DEFAULT_TURN_CELLS = 6
MIN_TURN_CELLS = 1
MIN_ROUND_TIME_SECONDS = 5
MAX_ROUND_TIME_SECONDS = 20
MIN_GAME_TIME_SECONDS = 60
MAX_GAME_TIME_SECONDS = 30 * 60
ATTACK_COLOR = "#ff4545"
RECONNECT_TIMEOUT_SECONDS = 10
REACTION_DISPLAY_SECONDS = 3
REACTION_EMOJIS = {
    "happy": "😊",
    "sad": "😢",
    "angry": "😠",
}
MULTIPLAYER_WIN_MESSAGES = (
    "GOOD JOB!",
    "You made a square move; omg, how did you do that?",
    "Oh wow, good job!",
)
MULTIPLAYER_LOSS_MESSAGES = (
    "Whoops!",
    "Aww, no :(",
    "Not this time!",
    "Better luck next round!",
)
MULTIPLAYER_FACTS = (
    (
        "The world's first computer programmer was a woman. In 1843, Ada Lovelace "
        "wrote an algorithm for Charles Babbage's Analytical Engine to calculate "
        "Bernoulli numbers."
    ),
    (
        'The first computer "bug" was a real insect. In 1947, Grace Hopper and her '
        "team found a moth trapped in a Harvard Mark II relay and taped it into "
        'their logbook with the note, "First actual case of bug being found."'
    ),
    (
        "\"Algorithm\" comes from a person's name: the Latinized form of the name of "
        "9th-century Persian mathematician Muhammad ibn Musa al-Khwarizmi."
    ),
    (
        "George Boole developed Boolean algebra in 1854, nearly a century before "
        "the first electronic computer—and without knowing about computers."
    ),
    (
        'Physicist William Higinbotham created "Tennis for Two" on an oscilloscope '
        "in 1958 to entertain laboratory visitors."
    ),
    (
        "Apollo 11's guidance software was woven by hand into core-rope memory. "
        'Margaret Hamilton led the software team; the memory was nicknamed "LOL '
        'memory," short for "Little Old Lady memory."'
    ),
    (
        'Creeper was an early computer worm. In 1971, Bob Thomas created the '
        'experimental program to move across ARPANET and display: "I\'m the '
        'creeper, catch me if you can!"'
    ),
    (
        "Reaper was created to find and remove copies of Creeper. Like Creeper, "
        "Reaper spread through the network as a worm."
    ),
    (
        "FORTRAN was developed by IBM in 1957 and is often described as the oldest "
        "high-level language still in use. It remains used in supercomputing and "
        "weather forecasting."
    ),
    (
        "The first web browser was called WorldWideWeb. Tim Berners-Lee wrote it "
        "on a NeXT computer in 1990 and later renamed it Nexus to avoid confusion "
        "with the World Wide Web."
    ),
    (
        "Python was named after the British comedy group Monty Python, not after "
        "the snake."
    ),
    (
        "Java was originally called Oak, after a tree near James Gosling's office. "
        "The name changed because of trademark concerns; Java was inspired by "
        "coffee."
    ),
    (
        "Brendan Eich created the first JavaScript prototype in 10 days in 1995 "
        "for the Netscape Navigator 2.0 release."
    ),
    (
        'Java and JavaScript are about as related as "car" and "carpet"; the name '
        "JavaScript was chosen partly for marketing reasons."
    ),
    (
        "C followed the B programming language, which was a simplified descendant "
        "of BCPL (Basic Combined Programming Language)."
    ),
    (
        "The # in C# is a musical sharp sign, suggesting a step up from C++; it "
        "also resembles four plus signs arranged together."
    ),
    (
        "Ruby's creator, Yukihiro Matsumoto, designed it with programmer happiness "
        "in mind and drew inspiration from languages including Perl and Python."
    ),
    (
        "Kotlin is named after Kotlin Island near Saint Petersburg, following "
        "Java's island-inspired name."
    ),
    (
        "Rust is named after rust fungi. Its creator, Graydon Hoare, described them "
        "as being over-engineered for survival."
    ),
    (
        "Go's gopher mascot was drawn by Renée French, who also created Glenda, "
        "the rabbit mascot for the Plan 9 operating system."
    ),
    (
        "Brainfuck has only eight commands, yet it is Turing complete and can "
        "express any computable algorithm."
    ),
    (
        "Whitespace uses spaces, tabs, and line breaks as its instructions; "
        "ordinary visible characters are ignored."
    ),
    (
        "In the Shakespeare programming language, programs resemble plays: "
        "characters act as variables, and insults or compliments set values."
    ),
    (
        "Chef programs are written to look like recipes: ingredients represent "
        "variables and mixing bowls represent stacks."
    ),
    (
        "LOLCODE is inspired by internet cat-speak. A program begins with "
        "HAI 1.2 and ends with KTHXBYE."
    ),
    (
        "ArnoldC uses Arnold Schwarzenegger quotes as commands. For example, "
        "I LIED means false, and I'LL BE BACK means return."
    ),
    (
        "Malbolge was designed to be extremely difficult to program in. Its first "
        "program was generated by a search algorithm two years after the language "
        "was released."
    ),
    (
        "Piet programs look like abstract paintings. Their instructions are "
        "encoded in color transitions, and the language is named after artist "
        "Piet Mondrian."
    ),
    (
        "INTERCAL, created in 1972 as a parody, requires the word PLEASE at just "
        "the right frequency or its compiler complains that the program is "
        "impolite or overly flattering."
    ),
    (
        "Rockstar is a programming language whose code is designed to read like "
        "1980s rock ballads."
    ),
    (
        "Euclid's algorithm for finding the greatest common divisor is over "
        "2,300 years old and is still used in modern computing."
    ),
    (
        "Bogosort repeatedly shuffles a list and checks whether it is sorted. "
        "Its expected running time grows factorially, making it wildly "
        "impractical for large lists."
    ),
    (
        "Sleep Sort starts a timer for each number and prints it after that many "
        "seconds, using timing to put the numbers in order."
    ),
    (
        "Stalin Sort scans a list and deletes any item that breaks ascending "
        "order, leaving a sorted subsequence."
    ),
    (
        "Edsger Dijkstra said he came up with his shortest-path algorithm in "
        "about 20 minutes while sitting at a café with his fiancée."
    ),
    (
        "Tim Peters created Timsort in 2002. It combines merge sort and insertion "
        "sort and is used by Python and several other platforms."
    ),
    (
        "Quicksort averages O(n log n) time, but poor pivot choices can make its "
        "worst-case running time O(n²)."
    ),
    (
        "The Fast Fourier Transform makes many signal-processing tasks practical, "
        "including parts of audio and image compression and wireless "
        "communications."
    ),
    (
        "Google's PageRank is named after co-founder Larry Page, not simply after "
        "web pages. The algorithm was patented in 1998."
    ),
    (
        "A Bloom filter can produce false positives, but not false negatives: it "
        "can say an item might be present or that it is definitely absent."
    ),
    (
        "Zero-based indexing became common partly because an array index can "
        "represent an offset from the array's starting address."
    ),
    (
        "Floating-point arithmetic cannot represent many decimal fractions "
        "exactly, which is why 0.1 + 0.2 may not equal 0.3 in code."
    ),
    (
        "The Year 2038 problem affects some 32-bit systems when Unix time exceeds "
        "the maximum signed 32-bit integer on January 19, 2038."
    ),
    (
        "The Y2K problem arose because many programs stored years with two digits, "
        "so 99 could mean 1999. Fixing the issue required changes to many systems."
    ),
    (
        "A kibibyte (KiB) is 1,024 bytes, while a kilobyte (kB) is 1,000 bytes. "
        "The IEC standardized binary prefixes such as KiB in 1998."
    ),
    (
        "In IEEE 754 arithmetic, NaN is not equal to itself: NaN == NaN evaluates "
        "to false."
    ),
    (
        "Quake III Arena's famous fast inverse square-root routine used the "
        "constant 0x5f3759df and included the memorable source comment "
        '"// what the fuck?"'
    ),
    (
        "UTF-8 preserves ASCII: its encodings for the first 128 characters match "
        "the ASCII bytes exactly."
    ),
    (
        "IPv6 provides 2¹²⁸ addresses—enough to assign trillions of addresses to "
        "every square meter of Earth's surface."
    ),
    (
        "Google was originally called BackRub, a name referring to its analysis "
        "of web backlinks."
    ),
    (
        "The Ariane 5 rocket was destroyed 37 seconds after launch in 1996 after "
        "a conversion from a 64-bit value to a 16-bit value caused a software "
        "failure. The loss was valued at about $370 million."
    ),
    (
        "Mariner 1 was destroyed shortly after launch in 1962 after a missing "
        "overbar in a formula contributed to a guidance error."
    ),
    (
        "NASA's Mars Climate Orbiter was lost in 1999 after its teams used "
        "different units: one system used newton-seconds while another used "
        "pound-force seconds."
    ),
    (
        "A popular story says Civilization's Gandhi became aggressive because of "
        "an integer overflow. Designer Sid Meier later said this was a myth that "
        "was added to later games as a joke."
    ),
    (
        "Knight Capital lost about $440 million in 45 minutes in 2012 after old "
        "test code was accidentally activated in its trading system."
    ),
    (
        "A race condition in the Therac-25 radiation therapy machine's software "
        "contributed to several patients receiving dangerous radiation "
        "overdoses."
    ),
    (
        "In 2016, removing the 11-line npm package left-pad broke many projects "
        "that depended on it, including projects in the React and Babel "
        "ecosystems."
    ),
    (
        "Intel paid about $475 million to settle claims related to the Pentium "
        "FDIV floating-point division bug discovered in 1994."
    ),
    (
        "The Heartbleed bug was a memory-read vulnerability in OpenSSL that could "
        "expose data from a server's memory."
    ),
    (
        "Investigations into Toyota's unintended-acceleration incidents found "
        "complex software with thousands of global variables, raising concerns "
        "about its safety and maintainability."
    ),
    (
        "Linus Torvalds named Linux after himself. He later joked that he named "
        "Git after himself too; in British slang, 'git' can mean an unpleasant "
        "or stubborn person."
    ),
    (
        "Bill Gates wrote his first program at age 13: a Tic-Tac-Toe game in "
        "BASIC."
    ),
    (
        "Steve Wozniak wrote the Apple II BASIC interpreter without access to a "
        "computer for testing, translating parts of the code into machine code "
        "by hand."
    ),
    (
        "Ken Thompson wrote the first version of Unix in 1969 while his family "
        "was away on vacation."
    ),
    (
        "Donald Knuth offers a $2.56 check for errors found in The Art of "
        "Computer Programming—a hexadecimal dollar."
    ),
    (
        "The Konami Code (Up, Up, Down, Down, Left, Right, Left, Right, B, A) "
        "was added to Gradius in 1986 to make testing easier."
    ),
    (
        "In 1979, Warren Robinett hid a room with his name in Atari's Adventure, "
        "creating one of the earliest well-known video-game Easter eggs."
    ),
    (
        '"// Magic. Do not touch." is a familiar kind of programming folklore: '
        "a mysterious code fragment that nobody dares remove."
    ),
    (
        "Rubber duck debugging means explaining code line by line to an object, "
        "such as a toy duck; talking through the logic can reveal a bug."
    ),
    (
        "The bus factor is the smallest number of team members whose absence "
        "would leave a project without essential knowledge."
    ),
    (
        "The world's first website is still available at info.cern.ch. It used "
        "simple text and links."
    ),
    (
        "CAPTCHA stands for Completely Automated Public Turing test to tell "
        "Computers and Humans Apart. Some early text CAPTCHAs also helped digitize "
        "old books."
    ),
    (
        "One of the first web banner ads appeared in 1994. Its question, "
        '"Have you ever clicked your mouse right HERE? You will," reportedly '
        "achieved a 44% click-through rate."
    ),
    (
        "RSA is named for its creators, Rivest, Shamir, and Adleman. They "
        "published it in 1977; a similar method had been developed secretly at "
        "GCHQ in 1973."
    ),
    (
        "Joseph Weizenbaum created ELIZA in 1966. Its therapist-style scripts "
        "rephrased users' statements as questions, and some users felt it "
        "understood them."
    ),
    (
        "IBM's Deep Blue defeated world chess champion Garry Kasparov in a "
        "standard time-control match in 1997 and could evaluate about 200 million "
        "positions per second."
    ),
    (
        "In 2016, AlphaGo's 37th move against Lee Sedol looked unusual to human "
        "experts but became one of the match's celebrated strategic moves."
    ),
    (
        "SQL injection remains a common vulnerability. Parameterized queries are "
        "a standard way to prevent untrusted input from being treated as SQL code."
    ),
    (
        "Peter Shor's 1994 quantum algorithm showed how a sufficiently capable "
        "quantum computer could factor large integers much faster than known "
        "classical methods."
    ),
    (
        "Bitcoin's proof-of-work uses SHA-256, a cryptographic hash function "
        "designed by the U.S. National Security Agency."
    ),
    (
        "Moore's Law is a technology-industry observation, not a law of physics. "
        "In 1965, Gordon Moore predicted that transistor counts would roughly "
        "double every two years."
    ),
    (
        "Brooks's Law says that adding people to a late software project can make "
        "it later, because onboarding and communication take time."
    ),
    (
        "Conway's Law observes that organizations tend to design systems that "
        "mirror their communication structures."
    ),
    (
        "Hofstadter's Law says that a task always takes longer than expected, "
        "even when you account for Hofstadter's Law."
    ),
    (
        "Kernighan's Law jokes that debugging is twice as hard as writing code; "
        "if you write code as cleverly as possible, you may not be able to "
        "debug it."
    ),
    (
        "The P versus NP problem asks whether every problem whose solution can be "
        "checked quickly can also be solved quickly. It is one of the Millennium "
        "Prize Problems."
    ),
    (
        "Alan Turing proved in 1936 that no general algorithm can determine for "
        "every program whether it will eventually halt or run forever."
    ),
    (
        "The Pareto principle is often used as a rule of thumb in software: a "
        "small portion of code may account for much of the runtime or many bugs."
    ),
    (
        "Hyrum's Law says that with enough users, every observable behavior of a "
        "system will eventually be depended on by someone."
    ),
    (
        "Linus's Law says: 'Given enough eyeballs, all bugs are shallow.' It is "
        "often associated with open-source development."
    ),
    (
        "Software developers often spend more time reading and understanding "
        "existing code than writing new code."
    ),
    (
        "A Stack Overflow survey once found a correlation between using spaces "
        "instead of tabs and higher developer salaries; that does not show that "
        "spaces cause higher pay."
    ),
    (
        "GitHub's Arctic Code Vault project stored open-source code on film in "
        "an abandoned coal mine in Svalbard, with the goal of preserving it for "
        "1,000 years."
    ),
    (
        "The Linux kernel contains tens of millions of lines of code and is built "
        "through contributions from developers around the world."
    ),
    (
        'The word "code" comes from the Latin "codex." The word referred to a '
        "book or manuscript before gaining its modern meanings related to rules "
        "and coded messages."
    ),
    (
        "Markus Persson created the first version of Minecraft in Java in about "
        "six days in May 2009."
    ),
    (
        "Ray Tomlinson chose @ in 1971 to separate a user name from a host name "
        "in email addresses; it was uncommon in personal names."
    ),
    (
        'Brian Kernighan used "Hello, World!" in a 1972 tutorial on the B '
        "programming language. The phrase became widely known through later "
        "programming books."
    ),
    (
        "The first computer mouse was made of wood. Douglas Engelbart built it "
        "in 1964 with two metal wheels for horizontal and vertical movement."
    ),
    (
        "The inventors of the B-tree never settled on what the B stands for. "
        "Suggested meanings include balanced, broad, Bayer, and Boeing."
    ),
    (
        "Pressing Ctrl+C in a terminal commonly sends SIGINT, a Unix signal that "
        "asks a running process to interrupt."
    ),
    (
        "A qubit can be in a quantum superposition of 0 and 1; measurement yields "
        "a definite outcome."
    ),
    (
        'A famous computer-science joke says there are only two hard things: '
        '"cache invalidation and naming things"—often followed by off-by-one '
        "errors."
    ),
    (
        "The CERN room 404 story is a myth. HTTP 404 is simply the status code "
        "for Not Found; its first digit places it in the client-error range."
    ),
    (
        "There are hundreds of programming languages, but only a few dozen are "
        "widely used in everyday software development."
    ),
)
PLAYER_COLOR_OPTIONS = (
    ("Mint green", "#59e1a5"),
    ("Sky blue", "#5aa9ff"),
    ("Gold", "#ffd166"),
    ("Lavender", "#c792ea"),
    ("Cyan", "#56cfe1"),
    ("Pink", "#ff8fab"),
    ("Lime", "#a3e635"),
    ("Orange", "#ff9f1c"),
    ("Periwinkle", "#b8c0ff"),
    ("White", "#f4f7fb"),
)
PLAYER_COLORS = tuple(option[1] for option in PLAYER_COLOR_OPTIONS)
PLAYER_COLOR_BY_NAME = dict(PLAYER_COLOR_OPTIONS)
PLAYER_COLOR_NAME_BY_VALUE = {
    color: name for name, color in PLAYER_COLOR_OPTIONS
}
BOT_START_OFFSETS = ((1, 0), (2, 1), (0, 2), (1, 2), (2, 2))
PIXEL_FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "'": ("00100", "00100", "00010", "00000", "00000", "00000", "00000"),
}
class GameRoom:
    def __init__(
        self,
        mode,
        generations_per_round,
        room_code,
        bot_enabled=False,
        max_setup_cells=MAX_SETUP_CELLS,
        round_time_limit_seconds=ROUND_TIME_LIMIT_SECONDS,
        game_time_limit_seconds=GAME_TIME_LIMIT_SECONDS,
        max_turn_cells=DEFAULT_TURN_CELLS,
    ):
        if mode not in ("1v1", "2v2"):
            raise ValueError("Game mode must be 1v1 or 2v2.")
        if not 1 <= generations_per_round <= 100:
            raise ValueError("Generations per round must be between 1 and 100.")
        if not MIN_SETUP_CELLS <= max_setup_cells <= MAX_STARTING_CELLS:
            raise ValueError(
                f"Starting cells must be between {MIN_SETUP_CELLS} and "
                f"{MAX_STARTING_CELLS}."
            )
        if not MIN_ROUND_TIME_SECONDS <= round_time_limit_seconds <= MAX_ROUND_TIME_SECONDS:
            raise ValueError(
                f"Drawing time must be between {MIN_ROUND_TIME_SECONDS} and "
                f"{MAX_ROUND_TIME_SECONDS} seconds."
            )
        if not MIN_GAME_TIME_SECONDS <= game_time_limit_seconds <= MAX_GAME_TIME_SECONDS:
            raise ValueError(
                f"Game time must be between {MIN_GAME_TIME_SECONDS // 60} and "
                f"{MAX_GAME_TIME_SECONDS // 60} minutes."
            )
        if not MIN_TURN_CELLS <= max_turn_cells <= MAX_TURN_CELLS:
            raise ValueError(
                f"Cells per turn must be between {MIN_TURN_CELLS} and "
                f"{MAX_TURN_CELLS}."
            )
        self.mode = mode
        self.bot_enabled = bot_enabled
        self.player_count = 2 if mode == "1v1" else 4
        self.width = 64
        self.height = 40 if mode == "1v1" else 64
        self.generations_per_round = generations_per_round
        self.max_setup_cells = max_setup_cells
        self.round_time_limit_seconds = round_time_limit_seconds
        self.game_time_limit_seconds = game_time_limit_seconds
        self.max_turn_cells = max_turn_cells
        self.room_code = room_code
        self.lock = threading.RLock()
        self.players = []
        self.tokens = {}
        self.cells = {}
        self.phase = "lobby"
        self.current_turn = None
        self.round_number = 0
        self.generation = 0
        self.winner = None
        self.started_at = None
        self.round_deadline = None
        self.round_submissions = {}
        self.message = "Waiting for players to join."
        self.previous_generation_scores = None
        self.reactions = {}

    def _territory(self, x, y):
        if self.mode == "1v1":
            return 0 if x < self.width // 2 else 1
        column = 0 if x < self.width // 2 else 1
        row = 0 if y < self.height // 2 else 1
        return row * 2 + column

    def _team(self, player_index):
        if self.mode == "1v1":
            return player_index
        return player_index % 2

    def _team_cell_counts(self, cells=None):
        cells_to_count = self.cells if cells is None else cells
        counts = {0: 0, 1: 0}
        for x, y in cells_to_count:
            team = self._team(self._territory(x, y))
            counts[team] += 1
        return counts

    def _team_with_most_cells(self):
        current_scores = self._team_cell_counts()
        highest_score = max(current_scores.values())
        leaders = [
            team for team, score in current_scores.items()
            if score == highest_score
        ]
        if len(leaders) == 1:
            return leaders[0], "cell count"

        if self.previous_generation_scores is not None:
            previous_highest = max(self.previous_generation_scores.values())
            previous_leaders = [
                team
                for team, score in self.previous_generation_scores.items()
                if score == previous_highest
            ]
            if len(previous_leaders) == 1:
                return previous_leaders[0], "cell count before the last generation"

        return self.players[0]["team"], "host tie-break"

    def _team_label(self, team):
        if self.mode == "1v1":
            return next(
                player["name"]
                for player in self.players
                if player["team"] == team
            )
        return f"Team {team + 1}"

    def join(self, name, room_code, color=None):
        with self.lock:
            if room_code != self.room_code:
                raise ValueError("That room code is incorrect.")
            clean_name = " ".join(str(name).split())[:20] or f"Player {len(self.players) + 1}"
            used_colors = {player["color"] for player in self.players}
            if color is None:
                color = next(
                    (available for available in PLAYER_COLORS if available not in used_colors),
                    None,
                )
            if color not in PLAYER_COLORS:
                raise ValueError("Choose one of the 10 available player colors.")

            now = time.monotonic()
            reconnecting_player = next(
                (
                    player
                    for player in self.players
                    if not player.get("is_bot")
                    and player["name"] == clean_name
                    and player["color"] == color
                ),
                None,
            )
            if reconnecting_player is not None:
                if self.phase == "finished":
                    raise ValueError("This game has already finished.")
                if (
                    reconnecting_player["connected"]
                    and now - reconnecting_player["last_seen"]
                    < RECONNECT_TIMEOUT_SECONDS
                ):
                    raise ValueError(
                        "A player with this name and color is already connected."
                    )

                player_index = reconnecting_player["index"]
                for existing_token, existing_index in list(self.tokens.items()):
                    if existing_index == player_index:
                        del self.tokens[existing_token]
                token = secrets.token_urlsafe(24)
                self.tokens[token] = player_index
                reconnecting_player["connected"] = True
                reconnecting_player["last_seen"] = now
                if (
                    self.phase == "action"
                    and self.round_submissions.get(player_index, {}).get(
                        "disconnected"
                    )
                ):
                    del self.round_submissions[player_index]
                self.message = f"{clean_name} rejoined the game."
                return {
                    "token": token,
                    "player_index": player_index,
                    "state": self.state(),
                }

            if self.phase != "lobby":
                raise ValueError(
                    "This game has started. Rejoin using your original name and color."
                )
            if len(self.players) >= self.player_count:
                raise ValueError("This game is full.")
            if color in used_colors:
                raise ValueError("That color is already taken. Choose another color.")

            index = len(self.players)
            token = secrets.token_urlsafe(24)
            self.players.append(
                {
                    "index": index,
                    "name": clean_name,
                    "team": self._team(index),
                    "color": color,
                    "alive": True,
                    "connected": True,
                    "last_seen": now,
                }
            )
            self.tokens[token] = index

            if self.bot_enabled:
                for bot_index in range(1, self.player_count):
                    self.players.append(
                        {
                            "index": bot_index,
                            "name": f"Robot {bot_index}",
                            "team": self._team(bot_index),
                            "color": next(
                                available
                                for available in PLAYER_COLORS
                                if available not in {
                                    player["color"] for player in self.players
                                }
                            ),
                            "alive": True,
                            "connected": True,
                            "is_bot": True,
                        }
                    )
                self.phase = "setup"
                self.message = "Draw your starting pattern in your own territory."
            elif len(self.players) == self.player_count:
                self.phase = "setup"
                self.message = "Draw your starting pattern in your own territory."
            else:
                self.message = (
                    f"Waiting for players ({len(self.players)}/{self.player_count})."
                )
            return {"token": token, "player_index": index, "state": self.state()}

    def _authenticated_player(self, token):
        player_index = self.tokens.get(token)
        if player_index is None:
            raise ValueError("The game connection is not authorized.")
        player = self.players[player_index]
        player["last_seen"] = time.monotonic()
        player["connected"] = True
        return player_index

    def _disconnect_player(self, player):
        if not player["connected"]:
            return
        player["connected"] = False
        player["last_seen"] = time.monotonic()
        player_index = player["index"]
        for token, token_player_index in list(self.tokens.items()):
            if token_player_index == player_index:
                del self.tokens[token]
        if self.phase == "action" and player["alive"]:
            self.round_submissions.setdefault(
                player_index,
                {"cells": set(), "color": None, "disconnected": True},
            )
        self.message = f"{player['name']} disconnected; they can rejoin."

    def _mark_stale_players_disconnected(self):
        now = time.monotonic()
        for player in self.players:
            if (
                not player.get("is_bot")
                and player["connected"]
                and now - player["last_seen"] >= RECONNECT_TIMEOUT_SECONDS
            ):
                self._disconnect_player(player)
        if self.phase == "action" and self._all_alive_players_submitted():
            self._resolve_round()

    def start(self, token):
        with self.lock:
            self._finish_if_time_expired()
            player_index = self._authenticated_player(token)
            if player_index != 0:
                raise ValueError("Only the host can start the game.")
            if self.phase != "setup":
                raise ValueError("Wait until all players have joined.")
            if self.bot_enabled:
                for player_index in range(1, self.player_count):
                    if self.mode == "1v1":
                        center_x, center_y = 48, 17
                    else:
                        center_x = 48 if player_index % 2 else 16
                        center_y = 16 if player_index < 2 else 48
                    for offset_x, offset_y in BOT_START_OFFSETS:
                        point = (center_x + offset_x, center_y + offset_y)
                        self.cells[point] = self.players[player_index]["color"]
            self.phase = "action"
            self.started_at = time.monotonic()
            self._begin_round()

    def leave(self, token):
        with self.lock:
            self._finish_if_time_expired()
            player_index = self._authenticated_player(token)
            player = self.players[player_index]
            self._disconnect_player(player)
            if self.phase == "action" and self._all_alive_players_submitted():
                self._resolve_round()

    def submit_stroke(self, token, cells, round_number):
        with self.lock:
            self._finish_if_time_expired()
            self._finish_round_if_expired()
            player_index = self._authenticated_player(token)
            if round_number != self.round_number:
                raise ValueError("This drawing belongs to an earlier round.")
            player = self.players[player_index]
            if not player["alive"]:
                raise ValueError("You have been eliminated.")
            if not isinstance(cells, list):
                raise ValueError("A drawing must be a list of cells.")
            if self.phase == "setup" and (
                not cells or len(cells) > self.max_setup_cells
            ):
                raise ValueError(
                    f"A starting drawing must contain between 1 and "
                    f"{self.max_setup_cells} cells."
                )
            if self.phase == "action" and len(cells) > self.max_turn_cells:
                raise ValueError(
                    f"A round can contain at most {self.max_turn_cells} cells."
                )

            checked_cells = []
            seen = set()
            for point in cells:
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or type(point[0]) is not int
                    or type(point[1]) is not int
                ):
                    raise ValueError("The drawing contains an invalid cell.")
                x, y = point
                if not (0 <= x < self.width and 0 <= y < self.height):
                    raise ValueError("You can only draw inside the game board.")
                seen.add((x, y))
                checked_cells.append((x, y))

            if self.phase == "setup":
                target_area = player_index
                color = player["color"]
                existing_cells = {
                    point
                    for point in self.cells
                    if self._territory(*point) == player_index
                }
                if len(existing_cells | seen) > self.max_setup_cells:
                    raise ValueError(
                        f"Your starting pattern can contain at most "
                        f"{self.max_setup_cells} cells."
                    )
            elif self.phase == "action":
                if player_index in self.round_submissions:
                    raise ValueError("You have already submitted this round.")
                if len(seen) > self.max_turn_cells:
                    raise ValueError(
                        f"A round can contain at most {self.max_turn_cells} cells."
                    )
                if seen:
                    target_area = self._territory(*checked_cells[0])
                    if any(self._territory(*point) != target_area for point in seen):
                        raise ValueError(
                            "One round's drawing must stay in one territory."
                        )
                    if target_area != player_index:
                        if self._team(target_area) == self._team(player_index):
                            raise ValueError(
                                "You can attack opponents, not a teammate."
                            )
                        color = ATTACK_COLOR
                    else:
                        color = player["color"]
                else:
                    color = None
            else:
                raise ValueError("The game is not accepting drawings right now.")

            if seen and any(
                self._territory(x, y) != target_area for x, y in checked_cells
            ):
                raise ValueError("Drawings must stay inside the selected territory.")

            if self.phase == "setup":
                for point in seen:
                    self.cells[point] = color
            else:
                self.round_submissions[player_index] = {
                    "cells": seen,
                    "color": color,
                }
                if self.bot_enabled:
                    self._submit_bot_turn()
                if self._all_alive_players_submitted():
                    self._resolve_round()

    def erase_cells(self, token, cells, round_number):
        with self.lock:
            player_index = self._authenticated_player(token)
            if self.phase != "setup":
                raise ValueError("Cells can only be erased during setup.")
            if round_number != self.round_number:
                raise ValueError("This drawing belongs to an earlier round.")
            if not isinstance(cells, list) or len(cells) > self.max_setup_cells:
                raise ValueError("The eraser request contains invalid cells.")

            for point in cells:
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or type(point[0]) is not int
                    or type(point[1]) is not int
                ):
                    raise ValueError("The eraser request contains an invalid cell.")
                x, y = point
                if (
                    not (0 <= x < self.width and 0 <= y < self.height)
                    or self._territory(x, y) != player_index
                ):
                    raise ValueError("You can only erase cells in your own territory.")
                self.cells.pop((x, y), None)

    def react(self, token, reaction):
        with self.lock:
            self._finish_if_time_expired()
            self._finish_round_if_expired()
            player_index = self._authenticated_player(token)
            if not isinstance(reaction, str) or reaction not in REACTION_EMOJIS:
                raise ValueError("Choose a supported reaction.")
            if self.phase not in ("setup", "action"):
                raise ValueError("Reactions are only available during a game.")
            if not self.players[player_index]["alive"]:
                raise ValueError("You have been eliminated.")
            self.reactions[player_index] = {
                "emoji": REACTION_EMOJIS[reaction],
                "expires_at": time.monotonic() + REACTION_DISPLAY_SECONDS,
            }

    def _begin_round(self):
        self.round_number += 1
        self.current_turn = None
        self.round_deadline = (
            time.monotonic() + self.round_time_limit_seconds
        )
        self.round_submissions = {}
        self.message = (
            f"Round {self.round_number}: all players draw at the same time. "
            f"You have {self.round_time_limit_seconds} seconds."
        )

    def _all_alive_players_submitted(self):
        return all(
            not player["alive"] or player["index"] in self.round_submissions
            for player in self.players
        )

    def _finish_round_if_expired(self):
        if (
            self.phase == "action"
            and self.round_deadline is not None
            and time.monotonic() >= self.round_deadline
        ):
            self._resolve_round()

    def _resolve_round(self):
        if self.bot_enabled:
            self._submit_bot_turn()
        for player_index in sorted(self.round_submissions):
            submission = self.round_submissions[player_index]
            for point in submission["cells"]:
                self.cells[point] = submission["color"]
        self._advance_life()
        if self.phase == "finished":
            return
        self._begin_round()

    def _submit_bot_turn(self):
        if not self.bot_enabled or self.phase != "action":
            return

        for bot_index in range(1, self.player_count):
            if (
                not self.players[bot_index]["alive"]
                or bot_index in self.round_submissions
            ):
                continue

            enemy_areas = [
                area
                for area in range(self.player_count)
                if self._team(area) != self._team(bot_index)
            ]
            has_enemy_cells = any(
                self._territory(*point) in enemy_areas for point in self.cells
            )
            target_area = bot_index
            if enemy_areas and has_enemy_cells and random.random() < 0.35:
                target_area = random.choice(enemy_areas)

            candidates = set()
            for x, y in self.cells:
                if self._territory(x, y) != target_area:
                    continue
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        point = (x + dx, y + dy)
                        if (
                            (dx or dy)
                            and 0 <= point[0] < self.width
                            and 0 <= point[1] < self.height
                            and self._territory(*point) == target_area
                            and point not in self.cells
                        ):
                            candidates.add(point)

            if not candidates:
                candidates = {
                    (x, y)
                    for x in range(self.width)
                    for y in range(self.height)
                    if self._territory(x, y) == target_area
                    and (x, y) not in self.cells
                }

            cells = set(
                random.sample(
                    list(candidates), min(self.max_turn_cells, len(candidates))
                )
            )
            color = (
                ATTACK_COLOR
                if self._team(target_area) != self._team(bot_index)
                else self.players[bot_index]["color"]
            )
            self.round_submissions[bot_index] = {"cells": cells, "color": color}

    def _advance_life(self):
        for _ in range(self.generations_per_round):
            self.previous_generation_scores = self._team_cell_counts()
            neighbor_counts = {}
            for x, y in self.cells:
                area = self._territory(x, y)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        neighbor = (x + dx, y + dy)
                        if (
                            0 <= neighbor[0] < self.width
                            and 0 <= neighbor[1] < self.height
                            and self._territory(*neighbor) == area
                        ):
                            neighbor_counts[neighbor] = (
                                neighbor_counts.get(neighbor, 0) + 1
                            )

            next_cells = {
                point
                for point, count in neighbor_counts.items()
                if count == 3 or (count == 2 and point in self.cells)
            }
            self.cells = {
                point: self.cells.get(point, self.players[self._territory(*point)]["color"])
                for point in next_cells
            }
            self.generation += 1

        for player in self.players:
            if player["alive"] and not any(
                self._territory(x, y) == player["index"] for x, y in self.cells
            ):
                player["alive"] = False

        alive_teams = {player["team"] for player in self.players if player["alive"]}
        if len(alive_teams) <= 1:
            self.phase = "finished"
            self.current_turn = None
            if alive_teams:
                self.winner = next(iter(alive_teams))
                self.message = f"{self._team_label(self.winner)} wins!"
            else:
                self.winner, reason = self._team_with_most_cells()
                self.message = (
                    f"No players survived. {self._team_label(self.winner)} "
                    f"wins by {reason}."
                )

    def _finish_if_time_expired(self):
        if (
            self.phase != "action"
            or self.started_at is None
            or time.monotonic() - self.started_at < self.game_time_limit_seconds
        ):
            return

        self.phase = "finished"
        self.current_turn = None
        self.winner, reason = self._team_with_most_cells()
        self.message = (
            f"Time is up. {self._team_label(self.winner)} wins by {reason}."
        )

    def state(self):
        with self.lock:
            self._mark_stale_players_disconnected()
            self._finish_if_time_expired()
            self._finish_round_if_expired()
            now = time.monotonic()
            self.reactions = {
                player_index: reaction
                for player_index, reaction in self.reactions.items()
                if reaction["expires_at"] > now
            }
            time_remaining = None
            if self.phase == "action" and self.started_at is not None:
                time_remaining = max(
                    0,
                    self.game_time_limit_seconds
                    - int(time.monotonic() - self.started_at),
                )
            round_time_remaining = None
            if self.phase == "action" and self.round_deadline is not None:
                round_time_remaining = max(
                    0, math.ceil(self.round_deadline - time.monotonic())
                )
            return {
                "mode": self.mode,
                "width": self.width,
                "height": self.height,
                "phase": self.phase,
                "players": [
                    {
                        key: value
                        for key, value in player.items()
                        if key != "last_seen"
                    }
                    for player in self.players
                ],
                "cells": [
                    [x, y, color] for (x, y), color in self.cells.items()
                ],
                "current_turn": self.current_turn,
                "round": self.round_number,
                "generation": self.generation,
                "winner": self.winner,
                "message": self.message,
                "generations_per_round": self.generations_per_round,
                "max_setup_cells": self.max_setup_cells,
                "round_time_limit_seconds": self.round_time_limit_seconds,
                "game_time_limit_seconds": self.game_time_limit_seconds,
                "max_turn_cells": self.max_turn_cells,
                "time_remaining": time_remaining,
                "round_time_remaining": round_time_remaining,
                "submitted_players": sorted(self.round_submissions),
                "reactions": [
                    {"player_index": player_index, "emoji": reaction["emoji"]}
                    for player_index, reaction in self.reactions.items()
                ],
                "available_colors": [
                    color
                    for color in PLAYER_COLORS
                    if color not in {player["color"] for player in self.players}
                ],
            }


class _GameRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(10.0)
            raw_request = self.rfile.readline(65537)
            if len(raw_request) > 65536:
                raise ValueError("The request is too large.")
            request = json.loads(raw_request.decode("utf-8"))
            response = self.server.dispatch(request)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            response = {"error": str(error)}
        except (ConnectionError, OSError):
            return

        try:
            self.wfile.write(json.dumps(response).encode("utf-8") + b"\n")
        except (ConnectionError, OSError):
            return


class _GameTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, room):
        self.room = room
        super().__init__(address, _GameRequestHandler)

    def dispatch(self, request):
        if not isinstance(request, dict):
            raise ValueError("Invalid game request.")
        action = request.get("action")
        if action == "join":
            return self.room.join(
                request.get("name", ""),
                request.get("code", ""),
                request.get("color"),
            )
        token = request.get("token", "")
        if action == "state":
            self.room._authenticated_player(token)
            return {"state": self.room.state()}
        if action == "start":
            self.room.start(token)
            return {"state": self.room.state()}
        if action == "leave":
            self.room.leave(token)
            return {"state": self.room.state()}
        if action == "stroke":
            self.room.submit_stroke(
                token, request.get("cells"), request.get("round")
            )
            return {"state": self.room.state()}
        if action == "erase":
            self.room.erase_cells(
                token, request.get("cells"), request.get("round")
            )
            return {"state": self.room.state()}
        if action == "react":
            self.room.react(token, request.get("reaction"))
            return {"state": self.room.state()}
        raise ValueError("Unknown game request.")


class GameServer:
    def __init__(
        self,
        mode,
        generations_per_round=10,
        bind_address="0.0.0.0",
        bot_enabled=False,
        max_setup_cells=MAX_SETUP_CELLS,
        round_time_limit_seconds=ROUND_TIME_LIMIT_SECONDS,
        game_time_limit_seconds=GAME_TIME_LIMIT_SECONDS,
        max_turn_cells=DEFAULT_TURN_CELLS,
    ):
        self.room_code = f"{secrets.randbelow(1_000_000):06d}"
        self.room = GameRoom(
            mode,
            generations_per_round,
            self.room_code,
            bot_enabled=bot_enabled,
            max_setup_cells=max_setup_cells,
            round_time_limit_seconds=round_time_limit_seconds,
            game_time_limit_seconds=game_time_limit_seconds,
            max_turn_cells=max_turn_cells,
        )
        self.server = _GameTCPServer((bind_address, PORT), self.room)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        if self.thread.is_alive():
            self.server.shutdown()
        self.server.server_close()


class GameClient:
    def __init__(self, host, name, room_code, color=None):
        self.host = host
        self.name = name
        self.room_code = room_code
        self.color = color
        self.token = None
        self.player_index = None

    def _request(self, payload):
        with socket.create_connection((self.host, PORT), timeout=2.0) as connection:
            connection.settimeout(2.0)
            with connection.makefile("rwb") as stream:
                stream.write(json.dumps(payload).encode("utf-8") + b"\n")
                stream.flush()
                line = stream.readline(1_000_001)
        if not line:
            raise ConnectionError("The host closed the connection.")
        response = json.loads(line.decode("utf-8"))
        if "error" in response:
            raise ValueError(response["error"])
        return response

    def join(self):
        response = self._request(
            {
                "action": "join",
                "name": self.name,
                "code": self.room_code,
                "color": self.color,
            }
        )
        self.token = response["token"]
        self.player_index = response["player_index"]
        return response["state"]

    def get_state(self):
        return self._request({"action": "state", "token": self.token})["state"]

    def start_game(self):
        return self._request({"action": "start", "token": self.token})["state"]

    def leave_game(self):
        return self._request({"action": "leave", "token": self.token})["state"]

    def submit_stroke(self, cells, round_number):
        return self._request(
            {
                "action": "stroke",
                "token": self.token,
                "cells": cells,
                "round": round_number,
            }
        )["state"]

    def erase_cells(self, cells, round_number):
        return self._request(
            {
                "action": "erase",
                "token": self.token,
                "cells": cells,
                "round": round_number,
            }
        )["state"]

    def react(self, reaction):
        return self._request(
            {
                "action": "react",
                "token": self.token,
                "reaction": reaction,
            }
        )["state"]


def local_ipv4_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("192.0.2.1", 80))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"

LOGGER = logging.getLogger(__name__)

COLUMNS = 60
ROWS = 40
INITIAL_CELL_SIZE = 14
MIN_CELL_SIZE = 4
MAX_CELL_SIZE = 40
SCROLL_PADDING_CELLS = 100
BACKGROUND = "#0b1220"
GRID = "#26354c"
ALIVE = "#59e1a5"
TEXT = "#e7edf7"
MUTED = "#91a0b7"
TOOL_SELECTED_BACKGROUND = "#2563eb"
TOOL_HOVER_BACKGROUND = "#3b82f6"


class GameOfLife:
    def __init__(self, root):
        self.root = root
        self.root.title("Conway's Game of Life")
        self.root.geometry("1000x760")
        self.root.minsize(680, 520)
        self.root.configure(bg=BACKGROUND)

        self.selected_color = ALIVE
        self.live_cells = self.glider()
        self.cell_colors = {cell: self.selected_color for cell in self.live_cells}
        self.generation = 0
        self.running = False
        self.after_id = None
        self.last_painted_cell = None
        self.cell_size = INITIAL_CELL_SIZE
        self.board_left = 0
        self.board_top = 0
        self.scroll_region_update_id = None
        self.updating_scroll_region = False
        self.current_screen = "menu"
        self.main_multiplayer_expanded = False
        self.rules_window = None
        self.options_window = None
        self.multiplayer_server = None
        self.hosted_server = None
        self.multiplayer_client = None
        self.multiplayer_state = None
        self.mp_fact_bag = []
        self.multiplayer_stop = threading.Event()
        self.multiplayer_queue = queue.Queue()
        self.multiplayer_poll_started = False
        self.multiplayer_busy = False
        self.multiplayer_connecting = False
        self.mp_cell_size = 1
        self.mp_board_left = 0
        self.mp_board_top = 0
        self.mp_stroke = set()
        self.mp_last_cell = None
        self.mp_shift_erasing = False
        self._build_ui()

        self.root.bind("<space>", self._on_space)
        self.root.bind("<KeyPress-e>", self._toggle_eraser)
        self.root.bind("<KeyPress-E>", self._toggle_eraser)
        self.root.bind("<Escape>", lambda _event: self._on_escape())
        self.root.bind("<KeyPress-n>", lambda _event: self._run_game_action(self.step))
        self.root.bind("<KeyPress-N>", lambda _event: self._run_game_action(self.step))
        self.root.bind("<KeyPress-c>", lambda _event: self._run_game_action(self.clear))
        self.root.bind("<KeyPress-C>", lambda _event: self._run_game_action(self.clear))
        self.root.bind("<KeyPress-r>", lambda _event: self._run_game_action(self.randomize))
        self.root.bind("<KeyPress-R>", lambda _event: self._run_game_action(self.randomize))
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    @staticmethod
    def _draw_pixel_text(canvas, text, color, pixel_size):
        canvas.delete("all")
        text = text.upper()
        character_widths = [4 if character == " " else 6 for character in text]
        text_width = (sum(character_widths) - 1) * pixel_size
        canvas_width = int(canvas.winfo_width())
        canvas_height = int(canvas.winfo_height())
        if canvas_width <= 1 or canvas_height <= 1:
            return

        x_offset = max(0, (canvas_width - text_width) // 2)
        y_offset = max(0, (canvas_height - 7 * pixel_size) // 2)
        for character, character_width in zip(text, character_widths):
            glyph = PIXEL_FONT.get(character)
            if glyph is not None:
                for row, pattern in enumerate(glyph):
                    for column, pixel in enumerate(pattern):
                        if pixel == "1":
                            left = x_offset + column * pixel_size
                            top = y_offset + row * pixel_size
                            canvas.create_rectangle(
                                left,
                                top,
                                left + pixel_size - 1,
                                top + pixel_size - 1,
                                fill=color,
                                outline="",
                            )
            x_offset += character_width * pixel_size

    def _show_rules(self):
        if self.rules_window is not None and self.rules_window.winfo_exists():
            self.rules_window.lift()
            return

        window = tk.Toplevel(self.root)
        self.rules_window = window
        window.title("Multiplayer Rules")
        window.configure(background=BACKGROUND)
        window.resizable(False, False)
        window.transient(self.root)

        rules = (
            "The host chooses Solo, Duo, or Test server, plus starting cells, "
            "turn time, match length, and the cells-per-turn limit. Defend "
            "your territory or attack opponents (red); teammates cannot "
            "attack each other. Each turn advances 10 generations. You are "
            "eliminated when your starting territory has no live cells; the "
            "last survivor wins. If time runs out, the player or team with "
            "the most cells in its territory wins. Ties use the previous "
            "generation's count, then the host."
        )
        content = ttk.Frame(window, style="Game.TFrame", padding=18)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content,
            text="MULTIPLAYER RULES",
            style="Title.TLabel",
        ).pack(anchor="w", pady=(0, 12))
        ttk.Label(
            content,
            text=rules,
            style="Hint.TLabel",
            wraplength=340,
            justify="left",
        ).pack(anchor="w", fill="x", expand=True)

        def close_window():
            window.destroy()
            self.rules_window = None

        ttk.Button(
            content,
            text="Close",
            style="Game.TButton",
            command=close_window,
        ).pack(anchor="e", pady=(12, 0))
        window.protocol("WM_DELETE_WINDOW", close_window)
        window.geometry("380x340")
        window.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - 380) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 340) // 2
        window.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _show_multiplayer_options(self):
        if self.options_window is not None and self.options_window.winfo_exists():
            self.options_window.lift()
            return

        window = tk.Toplevel(self.root)
        self.options_window = window
        window.title("Multiplayer Options")
        window.configure(background=BACKGROUND)
        window.resizable(False, False)
        window.transient(self.root)

        content = ttk.Frame(window, style="Game.TFrame", padding=18)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content,
            text="MULTIPLAYER OPTIONS",
            style="Title.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        options = (
            (
                "Starting cells (max)",
                self.mp_setup_cells_var,
                MIN_SETUP_CELLS,
                MAX_STARTING_CELLS,
            ),
            (
                "Drawing time (sec.)",
                self.mp_round_time_var,
                MIN_ROUND_TIME_SECONDS,
                MAX_ROUND_TIME_SECONDS,
            ),
            (
                "Match length (min.)",
                self.mp_game_time_var,
                MIN_GAME_TIME_SECONDS // 60,
                MAX_GAME_TIME_SECONDS // 60,
            ),
            (
                "Cells allowed per turn",
                self.mp_turn_cells_var,
                MIN_TURN_CELLS,
                MAX_TURN_CELLS,
            ),
        )
        for row, (label, variable, lower, upper) in enumerate(options, start=1):
            ttk.Label(
                content, text=label, style="Hint.TLabel"
            ).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=5)
            ttk.Spinbox(
                content,
                textvariable=variable,
                from_=lower,
                to=upper,
                width=9,
            ).grid(row=row, column=1, sticky="e", pady=5)

        def close_window():
            window.destroy()
            self.options_window = None

        ttk.Button(
            content,
            text="Close",
            style="Game.TButton",
            command=close_window,
        ).grid(row=5, column=0, columnspan=2, sticky="e", pady=(12, 0))
        window.protocol("WM_DELETE_WINDOW", close_window)
        window.geometry("380x340")
        window.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - 380) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 340) // 2
        window.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build_ui(self):
        style = ttk.Style()
        style.configure("Game.TFrame", background=BACKGROUND)
        style.configure(
            "Title.TLabel",
            background=BACKGROUND,
            foreground=TEXT,
            font=("Segoe UI", 19, "bold"),
        )
        style.configure(
            "Hint.TLabel",
            background=BACKGROUND,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "MultiplayerHint.TLabel",
            background=BACKGROUND,
            foreground=TEXT,
            font=("Segoe UI", 15, "bold"),
        )
        style.configure(
            "Stats.TLabel",
            background=BACKGROUND,
            foreground=TEXT,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Celebration.TLabel",
            background=BACKGROUND,
            foreground="#ffd166",
            font=("Segoe UI", 25, "bold"),
        )
        style.configure(
            "Game.TButton",
            font=("Segoe UI", 10),
            padding=(10, 6),
        )
        style.configure(
            "Mode.TButton",
            font=("Segoe UI", 12, "bold"),
            padding=(18, 12),
        )
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.mode_frame = ttk.Frame(self.root, style="Game.TFrame", padding=24)
        self.mode_frame.grid(row=0, column=0, sticky="nsew")
        self.mode_frame.columnconfigure(0, weight=1)
        self.mode_frame.rowconfigure(0, weight=1)
        mode_content = ttk.Frame(self.mode_frame, style="Game.TFrame")
        mode_content.grid(row=0, column=0)
        title_canvas = tk.Canvas(
            mode_content,
            width=940,
            height=64,
            background=BACKGROUND,
            highlightthickness=0,
        )
        title_canvas.grid(row=0, column=0, columnspan=2, pady=(0, 8))
        title_canvas.bind(
            "<Configure>",
            lambda _event: self._draw_pixel_text(
                title_canvas, "CONWAY'S GAME OF LIFE", ALIVE, 7
            ),
        )
        subtitle_canvas = tk.Canvas(
            mode_content,
            width=940,
            height=56,
            background=BACKGROUND,
            highlightthickness=0,
        )
        subtitle_canvas.grid(row=1, column=0, columnspan=2, pady=(0, 24))
        subtitle_canvas.bind(
            "<Configure>",
            lambda _event: self._draw_pixel_text(
                subtitle_canvas, "CHOOSE HOW YOU WANT TO PLAY", TEXT, 5
            ),
        )
        mode_buttons = ttk.Frame(mode_content, style="Game.TFrame")
        mode_buttons.grid(row=2, column=0, columnspan=2)
        ttk.Button(
            mode_buttons,
            text="Singleplayer",
            style="Mode.TButton",
            command=self.start_singleplayer,
            width=18,
        ).grid(row=0, column=0, padx=10, ipadx=12, ipady=6)
        ttk.Button(
            mode_buttons,
            text="Multiplayer",
            style="Mode.TButton",
            command=self._toggle_main_multiplayer_choices,
            width=18,
        ).grid(row=0, column=1, padx=10, ipadx=12, ipady=6)
        self.main_multiplayer_choices = ttk.Frame(
            mode_buttons, style="Game.TFrame"
        )
        self.main_multiplayer_choices.grid(
            row=1, column=1, pady=(8, 0)
        )
        tk.Button(
            self.main_multiplayer_choices,
            text="Host",
            command=lambda: self._open_multiplayer_form("host"),
            width=12,
            background=ALIVE,
            foreground=BACKGROUND,
            activebackground=ALIVE,
            activeforeground=BACKGROUND,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
        ).grid(row=0, column=0, padx=5)
        tk.Button(
            self.main_multiplayer_choices,
            text="Join",
            command=lambda: self._open_multiplayer_form("join"),
            width=12,
            background=ALIVE,
            foreground=BACKGROUND,
            activebackground=ALIVE,
            activeforeground=BACKGROUND,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
        ).grid(row=0, column=1, padx=5)
        self.main_multiplayer_choices.grid_remove()

        ttk.Button(
            self.mode_frame,
            text="Rules",
            style="Game.TButton",
            command=self._show_rules,
        ).place(relx=1, rely=1, x=-24, y=-24, anchor="se")

        self.multiplayer_frame = ttk.Frame(
            self.root, style="Game.TFrame", padding=24
        )
        self.multiplayer_frame.grid(row=0, column=0, sticky="nsew")
        self.multiplayer_frame.grid_remove()
        self.multiplayer_frame.columnconfigure(0, weight=1)
        self.multiplayer_frame.rowconfigure(0, weight=1)
        multiplayer_content = ttk.Frame(self.multiplayer_frame, style="Game.TFrame")
        multiplayer_content.grid(row=0, column=0)
        for column in range(4):
            multiplayer_content.columnconfigure(column, weight=1)
        self.mp_title_canvas = tk.Canvas(
            multiplayer_content,
            width=620,
            height=82,
            background=BACKGROUND,
            highlightthickness=0,
        )
        self.mp_title_canvas.grid(
            row=0, column=0, columnspan=4, pady=(0, 8)
        )
        self.mp_title_canvas.bind(
            "<Configure>",
            lambda _event: self._draw_pixel_text(
                self.mp_title_canvas, "MULTIPLAYER", ALIVE, 9
            ),
        )
        self.mp_description_label = ttk.Label(
            multiplayer_content,
            text="Wi-Fi/LAN only.",
            style="MultiplayerHint.TLabel",
            wraplength=520,
            justify="center",
        )
        self.mp_description_label.grid(
            row=1, column=0, columnspan=4, pady=(0, 20)
        )
        self.mp_disclaimer_label = ttk.Label(
            self.multiplayer_frame,
            text=(
                "* Share the room code only with people you trust.\n"
                "* Allow Python through Windows Firewall if asked.\n"
                "* Public internet play is not included yet."
            ),
            style="Hint.TLabel",
            justify="left",
            wraplength=320,
        )

        self.mp_name_label = ttk.Label(
            multiplayer_content, text="Your name", style="Hint.TLabel"
        )
        self.mp_name_var = tk.StringVar()
        self.mp_name_entry = ttk.Entry(
            multiplayer_content, textvariable=self.mp_name_var, width=22
        )
        self.mp_name_entry.grid(
            row=2, column=1, columnspan=2, sticky="w", pady=5
        )
        self.mp_mode_label = ttk.Label(
            multiplayer_content, text="Game mode", style="Hint.TLabel"
        )
        self.mp_mode_label.grid(
            row=3, column=0, columnspan=4, sticky="", pady=(8, 0)
        )
        self.mp_mode_var = tk.StringVar(value="Solo")
        self.mp_mode_menu = ttk.Combobox(
            multiplayer_content,
            textvariable=self.mp_mode_var,
            values=("Solo", "Duo", "Test server"),
            state="readonly",
            width=19,
        )
        self.mp_mode_menu.grid(
            row=4, column=0, columnspan=4, sticky="", pady=5
        )

        self.mp_color_label = ttk.Label(
            multiplayer_content, text="Your color", style="Hint.TLabel"
        )
        self.mp_color_var = tk.StringVar(value=PLAYER_COLOR_OPTIONS[0][0])
        self.mp_color_display_var = tk.StringVar()
        self.mp_color_menu = tk.Menubutton(
            multiplayer_content,
            textvariable=self.mp_color_display_var,
            width=23,
            anchor="center",
            background=PLAYER_COLOR_OPTIONS[0][1],
            foreground=BACKGROUND,
            activebackground=PLAYER_COLOR_OPTIONS[0][1],
            activeforeground=BACKGROUND,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 8, "bold"),
            padx=0,
            pady=4,
            cursor="hand2",
        )
        self.mp_color_dropdown = tk.Menu(
            self.mp_color_menu, tearoff=False, activeborderwidth=0
        )
        self.mp_color_menu.configure(menu=self.mp_color_dropdown)
        for color_name, color_value in PLAYER_COLOR_OPTIONS:
            self.mp_color_dropdown.add_command(
                label=color_name,
                background=color_value,
                foreground=BACKGROUND,
                activebackground=color_value,
                activeforeground=BACKGROUND,
                command=lambda name=color_name: self._select_mp_color(name),
            )
        self.mp_color_menu.grid(
            row=6, column=0, columnspan=4, sticky="", pady=5
        )

        self.mp_color_label.grid(
            row=5, column=0, columnspan=4, sticky="", pady=(8, 0)
        )
        self.mp_setup_cells_var = tk.StringVar(value=str(MAX_SETUP_CELLS))
        self.mp_round_time_var = tk.StringVar(value=str(ROUND_TIME_LIMIT_SECONDS))
        self.mp_game_time_var = tk.StringVar(
            value=str(GAME_TIME_LIMIT_SECONDS // 60)
        )
        self.mp_turn_cells_var = tk.StringVar(value=str(DEFAULT_TURN_CELLS))

        self.mp_host_label = ttk.Label(
            multiplayer_content, text="Host address", style="Hint.TLabel"
        )
        self.mp_host_label.grid(row=6, column=0, sticky="e", padx=8, pady=5)
        self.mp_host_var = tk.StringVar()
        self.mp_host_entry = ttk.Entry(
            multiplayer_content, textvariable=self.mp_host_var, width=22
        )
        self.mp_host_entry.grid(row=6, column=1, columnspan=2, sticky="w", pady=5)
        self.mp_code_label = ttk.Label(
            multiplayer_content, text="Room code", style="Hint.TLabel"
        )
        self.mp_code_label.grid(row=7, column=0, sticky="e", padx=8, pady=5)
        self.mp_code_var = tk.StringVar()
        self.mp_code_entry = ttk.Entry(
            multiplayer_content, textvariable=self.mp_code_var, width=22
        )
        self.mp_code_entry.grid(row=7, column=1, columnspan=2, sticky="w", pady=5)
        self.mp_entry_placeholders = {}
        self._set_mp_entry_placeholder(
            self.mp_name_entry, self.mp_name_var, "Your name"
        )
        self._set_mp_entry_placeholder(
            self.mp_host_entry, self.mp_host_var, "Host address"
        )
        self._set_mp_entry_placeholder(
            self.mp_code_entry, self.mp_code_var, "Room code"
        )
        self.current_multiplayer_form = "host"
        self._update_mp_color_button()
        self.mp_host_actions = ttk.Frame(
            multiplayer_content, style="Game.TFrame"
        )
        self.mp_host_button = ttk.Button(
            self.mp_host_actions,
            text="Host game",
            style="Game.TButton",
            command=self._host_multiplayer_game,
        )
        self.mp_host_button.grid(row=0, column=0, padx=5)
        self.mp_options_button = ttk.Button(
            self.mp_host_actions,
            text="Options",
            style="Game.TButton",
            command=self._show_multiplayer_options,
        )
        self.mp_options_button.grid(row=0, column=1, padx=5)
        self.mp_host_actions.grid(
            row=8, column=0, columnspan=4, pady=(14, 5)
        )
        self.mp_join_button = tk.Button(
            multiplayer_content,
            text="Join game",
            command=self._join_multiplayer_game,
            background=ALIVE,
            foreground=BACKGROUND,
            activebackground=ALIVE,
            activeforeground=BACKGROUND,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.mp_join_button.grid(row=8, column=2, sticky="w", pady=(14, 5))
        self.mp_back_button = ttk.Button(
            self.multiplayer_frame,
            text="Back to mode selection",
            style="Game.TButton",
            command=self.show_mode_selection,
        )
        self.mp_back_button.place(
            relx=0, rely=1, x=20, y=-16, anchor="sw"
        )

        self.multiplayer_game_frame = ttk.Frame(
            self.root, style="Game.TFrame", padding=(14, 12)
        )
        self.multiplayer_game_frame.grid(row=0, column=0, sticky="nsew")
        self.multiplayer_game_frame.grid_remove()
        self.multiplayer_game_frame.columnconfigure(0, weight=1)
        self.multiplayer_game_frame.rowconfigure(1, weight=1)
        self.mp_status_label = ttk.Label(
            self.multiplayer_game_frame,
            style="Title.TLabel",
            text="Connecting...",
        )
        self.mp_status_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.mp_canvas = tk.Canvas(
            self.multiplayer_game_frame,
            background=BACKGROUND,
            highlightthickness=1,
            highlightbackground=GRID,
        )
        self.mp_canvas.grid(row=1, column=0, sticky="nsew")
        self.mp_canvas.bind("<Configure>", lambda _event: self._draw_multiplayer_board())
        self.mp_canvas.bind("<Button-1>", self._multiplayer_canvas_click)
        self.mp_canvas.bind("<B1-Motion>", self._multiplayer_canvas_drag)
        self.mp_canvas.bind("<ButtonRelease-1>", self._multiplayer_canvas_release)
        reactions_frame = ttk.Frame(
            self.multiplayer_game_frame, style="Game.TFrame"
        )
        reactions_frame.grid(row=2, column=0, pady=(8, 0))
        for column, reaction in enumerate(("happy", "sad", "angry")):
            tk.Button(
                reactions_frame,
                text=REACTION_EMOJIS[reaction],
                command=lambda selected=reaction: self._send_multiplayer_reaction(
                    selected
                ),
                background=BACKGROUND,
                foreground=TEXT,
                activebackground=BACKGROUND,
                activeforeground=TEXT,
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0,
                font=("Segoe UI Emoji", 20),
                padx=4,
                pady=2,
                cursor="hand2",
            ).grid(row=0, column=column, padx=4)
        mp_controls = ttk.Frame(self.multiplayer_game_frame, style="Game.TFrame")
        mp_controls.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        mp_controls.columnconfigure(0, weight=1)
        mp_actions = ttk.Frame(mp_controls, style="Game.TFrame")
        mp_actions.grid(row=0, column=0, sticky="w")
        self.mp_submit_turn_button = ttk.Button(
            mp_actions,
            text="Submit turn (Space)",
            style="Game.TButton",
            command=self._submit_multiplayer_turn,
            state="disabled",
        )
        self.mp_submit_turn_button.grid(row=0, column=0, padx=(0, 8))
        self.mp_erase_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            mp_actions,
            text="Eraser",
            variable=self.mp_erase_var,
            indicatoron=False,
            selectcolor=TOOL_SELECTED_BACKGROUND,
            background=BACKGROUND,
            foreground=TEXT,
            activebackground=TOOL_HOVER_BACKGROUND,
            activeforeground=TEXT,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6,
        ).grid(row=0, column=1, padx=(0, 8))
        self.mp_navigation_frame = ttk.Frame(mp_controls, style="Game.TFrame")
        self.mp_navigation_frame.grid(row=0, column=1, sticky="e")
        self.mp_start_button = ttk.Button(
            self.mp_navigation_frame,
            text="Start game",
            style="Game.TButton",
            command=self._start_multiplayer_game,
        )
        self.mp_start_button.grid(row=0, column=0, padx=(0, 8))
        self.mp_leave_button = ttk.Button(
            self.mp_navigation_frame,
            text="Leave game",
            style="Game.TButton",
            command=self._leave_multiplayer_game,
        )
        self.mp_leave_button.grid(row=0, column=1)
        self.mp_connection_label = ttk.Label(
            self.multiplayer_game_frame, style="Hint.TLabel", text=""
        )
        self.mp_connection_label.grid(row=5, column=0, sticky="w", pady=(8, 0))
        self.mp_instruction_label = ttk.Label(
            self.multiplayer_game_frame,
            text="During setup, draw or erase in your territory. Each turn, place up to the host's cell limit; press Submit turn or Space. Eraser: E or hold Shift.",
            style="Hint.TLabel",
            anchor="center",
        )
        self.mp_instruction_label.grid(
            row=4, column=0, sticky="ew", pady=(6, 0)
        )

        self.multiplayer_result_frame = ttk.Frame(
            self.root, style="Game.TFrame", padding=32
        )
        self.multiplayer_result_frame.grid(row=0, column=0, sticky="nsew")
        self.multiplayer_result_frame.grid_remove()
        self.multiplayer_result_frame.columnconfigure(0, weight=1)
        self.multiplayer_result_frame.rowconfigure(0, weight=1)
        result_content = ttk.Frame(
            self.multiplayer_result_frame, style="Game.TFrame"
        )
        result_content.grid(row=0, column=0)
        self.mp_result_outcome = ttk.Label(
            result_content, style="Title.TLabel", text=""
        )
        self.mp_result_outcome.grid(row=0, column=0, pady=(0, 12))
        self.mp_result_heading = ttk.Label(
            result_content,
            style="Celebration.TLabel",
            text="",
            justify="center",
            wraplength=700,
        )
        self.mp_result_heading.grid(row=1, column=0, pady=(0, 12))
        self.mp_result_fact = ttk.Label(
            result_content,
            style="Hint.TLabel",
            text="",
            justify="center",
            wraplength=600,
        )
        self.mp_result_fact.grid(row=2, column=0, pady=(0, 24))
        ttk.Button(
            result_content,
            text="Back to start",
            style="Game.TButton",
            command=self._leave_multiplayer_game,
        ).grid(row=3, column=0)
        self.root.after(100, self._process_multiplayer_queue)

        self.game_frame = ttk.Frame(self.root, style="Game.TFrame")
        self.game_frame.grid(row=0, column=0, sticky="nsew")
        self.game_frame.grid_remove()
        self.game_frame.columnconfigure(0, weight=1)
        self.game_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(self.game_frame, style="Game.TFrame", padding=(18, 14, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header, text="CONWAY'S GAME OF LIFE", style="Title.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Draw on an infinite grid. Use the scrollbars to explore and the mouse wheel to zoom.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        board_frame = ttk.Frame(self.game_frame, style="Game.TFrame", padding=(14, 8, 14, 8))
        board_frame.grid(row=1, column=0, sticky="nsew")
        board_frame.rowconfigure(0, weight=1)
        board_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            board_frame,
            background=BACKGROUND,
            highlightthickness=1,
            highlightbackground=GRID,
            xscrollincrement=INITIAL_CELL_SIZE,
            yscrollincrement=INITIAL_CELL_SIZE,
            xscrollcommand=self._on_horizontal_scroll,
            yscrollcommand=self._on_vertical_scroll,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.horizontal_scrollbar = ttk.Scrollbar(
            board_frame, orient="horizontal", command=self._scroll_x
        )
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.vertical_scrollbar = ttk.Scrollbar(
            board_frame, orient="vertical", command=self._scroll_y
        )
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda _event: self._reset_paint())
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda event: self._zoom_at(event, 1.15))
        self.canvas.bind("<Button-5>", lambda event: self._zoom_at(event, 1 / 1.15))

        footer = ttk.Frame(self.game_frame, style="Game.TFrame", padding=(18, 8, 18, 14))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        controls = ttk.Frame(footer, style="Game.TFrame")
        controls.grid(row=0, column=0, sticky="w")
        self.tool_var = tk.StringVar(value="pencil")
        tool_button_style = {
            "background": BACKGROUND,
            "foreground": TEXT,
            "activebackground": TOOL_HOVER_BACKGROUND,
            "activeforeground": TEXT,
            "relief": tk.FLAT,
            "borderwidth": 0,
            "highlightthickness": 0,
            "font": ("Segoe UI", 10, "bold"),
            "width": 10,
            "padx": 12,
            "pady": 7,
        }
        tk.Radiobutton(
            controls,
            text="Pencil",
            variable=self.tool_var,
            value="pencil",
            command=self._set_tool,
            indicatoron=False,
            selectcolor=TOOL_SELECTED_BACKGROUND,
            **tool_button_style,
        ).grid(row=0, column=0, padx=(0, 6))
        tk.Radiobutton(
            controls,
            text="Eraser",
            variable=self.tool_var,
            value="eraser",
            command=self._set_tool,
            indicatoron=False,
            selectcolor=TOOL_SELECTED_BACKGROUND,
            **tool_button_style,
        ).grid(row=0, column=1, padx=6)
        tk.Button(
            controls,
            text="Randomize",
            command=self.randomize,
            **tool_button_style,
        ).grid(row=0, column=2, padx=6)
        tk.Button(
            controls,
            text="Clear",
            command=self.clear,
            **tool_button_style,
        ).grid(row=0, column=3, padx=6)

        toolbox = ttk.Frame(footer, style="Game.TFrame")
        toolbox.grid(
            row=0,
            column=1,
            rowspan=4,
            sticky="n",
            padx=24,
        )
        self.color_wheel = tk.Canvas(
            toolbox,
            width=144,
            height=144,
            background=BACKGROUND,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.color_wheel.grid(row=0, column=0)
        self._render_color_wheel()
        self.color_wheel.bind("<Button-1>", self._choose_wheel_color)
        self.color_wheel.bind("<B1-Motion>", self._choose_wheel_color)

        self.tool_status = ttk.Label(
            footer,
            style="Hint.TLabel",
            text="Tool: pencil (E toggles; hold Shift to erase)",
        )
        self.tool_status.grid(row=2, column=0, sticky="w", pady=(6, 0))

        self.stats_label = ttk.Label(footer, style="Stats.TLabel")
        self.stats_label.grid(row=3, column=0, sticky="w", pady=(6, 0))

        speed_frame = ttk.Frame(footer, style="Game.TFrame")
        speed_frame.grid(row=0, column=2, rowspan=4, sticky="ne", padx=(8, 0))
        ttk.Label(speed_frame, text="Speed", style="Hint.TLabel").grid(
            row=0, column=0, sticky="n"
        )
        self.speed = tk.IntVar(value=10)
        ttk.Scale(
            speed_frame,
            from_=30,
            to=1,
            variable=self.speed,
            orient="vertical",
            length=130,
        ).grid(row=1, column=0, sticky="ns", pady=(4, 0))
        ttk.Label(
            footer,
            text="Space: start/pause   N: skip   R: randomize   C: clear   Scroll: pan   Wheel: zoom",
            style="Hint.TLabel",
        ).grid(row=4, column=0, sticky="w", pady=(9, 0))

        actions = ttk.Frame(footer, style="Game.TFrame")
        actions.grid(row=4, column=1, sticky="s", pady=(9, 0))
        ttk.Button(
            actions,
            text="Mode selection",
            style="Game.TButton",
            command=self.show_mode_selection,
        ).grid(row=0, column=0, padx=(0, 7))
        self.run_button = ttk.Button(
            actions,
            text="Start",
            style="Game.TButton",
            command=self.toggle_running,
        )
        self.run_button.grid(row=0, column=1, padx=7)
        ttk.Button(
            footer,
            text="Skip",
            style="Game.TButton",
            command=self.step,
        ).grid(row=4, column=2, sticky="se", padx=(7, 0), pady=(9, 0))

        self._set_color(self.selected_color)

    def _show_screen(self, frame, name):
        for screen in (
            self.mode_frame,
            self.multiplayer_frame,
            self.game_frame,
            self.multiplayer_game_frame,
            self.multiplayer_result_frame,
        ):
            screen.grid_remove()
        frame.grid(row=0, column=0, sticky="nsew")
        self.current_screen = name

    def start_singleplayer(self):
        self._show_screen(self.game_frame, "game")
        self._update_stats()
        self._draw_board()

    def _toggle_main_multiplayer_choices(self):
        self.main_multiplayer_expanded = not self.main_multiplayer_expanded
        if self.main_multiplayer_expanded:
            self.main_multiplayer_choices.grid()
        else:
            self.main_multiplayer_choices.grid_remove()

    def _set_mp_entry_placeholder(self, entry, variable, placeholder):
        self.mp_entry_placeholders[entry] = placeholder
        variable.set(placeholder)
        entry.configure(foreground=MUTED)
        entry.bind(
            "<FocusIn>", self._clear_mp_entry_placeholder, add="+"
        )
        entry.bind(
            "<FocusOut>", self._restore_mp_entry_placeholder, add="+"
        )

    def _clear_mp_entry_placeholder(self, event):
        entry = event.widget
        if entry.get() == self.mp_entry_placeholders.get(entry):
            entry.delete(0, tk.END)
            entry.configure(foreground=TEXT)

    def _restore_mp_entry_placeholder(self, event):
        entry = event.widget
        if not entry.get().strip():
            entry.insert(0, self.mp_entry_placeholders[entry])
            entry.configure(foreground=MUTED)

    def _mp_entry_value(self, entry, variable):
        value = variable.get().strip()
        if value == self.mp_entry_placeholders.get(entry):
            return ""
        return value

    def _select_mp_color(self, color_name):
        self.mp_color_var.set(color_name)
        self._update_mp_color_button()

    def _update_mp_color_button(self):
        color_name = self.mp_color_var.get()
        color_value = PLAYER_COLOR_BY_NAME[color_name]
        if self.current_multiplayer_form == "join":
            display_text = f"Your color: {color_name}"
        else:
            display_text = color_name
        self.mp_color_display_var.set(display_text)
        self.mp_color_menu.configure(
            background=color_value,
            foreground=BACKGROUND,
            activebackground=color_value,
            activeforeground=BACKGROUND,
        )

    def _open_multiplayer_form(self, form):
        self.main_multiplayer_expanded = False
        self.main_multiplayer_choices.grid_remove()
        self.mp_description_label.configure(text="Wi-Fi/LAN only.")
        self._show_multiplayer_form(form)
        self._show_screen(self.multiplayer_frame, "multiplayer")

    def _hide_multiplayer_form(self):
        self.mp_disclaimer_label.place_forget()
        self.mp_back_button.place_forget()
        for widget in (
            self.mp_name_label,
            self.mp_name_entry,
            self.mp_mode_label,
            self.mp_mode_menu,
            self.mp_color_label,
            self.mp_color_menu,
            self.mp_host_label,
            self.mp_host_entry,
            self.mp_code_label,
            self.mp_code_entry,
            self.mp_join_button,
            self.mp_host_actions,
        ):
            widget.grid_remove()

    def _show_multiplayer_form(self, form):
        self._hide_multiplayer_form()
        self.current_multiplayer_form = form
        self._update_mp_color_button()

        self.mp_back_button.place(
            relx=0, rely=1, x=20, y=-16, anchor="sw"
        )
        self.mp_name_entry.grid(
            row=2, column=0, columnspan=4, sticky="", pady=5
        )

        if form == "host":
            self.mp_mode_label.grid(
                row=3, column=0, columnspan=4, sticky="", pady=(8, 0)
            )
            self.mp_mode_menu.grid(
                row=4, column=0, columnspan=4, sticky="", pady=5
            )
            self.mp_color_label.grid(
                row=5, column=0, columnspan=4, sticky="", pady=(8, 0)
            )
            self.mp_color_menu.grid(
                row=6, column=0, columnspan=4, sticky="", pady=5
            )
            self.mp_host_actions.grid(
                row=7, column=0, columnspan=4, pady=(14, 5)
            )
        else:
            self.mp_color_menu.grid(
                row=3, column=0, columnspan=4, sticky="", pady=5
            )
            self.mp_host_entry.grid(
                row=4, column=0, columnspan=4, sticky="", pady=5
            )
            self.mp_code_entry.grid(
                row=5, column=0, columnspan=4, sticky="", pady=5
            )
            self.mp_join_button.grid(
                row=6, column=1, columnspan=2, sticky="", pady=(14, 5)
            )
            self.mp_disclaimer_label.place(
                relx=1, rely=1, x=-20, y=-16, anchor="se"
            )

    def show_mode_selection(self):
        if self.running:
            self.toggle_running()
        self.main_multiplayer_expanded = False
        self.main_multiplayer_choices.grid_remove()
        self._show_screen(self.mode_frame, "menu")

    def _run_game_action(self, action):
        if self.current_screen == "game":
            action()

    def _leave_multiplayer_game(self):
        client = self.multiplayer_client
        server = self.multiplayer_server
        if server is not None:
            self.hosted_server = server
        self.multiplayer_stop.set()
        self.multiplayer_poll_started = False
        self.multiplayer_client = None
        self.multiplayer_server = None
        self.multiplayer_state = None
        self.mp_erase_var.set(False)
        self.mp_shift_erasing = False
        self.multiplayer_busy = False
        self._set_multiplayer_connecting(False)
        self._show_screen(self.mode_frame, "menu")

        def cleanup():
            if client is not None:
                try:
                    client.leave_game()
                except (OSError, ValueError, ConnectionError) as error:
                    self.multiplayer_queue.put(
                        ("error", f"Could not notify the host that you left: {error}")
                    )
        threading.Thread(target=cleanup, daemon=True).start()

    def _on_escape(self):
        if self.current_screen == "multiplayer" and not self.multiplayer_connecting:
            self.show_mode_selection()

    def _host_multiplayer_game(self):
        name = self._mp_entry_value(
            self.mp_name_entry, self.mp_name_var
        ) or "Player"
        color = self._selected_player_color()
        if color is None or self._existing_hosted_game():
            return
        settings = self._read_host_settings()
        if settings is None:
            return
        (
            mode,
            setup_cells,
            round_seconds,
            game_seconds,
            turn_cells,
            test_server,
        ) = settings
        self._set_multiplayer_connecting(True)
        self.mp_connection_label.configure(
            text=(
                "Starting local test server..."
                if test_server
                else "Starting game host..."
            )
        )
        threading.Thread(
            target=self._host_worker,
            args=(
                mode,
                name,
                color,
                test_server,
                setup_cells,
                round_seconds,
                game_seconds,
                turn_cells,
            ),
            daemon=True,
        ).start()

    def _selected_player_color(self):
        color = PLAYER_COLOR_BY_NAME.get(self.mp_color_var.get())
        if color is None:
            messagebox.showerror(
                "Player color", "Choose one of the 10 available colors.", parent=self.root
            )
        return color

    def _existing_hosted_game(self):
        if self.hosted_server is None or not self.hosted_server.thread.is_alive():
            return False
        messagebox.showerror(
            "Game already hosted",
            "This app is still hosting your previous game. Rejoin it with the "
            "saved host address and room code, or close and reopen the app to "
            "start a new game.",
            parent=self.root,
        )
        return True

    def _read_host_settings(self):
        selected_mode = self.mp_mode_var.get()
        try:
            setup_cells = int(self.mp_setup_cells_var.get())
            round_seconds = int(self.mp_round_time_var.get())
            game_minutes = int(self.mp_game_time_var.get())
            turn_cells = int(self.mp_turn_cells_var.get())
        except ValueError:
            messagebox.showerror(
                "Game settings",
                "Enter whole numbers for all game settings.",
                parent=self.root,
            )
            return None

        if selected_mode not in ("Solo", "Duo", "Test server"):
            messagebox.showerror(
                "Game settings",
                "Choose Solo, Duo, or Test server.",
                parent=self.root,
            )
            return None
        if not MIN_SETUP_CELLS <= setup_cells <= MAX_STARTING_CELLS:
            messagebox.showerror(
                "Game settings",
                f"Starting cells must be between {MIN_SETUP_CELLS} and "
                f"{MAX_STARTING_CELLS}.",
                parent=self.root,
            )
            return None
        if not MIN_ROUND_TIME_SECONDS <= round_seconds <= MAX_ROUND_TIME_SECONDS:
            messagebox.showerror(
                "Game settings",
                f"Drawing time must be between {MIN_ROUND_TIME_SECONDS} and "
                f"{MAX_ROUND_TIME_SECONDS} seconds.",
                parent=self.root,
            )
            return None
        min_game_minutes = MIN_GAME_TIME_SECONDS // 60
        max_game_minutes = MAX_GAME_TIME_SECONDS // 60
        if not min_game_minutes <= game_minutes <= max_game_minutes:
            messagebox.showerror(
                "Game settings",
                f"Game length must be between {min_game_minutes} and "
                f"{max_game_minutes} minutes.",
                parent=self.root,
            )
            return None
        if not MIN_TURN_CELLS <= turn_cells <= MAX_TURN_CELLS:
            messagebox.showerror(
                "Game settings",
                f"Cells per turn must be between {MIN_TURN_CELLS} and "
                f"{MAX_TURN_CELLS}.",
                parent=self.root,
            )
            return None
        mode = "2v2" if selected_mode == "Duo" else "1v1"
        test_server = selected_mode == "Test server"
        return (
            mode,
            setup_cells,
            round_seconds,
            game_minutes * 60,
            turn_cells,
            test_server,
        )

    def _host_worker(
        self,
        mode,
        name,
        color,
        test_server=False,
        setup_cells=MAX_SETUP_CELLS,
        round_seconds=ROUND_TIME_LIMIT_SECONDS,
        game_seconds=GAME_TIME_LIMIT_SECONDS,
        turn_cells=DEFAULT_TURN_CELLS,
    ):
        server = None
        try:
            host_address = "127.0.0.1" if test_server else local_ipv4_address()
            server = GameServer(
                mode,
                generations_per_round=10,
                bind_address=host_address,
                bot_enabled=test_server,
                max_setup_cells=setup_cells,
                round_time_limit_seconds=round_seconds,
                game_time_limit_seconds=game_seconds,
                max_turn_cells=turn_cells,
            )
            server.start()
            client = GameClient(host_address, name, server.room_code, color)
            state = client.join()
            self.multiplayer_queue.put(
                (
                    "connected",
                    {
                        "server": server,
                        "client": client,
                        "state": state,
                        "host_address": host_address,
                        "room_code": server.room_code,
                        "connection": (
                            ""
                            if test_server
                            else (
                                f"Host address: {host_address}  "
                                f"Room code: {server.room_code}"
                            )
                        ),
                    },
                )
            )
        except (OSError, ValueError, ConnectionError) as error:
            if server is not None:
                server.close()
            self.multiplayer_queue.put(("error", f"Could not host game: {error}"))

    def _join_multiplayer_game(self):
        host = self._mp_entry_value(self.mp_host_entry, self.mp_host_var)
        room_code = self._mp_entry_value(self.mp_code_entry, self.mp_code_var)
        name = self._mp_entry_value(
            self.mp_name_entry, self.mp_name_var
        ) or "Player"
        color = self._selected_player_color()
        if color is None:
            return
        if not host or not room_code:
            messagebox.showerror(
                "Multiplayer",
                "Enter the host address and room code.",
                parent=self.root,
            )
            return
        self._set_multiplayer_connecting(True)
        self.mp_connection_label.configure(text=f"Connecting to {host}...")
        threading.Thread(
            target=self._join_worker,
            args=(host, name, room_code, color),
            daemon=True,
        ).start()

    def _join_worker(self, host, name, room_code, color):
        try:
            client = GameClient(host, name, room_code, color)
            state = client.join()
            self.multiplayer_queue.put(
                (
                    "connected",
                    {
                        "server": None,
                        "client": client,
                        "state": state,
                        "host_address": host,
                        "room_code": room_code,
                        "connection": f"Connected to {host}",
                    },
                )
            )
        except (OSError, ValueError, ConnectionError) as error:
            self.multiplayer_queue.put(("error", f"Could not join game: {error}"))

    def _set_multiplayer_connecting(self, connecting):
        self.multiplayer_connecting = connecting
        state = "disabled" if connecting else "normal"
        self.mp_host_button.configure(state=state)
        self.mp_join_button.configure(state=state)
        self.mp_options_button.configure(state=state)
        self.mp_back_button.configure(state=state)

    def _start_multiplayer_polling(self):
        if self.multiplayer_poll_started:
            return
        client = self.multiplayer_client
        if client is None:
            return
        self.multiplayer_poll_started = True
        self.multiplayer_stop = threading.Event()
        threading.Thread(
            target=self._multiplayer_poll_worker,
            args=(client, self.multiplayer_stop),
            daemon=True,
        ).start()

    def _multiplayer_poll_worker(self, client, stop_event):
        while not stop_event.is_set():
            try:
                state = client.get_state()
                self.multiplayer_queue.put(("state", state))
            except (OSError, ValueError, ConnectionError) as error:
                self.multiplayer_queue.put(("error", f"Connection lost: {error}"))
                return
            stop_event.wait(0.5)

    def _process_multiplayer_queue(self):
        try:
            while True:
                kind, payload = self.multiplayer_queue.get_nowait()
                if kind == "connected":
                    self.multiplayer_server = payload["server"]
                    if self.multiplayer_server is not None:
                        self.hosted_server = self.multiplayer_server
                    self.multiplayer_client = payload["client"]
                    self.multiplayer_state = payload["state"]
                    self.mp_host_var.set(payload["host_address"])
                    self.mp_code_var.set(payload["room_code"])
                    self._set_multiplayer_connecting(False)
                    self.mp_connection_label.configure(text=payload["connection"])
                    self.mp_start_button.configure(state="normal")
                    self._show_screen(self.multiplayer_game_frame, "multiplayer_game")
                    self._start_multiplayer_polling()
                    self._draw_multiplayer_board()
                elif kind == "state":
                    if self.multiplayer_client is None:
                        continue
                    previous_phase = (
                        self.multiplayer_state["phase"]
                        if self.multiplayer_state is not None
                        else None
                    )
                    previous_round = (
                        self.multiplayer_state["round"]
                        if self.multiplayer_state is not None
                        else None
                    )
                    if (
                        payload["phase"] != previous_phase
                        or payload["round"] != previous_round
                        or (
                            payload["phase"] == "action"
                            and self.multiplayer_client.player_index
                            in payload["submitted_players"]
                        )
                    ):
                        self.mp_stroke.clear()
                        self.mp_last_cell = None
                    self.multiplayer_state = payload
                    self._draw_multiplayer_board()
                elif kind == "action_done":
                    if self.multiplayer_client is None:
                        continue
                    self.multiplayer_state = payload
                    self.multiplayer_busy = False
                    self.mp_stroke.clear()
                    self.mp_last_cell = None
                    self._draw_multiplayer_board()
                elif kind == "action_error":
                    self.multiplayer_busy = False
                    self.mp_connection_label.configure(
                        text=f"Action failed: {payload}"
                    )
                    self._draw_multiplayer_board()
                elif kind == "reaction_error":
                    self.mp_connection_label.configure(
                        text=f"Reaction failed: {payload}"
                    )
                elif kind == "error":
                    if self.current_screen == "multiplayer_game":
                        self.multiplayer_busy = False
                        self.mp_connection_label.configure(text=str(payload))
                        self._draw_multiplayer_board()
                    else:
                        self._set_multiplayer_connecting(False)
                        self.mp_connection_label.configure(text=str(payload))
                        if self.current_screen in ("menu", "multiplayer"):
                            messagebox.showerror(
                                "Multiplayer", str(payload), parent=self.root
                            )
        except queue.Empty:
            pass
        self.root.after(100, self._process_multiplayer_queue)

    def _send_multiplayer_action(self, action, cells=None, round_number=None):
        if self.multiplayer_busy or self.multiplayer_client is None:
            return
        self.multiplayer_busy = True
        self.mp_start_button.configure(state="disabled")
        self.mp_submit_turn_button.configure(state="disabled")
        client = self.multiplayer_client

        def send():
            try:
                if action == "start":
                    state = client.start_game()
                elif action == "erase":
                    state = client.erase_cells(cells, round_number)
                else:
                    state = client.submit_stroke(cells, round_number)
                self.multiplayer_queue.put(("action_done", state))
            except (OSError, ValueError, ConnectionError) as error:
                self.multiplayer_queue.put(("action_error", str(error)))

        threading.Thread(target=send, daemon=True).start()

    def _send_multiplayer_reaction(self, reaction):
        if (
            self.multiplayer_client is None
            or self.multiplayer_state is None
            or self.multiplayer_state["phase"] not in ("setup", "action")
        ):
            return
        client = self.multiplayer_client

        def send():
            try:
                client.react(reaction)
            except (OSError, ValueError, ConnectionError) as error:
                self.multiplayer_queue.put(("reaction_error", str(error)))

        threading.Thread(target=send, daemon=True).start()

    def _start_multiplayer_game(self):
        if (
            self.multiplayer_state is None
            or self.multiplayer_client is None
            or self.multiplayer_client.player_index != 0
        ):
            return
        self._send_multiplayer_action("start")

    @staticmethod
    def _team_for_player(player_index, mode):
        return player_index if mode == "1v1" else player_index % 2

    def _mp_territory_at(self, x, y):
        state = self.multiplayer_state
        if state["mode"] == "1v1":
            return 0 if x < state["width"] // 2 else 1
        column = 0 if x < state["width"] // 2 else 1
        row = 0 if y < state["height"] // 2 else 1
        return row * 2 + column

    def _mp_can_draw_cell(self, cell):
        state = self.multiplayer_state
        player_index = self.multiplayer_client.player_index
        target = self._mp_territory_at(*cell)
        if state["phase"] == "setup":
            return target == player_index
        if (
            state["phase"] != "action"
            or player_index in state["submitted_players"]
        ):
            return False
        if target == player_index:
            return True
        return self._team_for_player(target, state["mode"]) != self._team_for_player(
            player_index, state["mode"]
        )

    def _mp_drawing_area(self):
        if not self.mp_stroke:
            return None
        return self._mp_territory_at(*next(iter(self.mp_stroke)))

    def _mp_setup_cells(self):
        state = self.multiplayer_state
        player_index = self.multiplayer_client.player_index
        return {
            (x, y)
            for x, y, _color in state["cells"]
            if self._mp_territory_at(x, y) == player_index
        }

    def _mp_setup_cell_count(self):
        return len(self._mp_setup_cells() | self.mp_stroke)

    def _mp_cell_at(self, event):
        if self.multiplayer_state is None or self.mp_cell_size <= 0:
            return None
        x = int((event.x - self.mp_board_left) // self.mp_cell_size)
        y = int((event.y - self.mp_board_top) // self.mp_cell_size)
        if (
            0 <= x < self.multiplayer_state["width"]
            and 0 <= y < self.multiplayer_state["height"]
        ):
            return x, y
        return None

    def _multiplayer_canvas_click(self, event):
        if self.multiplayer_state is None or self.multiplayer_busy:
            return
        player_index = self.multiplayer_client.player_index
        state = self.multiplayer_state
        if state["phase"] == "lobby":
            return
        if (
            state["phase"] == "action"
            and player_index in state["submitted_players"]
        ):
            return
        cell = self._mp_cell_at(event)
        if cell is None or not self._mp_can_draw_cell(cell):
            return
        shift_held = self._shift_held(event)
        self.mp_shift_erasing = shift_held
        if self.mp_erase_var.get() or shift_held:
            if state["phase"] == "setup":
                if cell in self.mp_stroke:
                    self.mp_stroke.discard(cell)
                elif cell in self._mp_setup_cells():
                    self.mp_stroke.add(cell)
            else:
                self.mp_stroke.discard(cell)
            self.mp_last_cell = cell
            self._draw_multiplayer_board()
            return
        if cell in self.mp_stroke:
            self.mp_last_cell = cell
            return
        state = self.multiplayer_state
        if state["phase"] == "setup":
            if (
                len(self._mp_setup_cells() | self.mp_stroke | {cell})
                > self.multiplayer_state["max_setup_cells"]
            ):
                return
            self.mp_stroke.add(cell)
            self.mp_last_cell = cell
            self._draw_multiplayer_board()
            return
        if (
            len(self.mp_stroke) >= state["max_turn_cells"]
            or (
                self._mp_drawing_area() is not None
                and self._mp_territory_at(*cell) != self._mp_drawing_area()
            )
        ):
            return
        self.mp_stroke.add(cell)
        self.mp_last_cell = cell
        self._draw_multiplayer_board()

    def _multiplayer_canvas_drag(self, event):
        if self.multiplayer_busy or (
            not self.mp_stroke
            and not self.mp_erase_var.get()
            and not self.mp_shift_erasing
        ):
            return
        cell = self._mp_cell_at(event)
        if self.mp_erase_var.get() or self.mp_shift_erasing:
            if (
                cell is None
                or cell == self.mp_last_cell
                or not self._mp_can_draw_cell(cell)
            ):
                return
            if self.multiplayer_state["phase"] == "setup":
                if cell in self._mp_setup_cells():
                    self.mp_stroke.add(cell)
            else:
                self.mp_stroke.discard(cell)
            self.mp_last_cell = cell
            self._draw_multiplayer_board()
            return
        if (
            cell is None
            or cell == self.mp_last_cell
            or cell in self.mp_stroke
            or not self._mp_can_draw_cell(cell)
            or (
                self._mp_drawing_area() is not None
                and self._mp_territory_at(*cell) != self._mp_drawing_area()
            )
            or (
                self.multiplayer_state["phase"] == "setup"
                and self._mp_setup_cell_count()
                >= self.multiplayer_state["max_setup_cells"]
            )
            or (
                self.multiplayer_state["phase"] == "action"
                and len(self.mp_stroke)
                >= self.multiplayer_state["max_turn_cells"]
            )
        ):
            return
        self.mp_stroke.add(cell)
        self.mp_last_cell = cell
        self._draw_multiplayer_board()

    def _multiplayer_canvas_release(self, _event):
        erase_stroke = self.mp_erase_var.get() or self.mp_shift_erasing
        self.mp_shift_erasing = False
        if not self.mp_stroke:
            return
        self.mp_last_cell = None
        if self.multiplayer_state["phase"] == "setup":
            cells = [[x, y] for x, y in self.mp_stroke]
            self.mp_stroke.clear()
            self._send_multiplayer_action(
                "erase" if erase_stroke else "stroke",
                cells,
                self.multiplayer_state["round"],
            )
        elif self.mp_stroke:
            self.mp_submit_turn_button.configure(state="normal")

    def _submit_multiplayer_turn(self):
        if (
            self.multiplayer_busy
            or self.multiplayer_state is None
            or self.multiplayer_client is None
            or self.multiplayer_state["phase"] != "action"
            or self.multiplayer_client.player_index
            in self.multiplayer_state["submitted_players"]
        ):
            return
        cells = [[x, y] for x, y in self.mp_stroke]
        self._send_multiplayer_action(
            "stroke", cells, self.multiplayer_state["round"]
        )

    def _draw_multiplayer_board(self):
        if self.multiplayer_state is None or not hasattr(self, "mp_canvas"):
            return
        state = self.multiplayer_state
        if state["phase"] == "finished":
            self._show_multiplayer_result(state)
            return
        canvas = self.mp_canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        board_columns = state["width"]
        board_rows = state["height"]
        self.mp_cell_size = min(width / board_columns, height / board_rows)
        board_width = self.mp_cell_size * board_columns
        board_height = self.mp_cell_size * board_rows
        self.mp_board_left = (width - board_width) / 2
        self.mp_board_top = (height - board_height) / 2
        canvas.delete("all")

        for column in range(board_columns + 1):
            x = self.mp_board_left + column * self.mp_cell_size
            boundary = column == board_columns // 2
            canvas.create_line(
                x,
                self.mp_board_top,
                x,
                self.mp_board_top + board_height,
                fill=TEXT if boundary else GRID,
                width=2 if boundary else 1,
            )
        for row in range(board_rows + 1):
            y = self.mp_board_top + row * self.mp_cell_size
            boundary = state["mode"] == "2v2" and row == board_rows // 2
            canvas.create_line(
                self.mp_board_left,
                y,
                self.mp_board_left + board_width,
                y,
                fill=TEXT if boundary else GRID,
                width=2 if boundary else 1,
            )

        inset = min(1.5, self.mp_cell_size * 0.12)
        for x, y, color in state["cells"]:
            left = self.mp_board_left + x * self.mp_cell_size + inset
            top = self.mp_board_top + y * self.mp_cell_size + inset
            canvas.create_rectangle(
                left,
                top,
                left + self.mp_cell_size - 2 * inset,
                top + self.mp_cell_size - 2 * inset,
                fill=color,
                outline="",
            )

        for x, y in self.mp_stroke:
            target = self._mp_territory_at(x, y)
            player_index = self.multiplayer_client.player_index
            left = self.mp_board_left + x * self.mp_cell_size + inset
            top = self.mp_board_top + y * self.mp_cell_size + inset
            if (
                (self.mp_erase_var.get() or self.mp_shift_erasing)
                and state["phase"] == "setup"
            ):
                canvas.create_rectangle(
                    left,
                    top,
                    left + self.mp_cell_size - 2 * inset,
                    top + self.mp_cell_size - 2 * inset,
                    fill=BACKGROUND,
                    outline=ATTACK_COLOR,
                    width=2,
                )
            else:
                color = (
                    ATTACK_COLOR
                    if target != player_index
                    else state["players"][player_index]["color"]
                )
                canvas.create_rectangle(
                    left,
                    top,
                    left + self.mp_cell_size - 2 * inset,
                    top + self.mp_cell_size - 2 * inset,
                    fill=color,
                    outline="",
                )

        area_centers = (
            ((board_columns // 4, board_rows // 2), (3 * board_columns // 4, board_rows // 2))
            if state["mode"] == "1v1"
            else (
                (board_columns // 4, board_rows // 4),
                (3 * board_columns // 4, board_rows // 4),
                (board_columns // 4, 3 * board_rows // 4),
                (3 * board_columns // 4, 3 * board_rows // 4),
            )
        )
        labels = []
        for player in state["players"]:
            center_x, center_y = area_centers[player["index"]]
            label = f"{player['name']}  (Team {player['team'] + 1})"
            if not player["alive"]:
                label += " - OUT"
            if not player.get("connected", True):
                label += " - OFFLINE"
            labels.append((center_x, center_y, label, player["color"]))
        for x, y, label, color in labels:
            canvas.create_text(
                self.mp_board_left + x * self.mp_cell_size,
                self.mp_board_top + y * self.mp_cell_size,
                text=label,
                fill=color,
                font=("Segoe UI", 10, "bold"),
            )
        for reaction in state["reactions"]:
            center_x, center_y = area_centers[reaction["player_index"]]
            canvas.create_text(
                self.mp_board_left + center_x * self.mp_cell_size,
                self.mp_board_top + (center_y - 3) * self.mp_cell_size,
                text=reaction["emoji"],
                fill=TEXT,
                font=("Segoe UI Emoji", 20, "bold"),
            )

        self.mp_status_label.configure(text=state["message"])
        player_index = self.multiplayer_client.player_index
        if state["phase"] == "setup":
            setup_count = self._mp_setup_cell_count()
            self.mp_status_label.configure(
                text=(
                    f"{state['message']}  "
                    f"Starting cells: {setup_count}/{state['max_setup_cells']}"
                )
            )
        elif state["phase"] == "action":
            submitted_count = len(state["submitted_players"])
            active_count = sum(player["alive"] for player in state["players"])
            seconds_left = state["round_time_remaining"]
            local_status = (
                "Turn submitted."
                if player_index in state["submitted_players"]
                else (
                    f"My cells: {len(self.mp_stroke)}/"
                    f"{state['max_turn_cells']}."
                )
            )
            self.mp_status_label.configure(
                text=f"{state['message']}  {local_status} "
                f"Submitted: {submitted_count}/{active_count}. "
                f"Time left: {seconds_left}s."
            )
        if state["time_remaining"] is not None:
            minutes, seconds = divmod(state["time_remaining"], 60)
            status_text = self.mp_status_label.cget("text")
            self.mp_status_label.configure(
                text=f"{status_text}  Time left: {minutes:02d}:{seconds:02d}"
            )
        self.mp_submit_turn_button.configure(
            state="normal"
            if state["phase"] == "action"
            and player_index not in state["submitted_players"]
            and not self.multiplayer_busy
            else "disabled"
        )
        if state["phase"] == "setup":
            self.mp_start_button.configure(
                state="normal"
                if self.multiplayer_client.player_index == 0
                and not self.multiplayer_busy
                else "disabled",
                text="Start game (host)",
            )
        elif state["phase"] == "lobby":
            self.mp_start_button.configure(
                state="disabled", text="Waiting for players"
            )
        else:
            self.mp_start_button.configure(state="disabled", text="Game in progress")

    def _next_multiplayer_fact(self):
        if not self.mp_fact_bag:
            self.mp_fact_bag = random.sample(
                MULTIPLAYER_FACTS, len(MULTIPLAYER_FACTS)
            )
        return self.mp_fact_bag.pop()

    def _show_multiplayer_result(self, state):
        if self.current_screen == "multiplayer_result":
            return

        winner = state["winner"]
        players = state["players"]
        if winner is None:
            outcome_text = "YOU LOSE!"
            result_messages = MULTIPLAYER_LOSS_MESSAGES
        else:
            winning_players = [
                player for player in players if player["team"] == winner
            ]
            is_winner = any(
                player["index"] == self.multiplayer_client.player_index
                for player in winning_players
            )
            outcome_text = "YOU WIN!" if is_winner else "YOU LOSE!"
            result_messages = (
                MULTIPLAYER_WIN_MESSAGES
                if is_winner
                else MULTIPLAYER_LOSS_MESSAGES
            )

        self.mp_result_outcome.configure(text=outcome_text)
        self.mp_result_heading.configure(text=random.choice(result_messages))
        self.mp_result_fact.configure(
            text=f"Random fact: {self._next_multiplayer_fact()}"
        )
        self._show_screen(self.multiplayer_result_frame, "multiplayer_result")

    def _set_color(self, color):
        self.selected_color = color
        if not hasattr(self, "color_wheel"):
            return

        red, green, blue = (
            int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)
        )
        hue, saturation, _value = colorsys.rgb_to_hsv(red, green, blue)
        center = self.color_wheel_size / 2
        radius = self.color_wheel_radius * saturation
        angle = hue * 2 * math.pi
        x = center + radius * math.cos(angle)
        y = center + radius * math.sin(angle)
        self.color_wheel.delete("selection")
        self.color_wheel.create_oval(
            x - 6,
            y - 6,
            x + 6,
            y + 6,
            outline="#000000",
            width=3,
            tags="selection",
        )
        self.color_wheel.create_oval(
            x - 4,
            y - 4,
            x + 4,
            y + 4,
            outline="#ffffff",
            width=1,
            tags="selection",
        )

    def _set_tool(self):
        self.tool_status.configure(
            text=f"Tool: {self.tool_var.get()} (E toggles; hold Shift to erase)"
        )

    def _toggle_eraser(self, _event=None):
        if self.current_screen == "game":
            self.tool_var.set(
                "pencil" if self.tool_var.get() == "eraser" else "eraser"
            )
            self._set_tool()
        elif self.current_screen == "multiplayer_game":
            self.mp_erase_var.set(not self.mp_erase_var.get())
            self._draw_multiplayer_board()
        return "break"

    @staticmethod
    def _shift_held(event):
        return bool(event.state & 0x0001)

    def _render_color_wheel(self):
        self.color_wheel_size = 144
        self.color_wheel_radius = 62
        center = self.color_wheel_size / 2
        photo = tk.PhotoImage(
            master=self.root,
            width=self.color_wheel_size,
            height=self.color_wheel_size,
        )
        background_rgb = BACKGROUND
        for y in range(self.color_wheel_size):
            row = []
            dy = (y - center) / self.color_wheel_radius
            for x in range(self.color_wheel_size):
                dx = (x - center) / self.color_wheel_radius
                distance = math.hypot(dx, dy)
                if distance > 1:
                    row.append(background_rgb)
                    continue
                hue = math.atan2(dy, dx) / (2 * math.pi) % 1
                saturation = min(1, distance)
                rgb = colorsys.hsv_to_rgb(hue, saturation, 1)
                row.append(
                    "#"
                    + "".join(f"{round(channel * 255):02x}" for channel in rgb)
                )
            photo.put("{" + " ".join(row) + "}", (0, y))
        self.color_wheel_image = photo
        self.color_wheel.create_image(
            0, 0, image=photo, anchor="nw", tags="wheel"
        )

    def _choose_wheel_color(self, event):
        center = self.color_wheel_size / 2
        dx = event.x - center
        dy = event.y - center
        distance = math.hypot(dx, dy)
        saturation = min(1, distance / self.color_wheel_radius)
        hue = math.atan2(dy, dx) / (2 * math.pi) % 1
        rgb = colorsys.hsv_to_rgb(hue, saturation, 1)
        self._set_color(
            "#" + "".join(f"{round(channel * 255):02x}" for channel in rgb)
        )

    @staticmethod
    def glider():
        center_x = COLUMNS // 2
        center_y = ROWS // 2
        offsets = ((1, 0), (2, 1), (0, 2), (1, 2), (2, 2))
        return {(center_x + x, center_y + y) for x, y in offsets}

    def _on_canvas_configure(self, _event):
        self._draw_board()
        self._schedule_scroll_region_update()

    def _on_horizontal_scroll(self, first, last):
        self.horizontal_scrollbar.set(first, last)
        if not self.updating_scroll_region:
            self._schedule_scroll_region_update()

    def _on_vertical_scroll(self, first, last):
        self.vertical_scrollbar.set(first, last)
        if not self.updating_scroll_region:
            self._schedule_scroll_region_update()

    def _scroll_x(self, *args):
        self.canvas.xview(*args)
        self._draw_board()
        self._schedule_scroll_region_update()

    def _scroll_y(self, *args):
        self.canvas.yview(*args)
        self._draw_board()
        self._schedule_scroll_region_update()

    def _schedule_scroll_region_update(self):
        if self.scroll_region_update_id is None:
            self.scroll_region_update_id = self.root.after_idle(
                self._update_scroll_region
            )

    def _update_scroll_region(self, view_origin=None):
        self.scroll_region_update_id = None
        if not self.canvas.winfo_ismapped():
            return

        cell_size = self.cell_size
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        if view_origin is None:
            view_left = self.canvas.canvasx(0)
            view_top = self.canvas.canvasy(0)
        else:
            view_left = view_origin[0] * cell_size
            view_top = view_origin[1] * cell_size

        padding = SCROLL_PADDING_CELLS
        min_column = int(view_left // cell_size) - padding
        min_row = int(view_top // cell_size) - padding
        max_column = int((view_left + width) // cell_size) + padding
        max_row = int((view_top + height) // cell_size) + padding
        if self.live_cells:
            min_column = min(min_column, min(x for x, _ in self.live_cells) - padding)
            min_row = min(min_row, min(y for _, y in self.live_cells) - padding)
            max_column = max(max_column, max(x for x, _ in self.live_cells) + padding)
            max_row = max(max_row, max(y for _, y in self.live_cells) + padding)

        x1 = min_column * cell_size
        y1 = min_row * cell_size
        x2 = (max_column + 1) * cell_size
        y2 = (max_row + 1) * cell_size
        self.updating_scroll_region = True
        try:
            self.canvas.configure(scrollregion=(x1, y1, x2, y2))
            max_left = max(x1, x2 - width)
            max_top = max(y1, y2 - height)
            view_left = min(max(view_left, x1), max_left)
            view_top = min(max(view_top, y1), max_top)
            self.canvas.xview_moveto((view_left - x1) / (x2 - x1))
            self.canvas.yview_moveto((view_top - y1) / (y2 - y1))
        finally:
            self.updating_scroll_region = False
        self._draw_board()

    def _draw_board(self):
        if not hasattr(self, "canvas"):
            return
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        self.canvas.delete("all")
        cell_size = self.cell_size
        view_left = self.canvas.canvasx(0)
        view_top = self.canvas.canvasy(0)
        view_right = view_left + width
        view_bottom = view_top + height

        first_column = int(view_left // cell_size)
        last_column = int(view_right // cell_size) + 1
        first_row = int(view_top // cell_size)
        last_row = int(view_bottom // cell_size) + 1

        for column in range(first_column, last_column + 1):
            x = column * cell_size
            self.canvas.create_line(x, view_top, x, view_bottom, fill=GRID)
        for row in range(first_row, last_row + 1):
            y = row * cell_size
            self.canvas.create_line(view_left, y, view_right, y, fill=GRID)

        inset = min(1.5, cell_size * 0.12)
        for column, row in self.live_cells:
            if (
                first_column <= column <= last_column
                and first_row <= row <= last_row
            ):
                left = column * cell_size + inset
                top = row * cell_size + inset
                self.canvas.create_rectangle(
                    left,
                    top,
                    left + cell_size - 2 * inset,
                    top + cell_size - 2 * inset,
                    fill=self.cell_colors.get((column, row), ALIVE),
                    outline="",
                )

    def _on_mouse_wheel(self, event):
        factor = 1.15 if event.delta > 0 else 1 / 1.15
        self._zoom_at(event, factor)
        return "break"

    def _zoom_at(self, event, factor):
        old_size = self.cell_size
        new_size = min(MAX_CELL_SIZE, max(MIN_CELL_SIZE, old_size * factor))
        if new_size == old_size:
            return

        world_x = self.canvas.canvasx(event.x) / old_size
        world_y = self.canvas.canvasy(event.y) / old_size
        self.cell_size = new_size
        self.canvas.configure(
            xscrollincrement=new_size,
            yscrollincrement=new_size,
        )
        new_view_origin = (
            world_x - event.x / new_size,
            world_y - event.y / new_size,
        )
        self._update_scroll_region(view_origin=new_view_origin)

    def _cell_at(self, event):
        column = int(self.canvas.canvasx(event.x) // self.cell_size)
        row = int(self.canvas.canvasy(event.y) // self.cell_size)
        return column, row

    def _on_click(self, event):
        cell = self._cell_at(event)
        if cell is None:
            return
        self._paint_cell(cell, shift_held=self._shift_held(event))
        self.last_painted_cell = cell
        self._refresh()

    def _on_drag(self, event):
        cell = self._cell_at(event)
        if cell is None or cell == self.last_painted_cell:
            return
        self._paint_cell(cell, shift_held=self._shift_held(event))
        self.last_painted_cell = cell
        self._refresh()

    def _paint_cell(self, cell, shift_held=False):
        if self.tool_var.get() == "eraser" or shift_held:
            self.live_cells.discard(cell)
            self.cell_colors.pop(cell, None)
            return
        self.live_cells.add(cell)
        self.cell_colors[cell] = self.selected_color

    def _reset_paint(self):
        self.last_painted_cell = None

    def _update_stats(self):
        self.stats_label.configure(
            text=f"Generation: {self.generation}     Living cells: {len(self.live_cells)}"
        )

    def _refresh(self):
        self._update_stats()
        self._draw_board()
        self._schedule_scroll_region_update()

    def step(self):
        previous_cells = self.live_cells
        neighbor_counts = {}
        for column, row in previous_cells:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    neighbor = (column + dx, row + dy)
                    neighbor_counts[neighbor] = neighbor_counts.get(neighbor, 0) + 1

        self.live_cells = {
            cell
            for cell, count in neighbor_counts.items()
            if count == 3 or (count == 2 and cell in previous_cells)
        }
        self.cell_colors = {
            cell: self.cell_colors.get(cell, self.selected_color)
            if cell in previous_cells
            else self.selected_color
            for cell in self.live_cells
        }
        self.generation += 1
        self._refresh()

    def clear(self):
        self.live_cells.clear()
        self.cell_colors.clear()
        self.generation = 0
        self._refresh()

    def randomize(self):
        view_left = int(self.canvas.canvasx(0) // self.cell_size)
        view_top = int(self.canvas.canvasy(0) // self.cell_size)
        visible_columns = int(self.canvas.winfo_width() // self.cell_size) + 1
        visible_rows = int(self.canvas.winfo_height() // self.cell_size) + 1
        self.live_cells = {
            (view_left + column, view_top + row)
            for column in range(visible_columns)
            for row in range(visible_rows)
            if random.random() < 0.25
        }
        self.cell_colors = {
            cell: self.selected_color for cell in self.live_cells
        }
        self.generation = 0
        self._refresh()

    def toggle_running(self):
        if self.running:
            self.running = False
            self.run_button.configure(text="Start")
            if self.after_id is not None:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            return

        self.running = True
        self.run_button.configure(text="Pause")
        self._schedule_step()

    def _schedule_step(self):
        if self.running:
            speed = max(1, self.speed.get())
            delay_ms = max(30, int(800 / speed))
            self.after_id = self.root.after(delay_ms, self._tick)

    def _tick(self):
        self.after_id = None
        if self.running:
            self.step()
            self._schedule_step()

    def _on_space(self, _event):
        if self.current_screen == "game":
            self.toggle_running()
            return "break"
        if (
            self.current_screen == "multiplayer_game"
            and self.multiplayer_state is not None
            and self.multiplayer_state["phase"] == "action"
        ):
            self._submit_multiplayer_turn()
            return "break"
        return None

    def _on_close(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        if self.scroll_region_update_id is not None:
            self.root.after_cancel(self.scroll_region_update_id)
        self.multiplayer_stop.set()
        client = self.multiplayer_client
        server = self.hosted_server or self.multiplayer_server
        if client is not None or server is not None:
            threading.Thread(
                target=self._cleanup_multiplayer_on_close,
                args=(client, server),
                daemon=True,
            ).start()
        self.root.destroy()

    @staticmethod
    def _cleanup_multiplayer_on_close(client, server):
        if client is not None:
            try:
                client.leave_game()
            except (OSError, ValueError, ConnectionError):
                LOGGER.exception("Could not notify the multiplayer host on exit.")
        if server is not None:
            try:
                server.close()
            except OSError:
                LOGGER.exception("Could not close the multiplayer game host.")


def main():
    root = tk.Tk()
    GameOfLife(root)
    root.mainloop()


if __name__ == "__main__":
    main()
