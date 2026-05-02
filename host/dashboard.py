import customtkinter as ctk
import serial
import threading


SERIAL_PORT = "/dev/tty.usbserial-2102"
BAUD_RATE = 115200


class TrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Spatial Tracker")
        self.geometry("980x720")
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#0C1117")

        self.shell = ctk.CTkFrame(self, fg_color="#10161D", corner_radius=28)
        self.shell.pack(fill="both", expand=True, padx=18, pady=18)
        self.shell.grid_columnconfigure(0, weight=0)
        self.shell.grid_columnconfigure(1, weight=1)
        self.shell.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self.shell,
            width=280,
            fg_color="#151D26",
            corner_radius=24,
            border_width=1,
            border_color="#242E39",
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(18, 10), pady=18)
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(3, weight=1)

        self.header = ctk.CTkLabel(
            self.sidebar,
            text="AOA MONITOR",
            font=("Helvetica", 12, "bold"),
            text_color="#8FA2B6",
        )
        self.header.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 4))

        self.subheader = ctk.CTkLabel(
            self.sidebar,
            text="Live Tags",
            font=("Helvetica", 28, "bold"),
            text_color="#F4F7FB",
        )
        self.subheader.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 6))

        self.sidebar_meta = ctk.CTkLabel(
            self.sidebar,
            text="Stable view of active tags",
            font=("Helvetica", 14),
            text_color="#95A6B8",
        )
        self.sidebar_meta.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 14))

        self.tag_list = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="#151D26",
            corner_radius=0,
            scrollbar_button_color="#2B3642",
            scrollbar_button_hover_color="#3B4857",
        )
        self.tag_list.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.tag_list.grid_columnconfigure(0, weight=1)

        self.empty_state = ctk.CTkLabel(
            self.tag_list,
            text="Waiting for +UUDF packets...",
            font=("Helvetica", 14),
            text_color="#76889B",
        )
        self.empty_state.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        self.content = ctk.CTkFrame(
            self.shell,
            fg_color="#10161D",
            corner_radius=24,
            border_width=0,
        )
        self.content.grid(row=0, column=1, sticky="nsew", padx=(10, 18), pady=18)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        self.hero_card = ctk.CTkFrame(
            self.content,
            fg_color="#171F29",
            corner_radius=24,
            border_width=1,
            border_color="#26303B",
        )
        self.hero_card.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        self.hero_card.grid_columnconfigure(0, weight=1)

        self.summary_title = ctk.CTkLabel(
            self.hero_card,
            text="Spatial Map",
            font=("Helvetica", 13, "bold"),
            text_color="#90A3B8",
        )
        self.summary_title.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))

        self.readout = ctk.CTkLabel(
            self.hero_card,
            text="Waiting for tags",
            font=("Helvetica", 26, "bold"),
            justify="left",
            anchor="w",
            text_color="#F4F7FB",
        )
        self.readout.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))

        self.detail = ctk.CTkLabel(
            self.hero_card,
            text="AOA left/right  •  elevation up/down",
            font=("Helvetica", 15),
            justify="left",
            anchor="w",
            text_color="#9FAFBE",
        )
        self.detail.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 18))

        self.graph_frame = ctk.CTkFrame(
            self.content,
            fg_color="#171F29",
            corner_radius=24,
            border_width=1,
            border_color="#26303B",
        )
        self.graph_frame.grid(row=1, column=0, sticky="nsew")

        self.graph_title = ctk.CTkLabel(
            self.graph_frame,
            text="AOA vs Elevation",
            font=("Helvetica", 16, "bold"),
            text_color="#E5EBF1",
        )
        self.graph_title.pack(anchor="w", padx=18, pady=(16, 6))

        self.canvas = ctk.CTkCanvas(
            self.graph_frame,
            width=620,
            height=540,
            bg="#171F29",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.center_x = 310
        self.center_y = 270
        self.radius = 205
        self.tags = {}
        self.tag_cards = {}

        self.thread = threading.Thread(target=self.read_serial, daemon=True)
        self.thread.start()

    def read_serial(self):
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line.startswith("+UUDF:"):
                    continue

                payload = line[len("+UUDF:") :]
                parts = [part.strip().strip('"') for part in payload.split(",")]
                if len(parts) < 10:
                    continue

                try:
                    source_id = parts[0]
                    rssi = int(parts[1])
                    aoa = int(parts[2])
                    elevation = int(parts[3])
                    board_uuid = parts[6]
                    timestamp = int(parts[8])
                    sequence = int(parts[9])
                except ValueError:
                    continue

                self.after(
                    0,
                    self.update_display,
                    source_id,
                    aoa,
                    elevation,
                    rssi,
                    board_uuid,
                    timestamp,
                    sequence,
                )
        except Exception as exc:
            self.after(0, lambda: self.readout.configure(text=f"ERROR\n{exc}"))

    def update_display(self, source_id, aoa, elevation, rssi, board_uuid, timestamp, sequence):
        current = self.tags.get(source_id)
        if current is not None:
            if timestamp < current["timestamp"]:
                return
            if timestamp == current["timestamp"] and sequence < current["sequence"]:
                return

        self.tags[source_id] = {
            "aoa": aoa,
            "elevation": elevation,
            "rssi": rssi,
            "board_uuid": board_uuid,
            "timestamp": timestamp,
            "sequence": sequence,
        }

        self._update_readout()
        self._render_tag_list()
        self._draw_graph()

    def _update_readout(self):
        tag_count = len(self.tags)
        boards = sorted({tag["board_uuid"] for tag in self.tags.values() if tag["board_uuid"]})
        board_text = boards[0] if len(boards) == 1 else f"{len(boards)} boards"
        self.readout.configure(text=f"{tag_count} active tag{'s' if tag_count != 1 else ''}")
        self.detail.configure(
            text=f"Tracking {board_text}  •  AOA left/right  •  elevation up/down"
        )

    def _render_tag_list(self):
        if self.empty_state.winfo_exists() and self.tags:
            self.empty_state.grid_forget()

        for row, tag_id in enumerate(sorted(self.tags), start=0):
            tag = self.tags[tag_id]
            widgets = self.tag_cards.get(tag_id)

            if widgets is None:
                card = ctk.CTkFrame(
                    self.tag_list,
                    corner_radius=18,
                    fg_color="#1C2631",
                    border_width=1,
                    border_color="#273240",
                )
                card.grid_columnconfigure(1, weight=1)

                icon = ctk.CTkCanvas(
                    card,
                    width=34,
                    height=34,
                    bg="#1C2631",
                    highlightthickness=0,
                )
                icon.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(14, 10), pady=14)

                title = ctk.CTkLabel(
                    card,
                    text=tag_id,
                    font=("Helvetica", 15, "bold"),
                    text_color="#F4F7FB",
                    anchor="w",
                )
                title.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 2))

                subtitle = ctk.CTkLabel(
                    card,
                    text="",
                    font=("Helvetica", 13),
                    text_color="#A3B2C0",
                    justify="left",
                    anchor="w",
                )
                subtitle.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(0, 12))

                widgets = {
                    "card": card,
                    "icon": icon,
                    "title": title,
                    "subtitle": subtitle,
                }
                self.tag_cards[tag_id] = widgets

            widgets["title"].configure(text=tag_id)
            widgets["subtitle"].configure(
                text=(
                    f"AOA {tag['aoa']:>4}°    EL {tag['elevation']:>4}°\n"
                    f"RSSI {tag['rssi']:>4} dBm"
                )
            )

            widgets["card"].grid(row=row, column=0, sticky="ew", padx=8, pady=6)
            self._draw_tag_icon(widgets["icon"], row)

    def _draw_tag_icon(self, canvas, index):
        colors = ["#7CC7FF", "#9FD68F", "#F8B76E", "#D3A7FF", "#FF8A9E"]
        color = colors[index % len(colors)]
        canvas.delete("all")
        canvas.create_oval(4, 4, 30, 30, fill="#111821", outline="#2A3440", width=1)
        canvas.create_oval(9, 9, 25, 25, fill=color, outline="")
        canvas.create_oval(13, 13, 21, 21, fill="#F7FAFD", outline="")

    def _draw_graph(self):
        canvas_width = int(self.canvas.winfo_width() or 620)
        canvas_height = int(self.canvas.winfo_height() or 540)
        self.center_x = canvas_width // 2
        self.center_y = canvas_height // 2
        self.radius = min(canvas_width, canvas_height) * 0.38

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, canvas_width, canvas_height, fill="#171F29", outline="")
        self.canvas.create_oval(
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius,
            outline="#32404D",
            width=2,
        )
        self.canvas.create_oval(
            self.center_x - self.radius * 0.66,
            self.center_y - self.radius * 0.66,
            self.center_x + self.radius * 0.66,
            self.center_y + self.radius * 0.66,
            outline="#283440",
            width=1,
        )
        self.canvas.create_oval(
            self.center_x - self.radius * 0.33,
            self.center_y - self.radius * 0.33,
            self.center_x + self.radius * 0.33,
            self.center_y + self.radius * 0.33,
            outline="#202A34",
            width=1,
        )
        self.canvas.create_line(
            self.center_x - self.radius,
            self.center_y,
            self.center_x + self.radius,
            self.center_y,
            fill="#3A4855",
            width=1,
        )
        self.canvas.create_line(
            self.center_x,
            self.center_y - self.radius,
            self.center_x,
            self.center_y + self.radius,
            fill="#3A4855",
            width=1,
        )
        self.canvas.create_text(
            self.center_x,
            self.center_y - self.radius - 16,
            text="+EL",
            fill="#91A0AF",
            font=("Helvetica", 11, "bold"),
        )
        self.canvas.create_text(
            self.center_x,
            self.center_y + self.radius + 16,
            text="-EL",
            fill="#91A0AF",
            font=("Helvetica", 11, "bold"),
        )
        self.canvas.create_text(
            self.center_x + self.radius + 22,
            self.center_y,
            text="-AOA",
            fill="#91A0AF",
            font=("Helvetica", 11, "bold"),
        )
        self.canvas.create_text(
            self.center_x - self.radius - 22,
            self.center_y,
            text="+AOA",
            fill="#91A0AF",
            font=("Helvetica", 11, "bold"),
        )

        self.canvas.create_oval(
            self.center_x - 5,
            self.center_y - 5,
            self.center_x + 5,
            self.center_y + 5,
            fill="#F4F7FA",
            outline="",
        )

        colors = ["#7CC7FF", "#9FD68F", "#F8B76E", "#D3A7FF", "#FF8A9E"]
        for index, tag_id in enumerate(sorted(self.tags)):
            tag = self.tags[tag_id]
            color = colors[index % len(colors)]
            aoa_value = max(-90, min(90, tag["aoa"]))
            elevation_value = max(-90, min(90, tag["elevation"]))

            end_x = self.center_x - (aoa_value / 90.0) * self.radius
            end_y = self.center_y - (elevation_value / 90.0) * self.radius

            self.canvas.create_line(
                self.center_x,
                self.center_y,
                end_x,
                end_y,
                fill=color,
                width=4,
            )
            self.canvas.create_oval(
                end_x - 8,
                end_y - 8,
                end_x + 8,
                end_y + 8,
                fill=color,
                outline=color,
                width=2,
            )
            self.canvas.create_oval(
                end_x - 4,
                end_y - 4,
                end_x + 4,
                end_y + 4,
                fill="#F8FBFF",
                outline="",
            )
            self.canvas.create_text(
                end_x,
                end_y - 18,
                text=tag_id[:6],
                fill="#F3F7FB",
                font=("Helvetica", 10, "bold"),
            )


if __name__ == "__main__":
    app = TrackerApp()
    app.mainloop()
