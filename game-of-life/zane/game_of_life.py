import logging
import queue
import random
import threading
import tkinter as tk
from tkinter import colorchooser, messagebox
from tkinter import ttk

from multiplayer_game import GameClient, GameServer, local_ipv4_address

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
PALETTE = ("#59e1a5", "#5aa9ff", "#ff6b6b", "#ffd166", "#c792ea", "#f4f7fb")
PATTERNS = {
    "Blinker (period 2)": ("###",),
    "Toad (period 2)": (".###", "###."),
    "Beacon (period 2)": ("##..", "##..", "..##", "..##"),
    "Pulsar (period 3)": (
        "..###...###..",
        ".............",
        "#....#.#....#",
        "#....#.#....#",
        "#....#.#....#",
        "..###...###..",
        ".............",
        "..###...###..",
        "#....#.#....#",
        "#....#.#....#",
        "#....#.#....#",
        ".............",
        "..###...###..",
    ),
}


class GameOfLife:
    def __init__(self, root):
        self.root = root
        self.root.title("Conway's Game of Life")
        self.root.geometry("1000x760")
        self.root.minsize(680, 520)
        self.root.configure(bg=BACKGROUND)

        self.selected_color = PALETTE[0]
        self.live_cells = self.glider()
        self.cell_colors = {cell: self.selected_color for cell in self.live_cells}
        self.generation = 0
        self.running = False
        self.after_id = None
        self.last_painted_cell = None
        self.pending_pattern = False
        self.pattern_placed_this_press = False
        self.cell_size = INITIAL_CELL_SIZE
        self.board_left = 0
        self.board_top = 0
        self.scroll_region_update_id = None
        self.updating_scroll_region = False
        self.current_screen = "menu"
        self.multiplayer_server = None
        self.multiplayer_client = None
        self.multiplayer_state = None
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
        self._build_ui()

        self.root.bind("<space>", self._on_space)
        self.root.bind("<Escape>", lambda _event: self._on_escape())
        self.root.bind("<KeyPress-n>", lambda _event: self._run_game_action(self.step))
        self.root.bind("<KeyPress-N>", lambda _event: self._run_game_action(self.step))
        self.root.bind("<KeyPress-c>", lambda _event: self._run_game_action(self.clear))
        self.root.bind("<KeyPress-C>", lambda _event: self._run_game_action(self.clear))
        self.root.bind("<KeyPress-r>", lambda _event: self._run_game_action(self.randomize))
        self.root.bind("<KeyPress-R>", lambda _event: self._run_game_action(self.randomize))
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

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
        style.configure("Game.TButton", font=("Segoe UI", 10), padding=(10, 6))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.mode_frame = ttk.Frame(self.root, style="Game.TFrame", padding=24)
        self.mode_frame.grid(row=0, column=0, sticky="nsew")
        self.mode_frame.columnconfigure(0, weight=1)
        self.mode_frame.rowconfigure(0, weight=1)
        mode_content = ttk.Frame(self.mode_frame, style="Game.TFrame")
        mode_content.grid(row=0, column=0)
        ttk.Label(
            mode_content, text="CONWAY'S GAME OF LIFE", style="Title.TLabel"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 8))
        ttk.Label(
            mode_content,
            text="Choose how you want to play",
            style="Hint.TLabel",
        ).grid(row=1, column=0, columnspan=2, pady=(0, 24))
        ttk.Button(
            mode_content,
            text="Solo",
            style="Game.TButton",
            command=self.start_solo,
        ).grid(row=2, column=0, padx=8, ipadx=24, ipady=8)
        ttk.Button(
            mode_content,
            text="Multiplayer",
            style="Game.TButton",
            command=self.show_multiplayer,
        ).grid(row=2, column=1, padx=8, ipadx=24, ipady=8)

        self.multiplayer_frame = ttk.Frame(
            self.root, style="Game.TFrame", padding=24
        )
        self.multiplayer_frame.grid(row=0, column=0, sticky="nsew")
        self.multiplayer_frame.grid_remove()
        self.multiplayer_frame.columnconfigure(0, weight=1)
        self.multiplayer_frame.rowconfigure(0, weight=1)
        multiplayer_content = ttk.Frame(self.multiplayer_frame, style="Game.TFrame")
        multiplayer_content.grid(row=0, column=0)
        ttk.Label(
            multiplayer_content, text="MULTIPLAYER", style="Title.TLabel"
        ).grid(row=0, column=0, pady=(0, 8))
        ttk.Label(
            multiplayer_content,
            text="Host or join over the same Wi-Fi/LAN, and share the room code only with people you trust. Allow Python through Windows Firewall if asked. Public internet play is not included yet.",
            style="Hint.TLabel",
            wraplength=520,
            justify="center",
        ).grid(row=1, column=0, columnspan=3, pady=(0, 20))

        rules = (
            "SPĒLES NOTEIKUMI\n"
            "1. Izvēlies 1v1 vai 2v2. Host izveido spēli, bet pārējie pievienojas "
            "ar host adresi un istabas kodu (visi vienā Wi-Fi/LAN tīklā).\n"
            "2. Kad visi pievienojušies, katrs uzzīmē sākuma figūru savā laukumā. "
            "Spēli sāk hosts.\n"
            "3. Savā gājienā uzzīmē vienu līniju: savā laukumā, lai aizsargātos, "
            "vai pretinieka laukumā, lai uzbruktu (uzbrukums ir sarkanā krāsā). "
            "2v2 režīmā komandas biedriem uzbrukt nedrīkst.\n"
            "4. Pēc visu spēlētāju gājieniem spēle izspēlē 10 paaudzes. Ja tavā "
            "sākuma laukumā vairs nav dzīvu šūnu, tu esi izsists. Uzvar pēdējais "
            "izdzīvojušais spēlētājs vai komanda."
        )
        ttk.Label(
            multiplayer_content,
            text=rules,
            style="Hint.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(multiplayer_content, text="Your name", style="Hint.TLabel").grid(
            row=3, column=0, sticky="e", padx=8, pady=5
        )
        self.mp_name_var = tk.StringVar(value="Player")
        ttk.Entry(multiplayer_content, textvariable=self.mp_name_var, width=22).grid(
            row=3, column=1, columnspan=2, sticky="w", pady=5
        )
        ttk.Label(multiplayer_content, text="Game mode", style="Hint.TLabel").grid(
            row=4, column=0, sticky="e", padx=8, pady=5
        )
        self.mp_mode_var = tk.StringVar(value="1v1")
        ttk.Combobox(
            multiplayer_content,
            textvariable=self.mp_mode_var,
            values=("1v1", "2v2"),
            state="readonly",
            width=19,
        ).grid(row=4, column=1, columnspan=2, sticky="w", pady=5)
        ttk.Label(multiplayer_content, text="Host address", style="Hint.TLabel").grid(
            row=5, column=0, sticky="e", padx=8, pady=5
        )
        self.mp_host_var = tk.StringVar()
        ttk.Entry(
            multiplayer_content, textvariable=self.mp_host_var, width=22
        ).grid(row=5, column=1, columnspan=2, sticky="w", pady=5)
        ttk.Label(multiplayer_content, text="Room code", style="Hint.TLabel").grid(
            row=6, column=0, sticky="e", padx=8, pady=5
        )
        self.mp_code_var = tk.StringVar()
        ttk.Entry(
            multiplayer_content, textvariable=self.mp_code_var, width=22
        ).grid(row=6, column=1, columnspan=2, sticky="w", pady=5)
        self.mp_host_button = ttk.Button(
            multiplayer_content,
            text="Host game",
            style="Game.TButton",
            command=self._host_multiplayer_game,
        )
        self.mp_host_button.grid(row=7, column=1, sticky="w", pady=(14, 5))
        self.mp_join_button = ttk.Button(
            multiplayer_content,
            text="Join game",
            style="Game.TButton",
            command=self._join_multiplayer_game,
        )
        self.mp_join_button.grid(row=7, column=2, sticky="w", pady=(14, 5))
        self.mp_back_button = ttk.Button(
            multiplayer_content,
            text="Back to mode selection",
            style="Game.TButton",
            command=self.show_mode_selection,
        )
        self.mp_back_button.grid(row=8, column=0, columnspan=3, pady=(8, 0))

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
        mp_controls = ttk.Frame(self.multiplayer_game_frame, style="Game.TFrame")
        mp_controls.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.mp_start_button = ttk.Button(
            mp_controls,
            text="Start game",
            style="Game.TButton",
            command=self._start_multiplayer_game,
        )
        self.mp_start_button.grid(row=0, column=0, padx=(0, 8))
        ttk.Label(
            mp_controls,
            text="Setup: draw in your area. Each turn: one stroke to defend (your area) or attack (opponent area, red). After all turns, Life advances 10 generations; an empty home area means elimination.",
            style="Hint.TLabel",
            wraplength=800,
        ).grid(row=0, column=1, sticky="w")
        ttk.Button(
            mp_controls,
            text="Leave game",
            style="Game.TButton",
            command=self._leave_multiplayer_game,
        ).grid(row=0, column=2, padx=(12, 0))
        self.mp_connection_label = ttk.Label(
            self.multiplayer_game_frame, style="Hint.TLabel", text=""
        )
        self.mp_connection_label.grid(row=3, column=0, sticky="w", pady=(8, 0))

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
        self.mp_result_heading = ttk.Label(
            result_content, style="Title.TLabel", text=""
        )
        self.mp_result_heading.grid(row=0, column=0, pady=(0, 12))
        self.mp_result_winner = ttk.Label(
            result_content, style="Celebration.TLabel", text=""
        )
        self.mp_result_winner.grid(row=1, column=0, pady=(0, 12))
        self.mp_result_message = ttk.Label(
            result_content,
            style="Hint.TLabel",
            text="",
            justify="center",
            wraplength=600,
        )
        self.mp_result_message.grid(row=2, column=0, pady=(0, 24))
        ttk.Button(
            result_content,
            text="Atpakaļ uz sākumu",
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
        ttk.Button(
            controls,
            text="Mode selection",
            style="Game.TButton",
            command=self.show_mode_selection,
        ).grid(row=0, column=0, padx=(0, 7))
        self.run_button = ttk.Button(
            controls, text="Start", style="Game.TButton", command=self.toggle_running
        )
        self.run_button.grid(row=0, column=1, padx=7)
        ttk.Button(
            controls, text="Step", style="Game.TButton", command=self.step
        ).grid(row=0, column=2, padx=7)
        ttk.Button(
            controls, text="Randomize", style="Game.TButton", command=self.randomize
        ).grid(row=0, column=3, padx=7)
        ttk.Button(
            controls, text="Clear", style="Game.TButton", command=self.clear
        ).grid(row=0, column=4, padx=7)

        toolbox = ttk.Frame(footer, style="Game.TFrame")
        toolbox.grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.tool_var = tk.StringVar(value="pencil")
        ttk.Radiobutton(
            toolbox,
            text="Pencil",
            variable=self.tool_var,
            value="pencil",
            command=self._set_tool,
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Radiobutton(
            toolbox,
            text="Eraser",
            variable=self.tool_var,
            value="eraser",
            command=self._set_tool,
        ).grid(row=0, column=1, padx=(0, 12))

        ttk.Label(toolbox, text="Color:", style="Hint.TLabel").grid(
            row=0, column=2, padx=(0, 5)
        )
        self.color_buttons = {}
        for index, color in enumerate(PALETTE):
            button = tk.Button(
                toolbox,
                background=color,
                activebackground=color,
                width=2,
                relief="solid",
                borderwidth=2,
                command=lambda selected=color: self._set_color(selected),
            )
            button.grid(row=0, column=3 + index, padx=2)
            self.color_buttons[color] = button
        ttk.Button(
            toolbox,
            text="Custom",
            style="Game.TButton",
            command=self._choose_custom_color,
        ).grid(row=0, column=3 + len(PALETTE), padx=(5, 12))

        ttk.Label(toolbox, text="Lexicon:", style="Hint.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 0), padx=(0, 5)
        )
        self.pattern_var = tk.StringVar(value=next(iter(PATTERNS)))
        self.pattern_menu = ttk.Combobox(
            toolbox,
            textvariable=self.pattern_var,
            values=tuple(PATTERNS),
            state="readonly",
            width=25,
        )
        self.pattern_menu.grid(row=1, column=1, sticky="w", pady=(8, 0), padx=(0, 5))
        ttk.Button(
            toolbox,
            text="Place",
            style="Game.TButton",
            command=self._begin_pattern_placement,
        ).grid(row=1, column=2, sticky="w", pady=(8, 0))
        self.tool_status = ttk.Label(footer, style="Hint.TLabel", text="Tool: pencil")
        self.tool_status.grid(row=2, column=0, sticky="w", pady=(6, 0))

        self.stats_label = ttk.Label(footer, style="Stats.TLabel")
        self.stats_label.grid(row=3, column=0, sticky="w", pady=(6, 0))

        speed_frame = ttk.Frame(footer, style="Game.TFrame")
        speed_frame.grid(row=0, column=1, rowspan=5, sticky="e", padx=(24, 0))
        ttk.Label(speed_frame, text="Speed", style="Hint.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.speed = tk.IntVar(value=10)
        ttk.Scale(
            speed_frame,
            from_=1,
            to=30,
            variable=self.speed,
            orient="horizontal",
            length=150,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(
            footer,
            text="Space: start/pause   N: step   R: randomize   C: clear   Scrollbars: pan   Wheel: zoom",
            style="Hint.TLabel",
        ).grid(row=4, column=0, sticky="w", pady=(9, 0))

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

    def start_solo(self):
        self._show_screen(self.game_frame, "game")
        self._update_stats()
        self._draw_board()

    def show_multiplayer(self):
        self._show_screen(self.multiplayer_frame, "multiplayer")

    def show_mode_selection(self):
        if self.running:
            self.toggle_running()
        self._show_screen(self.mode_frame, "menu")

    def _run_game_action(self, action):
        if self.current_screen == "game":
            action()

    def _leave_multiplayer_game(self):
        client = self.multiplayer_client
        server = self.multiplayer_server
        self.multiplayer_stop.set()
        self.multiplayer_poll_started = False
        self.multiplayer_client = None
        self.multiplayer_server = None
        self.multiplayer_state = None
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
            if server is not None:
                try:
                    server.close()
                except OSError as error:
                    self.multiplayer_queue.put(
                        ("error", f"Could not close the game host: {error}")
                    )

        threading.Thread(target=cleanup, daemon=True).start()

    def _on_escape(self):
        if self.current_screen == "game" and self.pending_pattern:
            self._cancel_pattern_placement()
        elif self.current_screen == "multiplayer" and not self.multiplayer_connecting:
            self.show_mode_selection()

    def _host_multiplayer_game(self):
        name = self.mp_name_var.get().strip() or "Player"
        mode = self.mp_mode_var.get()
        if mode not in ("1v1", "2v2"):
            messagebox.showerror("Multiplayer", "Choose 1v1 or 2v2.", parent=self.root)
            return
        self._set_multiplayer_connecting(True)
        self.mp_connection_label.configure(text="Starting game host...")
        threading.Thread(
            target=self._host_worker, args=(mode, name), daemon=True
        ).start()

    def _host_worker(self, mode, name):
        server = None
        try:
            host_address = local_ipv4_address()
            server = GameServer(
                mode,
                generations_per_round=10,
                bind_address=host_address,
            )
            server.start()
            client = GameClient(host_address, name, server.room_code)
            state = client.join()
            self.multiplayer_queue.put(
                (
                    "connected",
                    {
                        "server": server,
                        "client": client,
                        "state": state,
                        "connection": (
                            f"Host address: {host_address}  "
                            f"Room code: {server.room_code}"
                        ),
                    },
                )
            )
        except (OSError, ValueError, ConnectionError) as error:
            if server is not None:
                server.close()
            self.multiplayer_queue.put(("error", f"Could not host game: {error}"))

    def _join_multiplayer_game(self):
        host = self.mp_host_var.get().strip()
        room_code = self.mp_code_var.get().strip()
        name = self.mp_name_var.get().strip() or "Player"
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
            args=(host, name, room_code),
            daemon=True,
        ).start()

    def _join_worker(self, host, name, room_code):
        try:
            client = GameClient(host, name, room_code)
            state = client.join()
            self.multiplayer_queue.put(
                (
                    "connected",
                    {
                        "server": None,
                        "client": client,
                        "state": state,
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
                    self.multiplayer_client = payload["client"]
                    self.multiplayer_state = payload["state"]
                    self._set_multiplayer_connecting(False)
                    self.mp_connection_label.configure(text=payload["connection"])
                    self.mp_start_button.configure(state="normal")
                    self._show_screen(self.multiplayer_game_frame, "multiplayer_game")
                    self._start_multiplayer_polling()
                    self._draw_multiplayer_board()
                elif kind == "state":
                    if self.multiplayer_client is None:
                        continue
                    self.multiplayer_state = payload
                    self._draw_multiplayer_board()
                elif kind == "action_done":
                    if self.multiplayer_client is None:
                        continue
                    self.multiplayer_state = payload
                    self.multiplayer_busy = False
                    self.mp_stroke.clear()
                    self._draw_multiplayer_board()
                elif kind == "action_error":
                    self.multiplayer_busy = False
                    self.mp_stroke.clear()
                    self.mp_connection_label.configure(
                        text=f"Action failed: {payload}"
                    )
                    self._draw_multiplayer_board()
                elif kind == "error":
                    if self.current_screen == "multiplayer_game":
                        self.multiplayer_busy = False
                        self.mp_connection_label.configure(text=str(payload))
                        self._draw_multiplayer_board()
                    else:
                        self._set_multiplayer_connecting(False)
                        self.mp_connection_label.configure(text=str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self._process_multiplayer_queue)

    def _send_multiplayer_action(self, action, cells=None):
        if self.multiplayer_busy or self.multiplayer_client is None:
            return
        self.multiplayer_busy = True
        self.mp_start_button.configure(state="disabled")
        client = self.multiplayer_client

        def send():
            try:
                if action == "start":
                    state = client.start_game()
                else:
                    state = client.submit_stroke(cells)
                self.multiplayer_queue.put(("action_done", state))
            except (OSError, ValueError, ConnectionError) as error:
                self.multiplayer_queue.put(("action_error", str(error)))

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
        if state["phase"] != "action" or state["current_turn"] != player_index:
            return False
        if target == player_index:
            return True
        return self._team_for_player(target, state["mode"]) != self._team_for_player(
            player_index, state["mode"]
        )

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
        if state["phase"] == "action" and state["current_turn"] != player_index:
            return
        cell = self._mp_cell_at(event)
        if cell is None or not self._mp_can_draw_cell(cell):
            return
        self.mp_stroke = {cell}
        self.mp_last_cell = cell
        self._draw_multiplayer_board()

    def _multiplayer_canvas_drag(self, event):
        if not self.mp_stroke or self.multiplayer_busy:
            return
        cell = self._mp_cell_at(event)
        if (
            cell is None
            or cell == self.mp_last_cell
            or not self._mp_can_draw_cell(cell)
            or self._mp_territory_at(*cell)
            != self._mp_territory_at(*next(iter(self.mp_stroke)))
            or len(self.mp_stroke) >= 300
        ):
            return
        self.mp_stroke.add(cell)
        self.mp_last_cell = cell
        self._draw_multiplayer_board()

    def _multiplayer_canvas_release(self, _event):
        if not self.mp_stroke:
            return
        cells = [[x, y] for x, y in self.mp_stroke]
        self.mp_stroke.clear()
        self.mp_last_cell = None
        self._send_multiplayer_action("stroke", cells)

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
            color = (
                "#ff4545"
                if target != player_index
                else state["players"][player_index]["color"]
            )
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
            labels.append((center_x, center_y, label, player["color"]))
        for x, y, label, color in labels:
            canvas.create_text(
                self.mp_board_left + x * self.mp_cell_size,
                self.mp_board_top + y * self.mp_cell_size,
                text=label,
                fill=color,
                font=("Segoe UI", 10, "bold"),
            )

        self.mp_status_label.configure(text=state["message"])
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

    def _show_multiplayer_result(self, state):
        winner = state["winner"]
        players = state["players"]
        if winner is None:
            self.mp_result_heading.configure(text="NEIZŠĶIRTS")
            self.mp_result_winner.configure(text="")
            self.mp_result_message.configure(
                text="Šoreiz neviens neizdzīvoja. Pamēģiniet vēlreiz!"
            )
        else:
            winning_players = [
                player for player in players if player["team"] == winner
            ]
            is_winner = any(
                player["index"] == self.multiplayer_client.player_index
                for player in winning_players
            )
            if state["mode"] == "1v1":
                winner_text = f"Uzvarētājs: {winning_players[0]['name']}"
                personal_message = (
                    "Apsveicu! Tu esi īsts meistars šūnu cīņā!"
                    if is_winner
                    else "Nākamreiz konča var būt tava!"
                )
            else:
                winner_text = f"Uzvarētāju komanda: {winner + 1}"
                personal_message = (
                    "Apsveicu! Tava komanda ir īsts meistars šūnu cīņā!"
                    if is_winner
                    else "Nākamreiz konča var būt tavai komandai!"
                )
            self.mp_result_heading.configure(text="SPĒLE BEIGUSIES")
            self.mp_result_winner.configure(text="KONČA NO ZANES!")
            self.mp_result_message.configure(
                text=f"{winner_text}\n{personal_message}"
            )

        if self.current_screen != "multiplayer_result":
            self._show_screen(
                self.multiplayer_result_frame, "multiplayer_result"
            )

    def _set_color(self, color):
        self.selected_color = color
        for palette_color, button in self.color_buttons.items():
            button.configure(
                relief="solid" if palette_color == color else "flat",
                borderwidth=3 if palette_color == color else 1,
            )

    def _set_tool(self):
        self._cancel_pattern_placement()
        self.tool_status.configure(text=f"Tool: {self.tool_var.get()}")

    def _choose_custom_color(self):
        chosen = colorchooser.askcolor(
            color=self.selected_color, title="Choose cell color", parent=self.root
        )[1]
        if chosen:
            self._set_color(chosen)

    def _begin_pattern_placement(self):
        self.pending_pattern = True
        self.tool_status.configure(
            text=f"Click the board to place {self.pattern_var.get()} (Esc to cancel)"
        )

    def _cancel_pattern_placement(self):
        if self.pending_pattern:
            self.pending_pattern = False
            self.tool_status.configure(text=f"Tool: {self.tool_var.get()}")

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
        self.pattern_placed_this_press = False
        if self.pending_pattern:
            self._place_pattern(cell)
            self.last_painted_cell = cell
            self.pattern_placed_this_press = True
            return
        self._paint_cell(cell)
        self.last_painted_cell = cell
        self._refresh()

    def _on_drag(self, event):
        cell = self._cell_at(event)
        if (
            self.pattern_placed_this_press
            or cell is None
            or cell == self.last_painted_cell
        ):
            return
        if self.pending_pattern:
            return
        self._paint_cell(cell)
        self.last_painted_cell = cell
        self._refresh()

    def _paint_cell(self, cell):
        if self.tool_var.get() == "eraser":
            self.live_cells.discard(cell)
            self.cell_colors.pop(cell, None)
            return
        self.live_cells.add(cell)
        self.cell_colors[cell] = self.selected_color

    def _place_pattern(self, center):
        pattern = PATTERNS[self.pattern_var.get()]
        height = len(pattern)
        width = max(len(line) for line in pattern)
        origin_x = center[0] - width // 2
        origin_y = center[1] - height // 2

        for row, line in enumerate(pattern):
            for column, marker in enumerate(line):
                cell = (origin_x + column, origin_y + row)
                if marker == "#":
                    self.live_cells.add(cell)
                    self.cell_colors[cell] = self.selected_color

        self.pending_pattern = False
        self.tool_status.configure(text=f"Tool: {self.tool_var.get()}")
        self._refresh()

    def _reset_paint(self):
        self.last_painted_cell = None
        self.pattern_placed_this_press = False

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
        self._cancel_pattern_placement()
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

    def _on_close(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        if self.scroll_region_update_id is not None:
            self.root.after_cancel(self.scroll_region_update_id)
        self.multiplayer_stop.set()
        client = self.multiplayer_client
        server = self.multiplayer_server
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
