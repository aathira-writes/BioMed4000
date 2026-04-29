import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
import os
import cv2
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from login import login, create_user, verify_admin, admin_exists, update_user_role
from training import capture_faces
from faces import recognize_user
from identity import verify_identity
from train_model import train_model
from database import init_db
from PIL import Image, ImageTk
from inventory import (
    add_item, get_all_items, get_item, edit_item, delete_item,
    checkout_item, get_dashboard_stats, get_weekly_usage,
    get_alerts, get_risk_level, get_depletion_forecast, get_item_forecast,
    get_item_by_barcode,
    get_all_users, get_user_checkout_history, get_health_notes, update_health_notes,
    delete_user_completely,
    add_personal_medication, get_personal_medications,
    get_personal_medication_by_barcode, delete_personal_medication,
    get_calendar_events, add_calendar_event, delete_calendar_event,
)

# ── theme ──────────────────────────────────────────────────────────────────
BG      = "#0d1117"
CARD    = "#161b22"
NAV     = "#010409"
TEXT    = "#c9d1d9"
DIM     = "#8b949e"
ACCENT  = "#1f6feb"
GREEN   = "#3fb950"
YELLOW  = "#dfb865"
RED     = "#e16a64"
INPUT   = "#21262d"
BORDER  = "#30363d"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("NASA HUNCH – Medical Inventory System")
        self.root.configure(bg=BG)
        self.root.geometry("780x560")
        self.current_user_id   = None
        self.current_user_role = None
        self._fig    = None
        self._canvas = None
        self._fig2   = None
        self._canvas2 = None
        self._nav_btns    = {}
        self.content_frame = None
        self._configure_styles()
        self.show_main_menu()

    # ── admin verification dialog ──────────────────────────────────────────

    def _request_admin_auth(self):
        """
        Shows a modal dialog asking for an existing admin's credentials.
        Returns True if verified, False if cancelled or wrong credentials.
        Skips the check automatically when no admins exist yet.
        """
        if not admin_exists():
            return True   # first admin can be created freely

        result = {"ok": False}

        dlg = tk.Toplevel(self.root)
        dlg.title("Admin Authorisation Required")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        # Centre over parent
        self.root.update_idletasks()
        px, py = self.root.winfo_rootx(), self.root.winfo_rooty()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        dlg.geometry(f"380x310+{px + pw//2 - 190}+{py + ph//2 - 155}")

        self._lbl(dlg, "Admin Authorisation Required",
                  font=("Arial", 13, "bold"), fg=TEXT, bg=BG).pack(pady=(22, 4))
        self._lbl(dlg,
                  "Creating an admin or medic account requires\n"
                  "an existing admin to enter their credentials.",
                  font=("Arial", 10), fg=DIM, bg=BG,
                  justify="center").pack(pady=(0, 18))

        form = tk.Frame(dlg, bg=BG)
        form.pack()

        self._lbl(form, "Admin Username", fg=DIM, bg=BG,
                  font=("Arial", 10)).pack(anchor="w")
        admin_user_e = tk.Entry(form, bg=INPUT, fg=TEXT, insertbackground=TEXT,
                                relief="flat", font=("Arial", 11), bd=6, width=30)
        admin_user_e.pack(pady=(2, 10))

        self._lbl(form, "Admin Password", fg=DIM, bg=BG,
                  font=("Arial", 10)).pack(anchor="w")
        admin_pass_e = tk.Entry(form, bg=INPUT, fg=TEXT, insertbackground=TEXT,
                                relief="flat", font=("Arial", 11), bd=6, width=30,
                                show="*")
        admin_pass_e.pack(pady=(2, 0))

        err_lbl = self._lbl(dlg, "", fg=RED, bg=BG, font=("Arial", 9))
        err_lbl.pack(pady=(6, 0))

        def _verify():
            if verify_admin(admin_user_e.get().strip(), admin_pass_e.get()):
                result["ok"] = True
                dlg.destroy()
            else:
                err_lbl.config(text="Incorrect credentials or not an admin account.")
                admin_pass_e.delete(0, "end")

        btn_row = tk.Frame(dlg, bg=BG)
        btn_row.pack(pady=(10, 0))
        tk.Button(btn_row, text="Authorise", command=_verify,
                  bg=ACCENT, fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=5,
                  cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel", command=dlg.destroy,
                  bg=INPUT, fg=TEXT, font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=5,
                  cursor="hand2").pack(side="left")

        admin_pass_e.bind("<Return>", lambda *_: _verify())
        admin_user_e.focus_set()
        dlg.wait_window()
        return result["ok"]

    # ── ttk theming ────────────────────────────────────────────────────────

    def _configure_styles(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("Dark.Treeview",
                    background=CARD, foreground=TEXT,
                    fieldbackground=CARD, rowheight=26,
                    font=("Arial", 10), borderwidth=0)
        s.configure("Dark.Treeview.Heading",
                    background=NAV, foreground=TEXT,
                    font=("Arial", 10, "bold"), relief="flat")
        s.map("Dark.Treeview", background=[("selected", ACCENT)])

    # ── generic helpers ────────────────────────────────────────────────────

    def clear_window(self):
        self._close_chart()
        for w in self.root.winfo_children():
            w.destroy()
        self._nav_btns = {}
        self.content_frame = None

    def _close_chart(self):
        import matplotlib.pyplot as plt
        if self._fig is not None:
            plt.close(self._fig)
            self._fig = None
            self._canvas = None
        if self._fig2 is not None:
            plt.close(self._fig2)
            self._fig2 = None
            self._canvas2 = None

    def _embed_chart(self, fig, master):
        """Embed a matplotlib figure into a Tkinter frame."""
        canvas = FigureCanvasTkAgg(fig, master=master)
        widget = canvas.get_tk_widget()
        widget.config(bg=CARD)
        widget.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        canvas.draw()
        return canvas

    def _clear_content(self):
        self._close_chart()
        self.root.unbind_all("<MouseWheel>")
        if self.content_frame:
            for w in self.content_frame.winfo_children():
                w.destroy()

    def _lbl(self, parent, text, font=("Arial", 11), fg=TEXT, bg=None, **kw):
        b = bg if bg is not None else self._bg(parent)
        return tk.Label(parent, text=text, font=font, fg=fg, bg=b, **kw)

    def _bg(self, widget):
        try:
            return widget.cget("bg")
        except Exception:
            return BG

    def _dark_btn(self, parent, text, cmd, color=ACCENT, fg="white", **pack_kw):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg=fg, font=("Arial", 10, "bold"),
                      relief="flat", bd=0, padx=12, pady=6,
                      activebackground=color, activeforeground=fg, cursor="hand2")
        b.pack(**pack_kw)
        return b

    def _field(self, parent, label, default="", show=None):
        self._lbl(parent, label, fg=DIM, bg=self._bg(parent),
                  font=("Arial", 10)).pack(anchor="w", pady=(10, 2))
        e = tk.Entry(parent, bg=INPUT, fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=("Arial", 11), bd=6, width=34)
        if show:
            e.config(show=show)
        e.insert(0, default)
        e.pack(anchor="w")
        return e

    # ── PRE-LOGIN SCREENS ──────────────────────────────────────────────────

    def show_main_menu(self):
        self.clear_window()
        self.root.geometry("780x560")

        frame = tk.Frame(self.root, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(frame, "★  NASA HUNCH", font=("Arial", 12), fg=DIM, bg=BG).pack(pady=(0, 6))
        self._lbl(frame, "Medical Inventory System",
                  font=("Arial", 22, "bold"), fg=TEXT, bg=BG).pack(pady=(0, 32))

        self._dark_btn(frame, "Login",         self.show_login,
                       fill="x", pady=(0, 8))
        self._dark_btn(frame, "Create User",   self.show_create_user,
                       color=INPUT, fill="x", pady=(0, 8))
        self._dark_btn(frame, "Exit",          self.root.quit,
                       color="#2d1b1b", fg=RED, fill="x")

    def show_login(self):
        self.clear_window()

        frame = tk.Frame(self.root, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(frame, "Login", font=("Arial", 20, "bold"), fg=TEXT, bg=BG).pack(pady=(0, 24))

        user_e = self._field(frame, "Username / Crew ID")
        pass_e = self._field(frame, "Password", show="*")

        def attempt_login():
            username = user_e.get().strip()
            password = pass_e.get()
            result = login(username, password)
            if result is None:
                messagebox.showerror("Login Failed", "Invalid username or password.")
                return
            user_id, role = result
            if not os.path.exists("model.yml"):
                messagebox.showerror(
                    "Face Model Missing",
                    "No face recognition model found.\n"
                    "Please create your user account again so your face can be registered."
                )
                return
            messagebox.showinfo("Face Verification",
                                "Password verified.\nCamera will open – please look at the camera.\n"
                                "Press 'q' if you need to cancel.")
            detected_id = recognize_user()
            success, msg = verify_identity(user_id, detected_id)
            if success:
                messagebox.showinfo("Access Granted", msg)
                self.show_home_page(user_id, role)
            else:
                messagebox.showerror("Access Denied", msg)

        self._dark_btn(frame, "Login",   attempt_login, fill="x", pady=(20, 8))
        self._dark_btn(frame, "← Back",  self.show_main_menu, color=INPUT, fill="x")

    def show_create_user(self):
        self.clear_window()

        frame = tk.Frame(self.root, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        self._lbl(frame, "Create New User",
                  font=("Arial", 20, "bold"), fg=TEXT, bg=BG).pack(pady=(0, 24))

        user_e = self._field(frame, "Username / Crew ID")
        pass_e = self._field(frame, "Password", show="*")

        self._lbl(frame, "Role", fg=DIM, bg=BG, font=("Arial", 10)).pack(anchor="w", pady=(10, 4))
        role_var = tk.StringVar(value="crew")
        role_row = tk.Frame(frame, bg=BG)
        role_row.pack(anchor="w")
        for val, label in [("crew", "Crew"), ("medic", "Medic"), ("admin", "Admin")]:
            tk.Radiobutton(role_row, text=label, variable=role_var, value=val,
                           bg=BG, fg=TEXT, selectcolor=INPUT,
                           activebackground=BG, font=("Arial", 10)).pack(side="left", padx=(0, 14))

        def save_user():
            username = user_e.get().strip()
            password = pass_e.get()
            role     = role_var.get()
            if not username or not password:
                messagebox.showerror("Error", "All fields are required.")
                return
            if role in ("admin", "medic"):
                if not self._request_admin_auth():
                    return   # cancelled or failed — do nothing
            user_id = create_user(username, password, role)
            if user_id is None:
                messagebox.showerror("Error", "Username already exists.")
                return
            messagebox.showinfo("Face Capture",
                                "Camera will open to register your face.\nPress 'q' when done.")
            capture_faces(user_id, num_images=50)
            train_model()
            messagebox.showinfo("Success", f"User '{username}' created and face registered.")
            self.show_main_menu()

        self._dark_btn(frame, "Create User", save_user, fill="x", pady=(20, 8))
        self._dark_btn(frame, "← Back", self.show_main_menu, color=INPUT, fill="x")

    # ── POST-LOGIN LAYOUT ──────────────────────────────────────────────────

    def show_home_page(self, user_id, role):
        self.clear_window()
        self.current_user_id   = user_id
        self.current_user_role = role
        self.root.geometry("1160x730")
        self._build_header()
        self._build_nav()
        self.content_frame = tk.Frame(self.root, bg=BG)
        self.content_frame.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        self.show_dashboard_content()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=CARD, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        self._lbl(hdr, "NASA HUNCH  |  Medical Inventory System",
                  font=("Arial", 13, "bold"), fg=TEXT, bg=CARD).pack(side="left", padx=16, pady=12)
        tk.Button(hdr, text="Logout", command=self.show_main_menu,
                  bg=RED, fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=12, pady=4, cursor="hand2").pack(side="right", padx=12, pady=10)
        self._lbl(hdr,
                  f"User {self.current_user_id}  ·  {self.current_user_role.upper()}",
                  fg=DIM, bg=CARD, font=("Arial", 10)).pack(side="right", padx=4, pady=12)

    def _build_nav(self):
        nav = tk.Frame(self.root, bg=NAV, height=38)
        nav.pack(fill="x")
        nav.pack_propagate(False)
        items = [
            ("Dashboard",    "dash", self.show_dashboard_content),
            ("Inventory",    "inv",  self.show_inventory_content),
            ("Calendar",     "cal",  self.show_calendar_content),
            ("Profile",      "pro",  self.show_profile_content),
        ]
        if self.current_user_role == "medic":
            items.append(("Medical Docs", "med", self.show_medical_docs_content))
        if self.current_user_role == "admin":
            items.append(("Manage Users", "usr", self.show_manage_users_content))
        for label, key, cmd in items:
            b = tk.Button(nav, text=label,
                          command=lambda k=key, c=cmd: [self._set_active(k), c()],
                          bg=NAV, fg=DIM, font=("Arial", 10),
                          relief="flat", bd=0, padx=20,
                          activebackground=CARD, activeforeground=TEXT, cursor="hand2")
            b.pack(side="left", fill="y")
            self._nav_btns[key] = b
        self._set_active("dash")

    def _set_active(self, key):
        for k, b in self._nav_btns.items():
            b.config(bg=ACCENT if k == key else NAV,
                     fg="white" if k == key else DIM)

    # ── DASHBOARD ──────────────────────────────────────────────────────────

    def show_dashboard_content(self):
        self._clear_content()
        cf = self.content_frame
        stats = get_dashboard_stats()
        risk_label, risk_color = get_risk_level()
        alerts = get_alerts()

        # KPI cards
        cards_row = tk.Frame(cf, bg=BG)
        cards_row.pack(fill="x", pady=(0, 12))
        for label, value, color in [
            ("Total Supplies",  stats["total"],     ACCENT),
            ("Low Stock Items", stats["low_stock"],  YELLOW),
            ("Expired Items",   stats["expired"],    RED),
            ("Total Checkouts", stats["checkouts"],  GREEN),
        ]:
            self._kpi_card(cards_row, label, value, color)

        # Bottom: two stacked charts on left, status+alerts on right
        bottom = tk.Frame(cf, bg=BG)
        bottom.pack(fill="both", expand=True)
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=2)   # weekly chart — taller
        bottom.grid_rowconfigure(1, weight=1)   # forecast chart — shorter

        # ── Weekly usage chart (top-left) ──────────────────────────────
        weekly_f = tk.Frame(bottom, bg=CARD)
        weekly_f.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 4))
        self._lbl(weekly_f, "Weekly Medical Usage",
                  font=("Arial", 11, "bold"), fg=TEXT, bg=CARD).pack(anchor="w", padx=12, pady=(10, 2))

        weekly = get_weekly_usage()
        days   = [d for d, _ in weekly]
        counts = [c for _, c in weekly]

        self._fig = Figure(figsize=(8, 3), facecolor=CARD)
        self._fig.set_tight_layout({"pad": 1.5})
        ax = self._fig.add_subplot(111)
        ax.set_facecolor(CARD)
        ax.plot(days, counts, color=ACCENT, linewidth=2, marker="o", markersize=5)
        ax.fill_between(range(len(days)), counts, alpha=0.12, color=ACCENT)
        ax.set_xticks(range(len(days)))
        ax.set_xticklabels(days)
        ax.tick_params(colors=DIM, labelsize=8)
        ax.set_ylabel("Items Used", color=DIM, fontsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)

        self._canvas = self._embed_chart(self._fig, weekly_f)

        # ── Predictive supply forecast (bottom-left) ───────────────────
        forecast_f = tk.Frame(bottom, bg=CARD)
        forecast_f.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(4, 0))

        # Title + search row
        top_row = tk.Frame(forecast_f, bg=CARD)
        top_row.pack(fill="x", padx=12, pady=(10, 6))
        self._lbl(top_row, "Predictive Supply Forecast",
                  font=("Arial", 11, "bold"), fg=TEXT, bg=CARD).pack(side="left")

        all_inv   = get_all_items()
        item_names = [r[1] for r in all_inv]
        item_map   = {r[1]: r[0] for r in all_inv}   # name → item_id

        search_row = tk.Frame(forecast_f, bg=CARD)
        search_row.pack(fill="x", padx=12, pady=(0, 6))
        self._lbl(search_row, "Focus on item:", fg=DIM, bg=CARD,
                  font=("Arial", 10)).pack(side="left", padx=(0, 8))

        entry_var = tk.StringVar()
        entry = tk.Entry(search_row, textvariable=entry_var, bg=INPUT, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=("Arial", 10),
                         bd=6, width=28)
        entry.pack(side="left", padx=(0, 6))

        tk.Button(search_row, text="✕",
                  command=lambda: [entry_var.set(""), _hide_popup(), _show_overview()],
                  bg=INPUT, fg=DIM, font=("Arial", 9), relief="flat",
                  padx=6, pady=1, cursor="hand2").pack(side="left")

        _popup = {"win": None}

        def _hide_popup():
            if _popup["win"] and _popup["win"].winfo_exists():
                _popup["win"].destroy()
            _popup["win"] = None

        def _show_popup(matches):
            _hide_popup()
            if not matches:
                return
            entry.update_idletasks()
            x = entry.winfo_rootx()
            y = entry.winfo_rooty() + entry.winfo_height() + 2
            w = max(entry.winfo_width(), 200)
            h = min(len(matches) * 26, 156)

            win = tk.Toplevel(self.root)
            win.wm_overrideredirect(True)
            win.geometry(f"{w}x{h}+{x}+{y}")
            win.config(bg=BORDER)
            _popup["win"] = win

            lb = tk.Listbox(win, bg=INPUT, fg=TEXT, font=("Arial", 10),
                            selectbackground=ACCENT, selectforeground="white",
                            relief="flat", bd=0, activestyle="none",
                            highlightthickness=1, highlightbackground=BORDER)
            vsb = ttk.Scrollbar(win, orient="vertical", command=lb.yview)
            lb.configure(yscrollcommand=vsb.set)
            if len(matches) > 6:
                vsb.pack(side="right", fill="y")
            lb.pack(fill="both", expand=True)

            for m in matches:
                lb.insert("end", f"  {m}")

            def _pick(event=None):
                sel = lb.curselection()
                if not sel:
                    return
                name = lb.get(sel[0]).strip()
                entry_var.set(name)
                _hide_popup()
                if name in item_map:
                    _show_item_detail(item_map[name], name)

            lb.bind("<ButtonRelease-1>", _pick)
            lb.bind("<Return>",          _pick)

            def _nav_down(event):
                lb.focus_set()
                lb.selection_clear(0, "end")
                lb.selection_set(0)
                lb.activate(0)
                return "break"

            def _nav_up_from_list(event):
                if event.keysym == "Up" and lb.curselection() and lb.curselection()[0] == 0:
                    entry.focus_set()
                    return "break"

            entry.bind("<Down>", _nav_down)
            lb.bind("<KeyPress>", _nav_up_from_list)
            lb.bind("<Escape>", lambda e: [_hide_popup(), entry.focus_set()])

        # Dynamic content area
        detail_frame = tk.Frame(forecast_f, bg=CARD)
        detail_frame.pack(fill="both", expand=True)

        def _reset_fig2():
            import matplotlib.pyplot as plt
            if self._fig2 is not None:
                plt.close(self._fig2)
                self._fig2 = None
                self._canvas2 = None
            for w in detail_frame.winfo_children():
                w.destroy()

        def _show_overview():
            _reset_fig2()
            forecast = get_depletion_forecast()
            self._fig2 = Figure(figsize=(8, 2), facecolor=CARD)
            self._fig2.set_tight_layout({"pad": 1.5})
            ax = self._fig2.add_subplot(111)
            ax.set_facecolor(CARD)
            if not forecast:
                ax.text(0.5, 0.5,
                        "No usage data yet — check out items to see the forecast",
                        ha="center", va="center", color=DIM, fontsize=9,
                        transform=ax.transAxes)
                ax.set_xticks([]); ax.set_yticks([])
            else:
                rc = {"NOMINAL": GREEN, "CAUTION": YELLOW, "CRITICAL": RED}
                names_  = [r[0] for r in forecast]
                dvals   = [min(r[3], 120) for r in forecast]
                colors_ = [rc[r[4]] for r in forecast]
                bars = ax.barh(names_, dvals, color=colors_, height=0.5)
                ax.axvline(x=30, color=RED,    linestyle="--", linewidth=1, alpha=0.6)
                ax.axvline(x=60, color=YELLOW, linestyle="--", linewidth=1, alpha=0.6)
                ax.tick_params(colors=DIM, labelsize=8)
                ax.set_xlabel("Days of supply remaining", color=DIM, fontsize=8)
                for spine in ax.spines.values():
                    spine.set_edgecolor(BORDER)
                for bar, row in zip(bars, forecast):
                    lbl = f"{row[3]}d" if row[3] < 120 else "120d+"
                    ax.text(bar.get_width() + 1,
                            bar.get_y() + bar.get_height() / 2,
                            lbl, va="center", color=DIM, fontsize=7)
            self._canvas2 = self._embed_chart(self._fig2, detail_frame)

        def _show_item_detail(item_id, name):
            _reset_fig2()
            info = get_item_forecast(item_id)
            if not info:
                return

            rc_map = {"CRITICAL": RED, "CAUTION": YELLOW, "NOMINAL": GREEN, "UNKNOWN": DIM}
            rc     = rc_map[info["risk"]]

            # Left stats panel
            stats_f = tk.Frame(detail_frame, bg=CARD, padx=14)
            stats_f.pack(side="left", fill="y", pady=10)

            self._lbl(stats_f, name,
                      font=("Arial", 12, "bold"), fg=TEXT, bg=CARD).pack(anchor="w")
            self._lbl(stats_f, f"●  {info['risk']}",
                      font=("Arial", 11, "bold"), fg=rc, bg=CARD).pack(anchor="w", pady=(4, 10))

            stat_rows = [
                ("Current Stock",   f"{info['qty']} units"),
                ("Avg Daily Usage",
                 f"{info['avg_daily']} units / day" if info["avg_daily"] > 0 else "No history"),
                ("Days Remaining",
                 f"{info['days']} days" if info["days"] is not None else "—"),
            ]
            for label, value in stat_rows:
                self._lbl(stats_f, label,
                          font=("Arial", 9), fg=DIM, bg=CARD).pack(anchor="w", pady=(4, 0))
                self._lbl(stats_f, value,
                          font=("Arial", 11, "bold"), fg=TEXT, bg=CARD).pack(anchor="w")

            # Right projection chart
            chart_f = tk.Frame(detail_frame, bg=CARD)
            chart_f.pack(side="left", fill="both", expand=True)

            self._fig2 = Figure(figsize=(6, 2), facecolor=CARD)
            self._fig2.set_tight_layout({"pad": 1.5})
            ax = self._fig2.add_subplot(111)
            ax.set_facecolor(CARD)

            if info["avg_daily"] > 0 and info["days"] is not None:
                end_day = min(info["days"] + 14, 120)
                x = list(range(end_day + 1))
                y = [max(0.0, info["qty"] - info["avg_daily"] * d) for d in x]
                ax.plot(x, y, color=ACCENT, linewidth=2)
                ax.fill_between(x, y, alpha=0.12, color=ACCENT)
                ax.axvline(x=30, color=RED,    linestyle="--", linewidth=1, alpha=0.5)
                ax.axvline(x=60, color=YELLOW, linestyle="--", linewidth=1, alpha=0.5)
                if info["days"] <= end_day:
                    ax.axvline(x=info["days"], color=RED, linewidth=1.5, alpha=0.9)
                    ax.text(info["days"] + 1, max(y) * 0.55,
                            f"Depletes ~{info['days']}d",
                            color=RED, fontsize=7)
                ax.set_xlabel("Days from now", color=DIM, fontsize=8)
                ax.set_ylabel("Stock",         color=DIM, fontsize=8)
            else:
                ax.text(0.5, 0.5, "No checkout history — cannot project depletion",
                        ha="center", va="center", color=DIM, fontsize=9,
                        transform=ax.transAxes)
                ax.set_xticks([]); ax.set_yticks([])

            ax.tick_params(colors=DIM, labelsize=8)
            for spine in ax.spines.values():
                spine.set_edgecolor(BORDER)
            self._canvas2 = self._embed_chart(self._fig2, chart_f)

        def _on_keyrelease(event=None):
            if event and event.keysym in ("Return", "Up", "Down", "Tab"):
                return
            if event and event.keysym == "Escape":
                entry_var.set("")
                _hide_popup()
                _show_overview()
                return
            typed = entry_var.get().strip()
            if typed:
                matches = [n for n in item_names if typed.lower() in n.lower()]
                _show_popup(matches)
            else:
                _hide_popup()
                _show_overview()

        def _on_confirm(event=None):
            name = entry_var.get().strip()
            _hide_popup()
            if name in item_map:
                _show_item_detail(item_map[name], name)
            else:
                _show_overview()

        entry.bind("<KeyRelease>", _on_keyrelease)
        entry.bind("<Return>",     _on_confirm)
        entry.bind("<FocusOut>",   lambda e: self.root.after(200, _hide_popup))
        forecast_f.bind("<Destroy>", lambda e: _hide_popup())

        _show_overview()

        # ── Right column: status + alerts (spans both rows) ────────────
        right = tk.Frame(bottom, bg=BG)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew")

        # Risk status card
        risk_card = tk.Frame(right, bg=CARD)
        risk_card.pack(fill="x", pady=(0, 8))
        self._lbl(risk_card, "System Status",
                  font=("Arial", 10), fg=DIM, bg=CARD).pack(anchor="w", padx=12, pady=(10, 2))
        self._lbl(risk_card, f"●  {risk_label}",
                  font=("Arial", 17, "bold"), fg=risk_color, bg=CARD).pack(anchor="w", padx=12, pady=(0, 12))

        # Alerts card
        alert_card = tk.Frame(right, bg=CARD)
        alert_card.pack(fill="both", expand=True)
        self._lbl(alert_card, "Alerts",
                  font=("Arial", 10), fg=DIM, bg=CARD).pack(anchor="w", padx=12, pady=(10, 4))

        alerts_inner = tk.Frame(alert_card, bg=CARD)
        alerts_inner.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        if not alerts:
            self._lbl(alerts_inner, "✓  No active alerts", fg=GREEN, bg=CARD,
                      font=("Arial", 10)).pack(anchor="w", pady=4)
        else:
            for kind, msg in alerts:
                color = RED if kind == "expired" else YELLOW
                self._lbl(alerts_inner, f"• {msg}", fg=color, bg=CARD,
                          font=("Arial", 9), wraplength=240,
                          justify="left").pack(anchor="w", pady=2)

    def _kpi_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg=CARD, padx=16, pady=10)
        card.pack(side="left", fill="both", expand=True, padx=4)
        tk.Frame(card, bg=color, height=3).pack(fill="x", pady=(0, 8))
        self._lbl(card, str(value),
                  font=("Arial", 28, "bold"), fg=color, bg=CARD).pack(anchor="w")
        self._lbl(card, label,
                  font=("Arial", 10), fg=DIM, bg=CARD).pack(anchor="w")

    # ── INVENTORY ──────────────────────────────────────────────────────────

    def _placeholder_entry(self, parent, placeholder, width=18):
        e = tk.Entry(parent, bg=INPUT, fg=DIM, insertbackground=TEXT,
                     relief="flat", font=("Arial", 10), bd=6, width=width)
        e.insert(0, placeholder)

        def on_in(event):
            if e.get() == placeholder:
                e.delete(0, "end")
                e.config(fg=TEXT)

        def on_out(event):
            if not e.get().strip():
                e.insert(0, placeholder)
                e.config(fg=DIM)

        e.bind("<FocusIn>",  on_in)
        e.bind("<FocusOut>", on_out)
        return e

    def show_inventory_content(self):
        self._clear_content()
        cf       = self.content_frame
        is_admin = (self.current_user_role == "admin")

        self._lbl(cf, "Inventory Management",
                  font=("Arial", 16, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 10))

        # ── inline add form (admin only) ──────────────────────────────────
        if is_admin:
            add_bar = tk.Frame(cf, bg=CARD, padx=14, pady=12)
            add_bar.pack(fill="x", pady=(0, 10))

            name_e = self._placeholder_entry(add_bar, "Item Name",  width=22)
            name_e.pack(side="left", padx=(0, 6))
            qty_e  = self._placeholder_entry(add_bar, "Quantity",   width=10)
            qty_e.pack(side="left", padx=(0, 6))
            exp_e  = self._placeholder_entry(add_bar, "MM/DD/YYYY", width=13)
            exp_e.pack(side="left", padx=(0, 10))

            def do_add():
                name    = name_e.get().strip()
                qty_str = qty_e.get().strip()
                exp_str = exp_e.get().strip()
                if name in ("", "Item Name"):
                    messagebox.showerror("Error", "Item name is required.")
                    return
                if qty_str in ("", "Quantity"):
                    messagebox.showerror("Error", "Quantity is required.")
                    return
                try:
                    qty = int(qty_str)
                except ValueError:
                    messagebox.showerror("Error", "Quantity must be a whole number.")
                    return
                exp_date = None
                if exp_str and exp_str != "MM/DD/YYYY":
                    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
                        try:
                            exp_date = datetime.datetime.strptime(exp_str, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    if exp_date is None:
                        messagebox.showerror("Error", "Date format: MM/DD/YYYY")
                        return
                add_item(name, qty, exp_date)
                self.show_inventory_content()

            tk.Button(add_bar, text="Add Item", command=do_add,
                      bg=ACCENT, fg="white", font=("Arial", 10, "bold"),
                      relief="flat", padx=14, pady=5, cursor="hand2").pack(side="left")

        # ── table: fixed header + scrollable body ────────────────────────
        col_weights = [4, 1, 2, 2, 3]
        headers     = ["Item Name", "Quantity", "Expiration Date", "Checked Out", "Actions"]
        VSB_W       = 17  # scrollbar width reserved in header

        table_wrap = tk.Frame(cf, bg=CARD)
        table_wrap.pack(fill="both", expand=True)

        # Fixed header row (never scrolls)
        hdr = tk.Frame(table_wrap, bg=ACCENT)
        hdr.pack(fill="x")
        for i, (text, w) in enumerate(zip(headers, col_weights)):
            tk.Label(hdr, text=text, bg=ACCENT, fg="white",
                     font=("Arial", 10, "bold")).grid(row=0, column=i,
                     sticky="ew", padx=8, pady=8)
            hdr.grid_columnconfigure(i, weight=w)
        # Placeholder to stay aligned with scrollbar when it appears
        vsb_spacer = tk.Frame(hdr, bg=ACCENT, width=0)
        vsb_spacer.grid(row=0, column=len(headers), sticky="ns")

        # Scrollable body
        body = tk.Frame(table_wrap, bg=CARD)
        body.pack(fill="both", expand=True)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(body, bg=CARD, highlightthickness=0)
        vsb    = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        # vsb starts hidden; shown only when content overflows

        inner = tk.Frame(canvas, bg=CARD)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        def _check_overflow(event=None):
            canvas.update_idletasks()
            need_scroll = inner.winfo_reqheight() > canvas.winfo_height()
            if need_scroll:
                vsb.grid(row=0, column=1, sticky="ns")
                vsb_spacer.configure(width=VSB_W)
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
            else:
                vsb.grid_remove()
                vsb_spacer.configure(width=0)
                canvas.unbind_all("<MouseWheel>")

        inner.bind("<Configure>", lambda e: [
            canvas.configure(scrollregion=canvas.bbox("all")),
            canvas.after(10, _check_overflow)
        ])
        canvas.bind("<Configure>", lambda e: [
            canvas.itemconfig(win, width=e.width),
            canvas.after(10, _check_overflow)
        ])

        # Data rows (same column weights as header → columns align)
        items = get_all_items()
        if not items:
            tk.Label(inner, text="No items in inventory.",
                     bg=CARD, fg=DIM, font=("Arial", 10)).pack(pady=20)
        else:
            for idx, item in enumerate(items):
                item_id, name, qty, exp, checked_out, _ = item
                row_bg = CARD if idx % 2 == 0 else "#141d27"
                qty_fg = RED if qty == 0 else (YELLOW if qty <= 5 else TEXT)

                row_f = tk.Frame(inner, bg=row_bg)
                row_f.pack(fill="x")
                for i, w in enumerate(col_weights):
                    row_f.grid_columnconfigure(i, weight=w)
                tk.Frame(inner, bg=BORDER, height=1).pack(fill="x")

                tk.Label(row_f, text=name,             bg=row_bg, fg=TEXT,   font=("Arial", 10), anchor="w"     ).grid(row=0, column=0, sticky="ew", padx=(12, 4), pady=8)
                tk.Label(row_f, text=str(qty),          bg=row_bg, fg=qty_fg, font=("Arial", 10), anchor="center").grid(row=0, column=1, sticky="ew", padx=4,       pady=8)
                tk.Label(row_f, text=exp or "-",        bg=row_bg, fg=TEXT,   font=("Arial", 10), anchor="center").grid(row=0, column=2, sticky="ew", padx=4,       pady=8)
                tk.Label(row_f, text=str(checked_out),  bg=row_bg, fg=TEXT,   font=("Arial", 10), anchor="center").grid(row=0, column=3, sticky="ew", padx=4,       pady=8)

                btn_f = tk.Frame(row_f, bg=row_bg)
                btn_f.grid(row=0, column=4, sticky="ew", padx=6, pady=5)

                def _checkout(iid=item_id, q=qty):
                    amt = simpledialog.askinteger(
                        "Checkout", f"Amount (available: {q}):", minvalue=1, parent=self.root)
                    if not amt:
                        return
                    ok, msg = checkout_item(iid, self.current_user_id, amt)
                    if ok:
                        self.show_inventory_content()
                    messagebox.showinfo("Checkout", msg) if ok else messagebox.showerror("Error", msg)

                tk.Button(btn_f, text="Checkout", command=_checkout,
                          bg=GREEN, fg="white", font=("Arial", 9, "bold"),
                          relief="flat", padx=8, pady=3, cursor="hand2").pack(side="left", padx=2)

                if is_admin:
                    tk.Button(btn_f, text="Edit",
                              command=lambda iid=item_id: self._show_item_form(iid),
                              bg="#cc8800", fg="white", font=("Arial", 9, "bold"),
                              relief="flat", padx=8, pady=3, cursor="hand2").pack(side="left", padx=2)

                    def _delete(iid=item_id, n=name):
                        if messagebox.askyesno("Delete", f"Delete '{n}'?"):
                            delete_item(iid)
                            self.show_inventory_content()

                    tk.Button(btn_f, text="Delete", command=_delete,
                              bg=RED, fg="white", font=("Arial", 9, "bold"),
                              relief="flat", padx=8, pady=3, cursor="hand2").pack(side="left", padx=2)

    def _show_item_form(self, item_id=None):
        self._clear_content()
        cf       = self.content_frame
        existing = get_item(item_id) if item_id else None

        self._lbl(cf, "Edit Item" if existing else "Add Item",
                  font=("Arial", 15, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 4))

        form = tk.Frame(cf, bg=BG)
        form.pack(anchor="w")

        name_e = self._field(form, "Item Name",
                             default=existing[1] if existing else "")
        qty_e  = self._field(form, "Quantity",
                             default=str(existing[2]) if existing else "")
        exp_e  = self._field(form, "Expiration Date  (YYYY-MM-DD, optional)",
                             default=(existing[3] or "") if existing else "")

        def save():
            name = name_e.get().strip()
            exp  = exp_e.get().strip() or None
            if not name:
                messagebox.showerror("Error", "Item name is required.")
                return
            try:
                qty = int(qty_e.get())
            except ValueError:
                messagebox.showerror("Error", "Quantity must be a whole number.")
                return
            if item_id:
                edit_item(item_id, name, qty, exp)
            else:
                add_item(name, qty, exp)
            self._set_active("inv")
            self.show_inventory_content()

        btn_row = tk.Frame(cf, bg=BG)
        btn_row.pack(anchor="w", pady=18)
        tk.Button(btn_row, text="Save", command=save,
                  bg=ACCENT, fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=5, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel", command=self.show_inventory_content,
                  bg=INPUT, fg=TEXT, font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=5, cursor="hand2").pack(side="left")

    # ── PROFILE ────────────────────────────────────────────────────────────

    def show_profile_content(self):
        self._clear_content()
        cf = self.content_frame

        row = get_health_notes(self.current_user_id)
        if not row:
            return
        username, role, health_notes = row

        layout = tk.Frame(cf, bg=BG)
        layout.pack(fill="both", expand=True)
        layout.grid_columnconfigure(0, weight=1)
        layout.grid_columnconfigure(1, weight=2)
        layout.grid_rowconfigure(0, weight=1)

        # ── Left: profile card ──────────────────────────────────────────
        prof_f = tk.Frame(layout, bg=CARD)
        prof_f.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._lbl(prof_f, "◉", font=("Arial", 42), fg=DIM, bg=CARD).pack(pady=(24, 4))
        self._lbl(prof_f, username,
                  font=("Arial", 14, "bold"), fg=TEXT, bg=CARD).pack()
        role_color = ACCENT if role == "admin" else GREEN
        self._lbl(prof_f, role.upper(),
                  font=("Arial", 10, "bold"), fg=role_color, bg=CARD).pack(pady=(2, 18))

        tk.Frame(prof_f, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0, 14))

        self._lbl(prof_f, "Health Notes",
                  font=("Arial", 10), fg=DIM, bg=CARD).pack(anchor="w", padx=16)
        notes_box = tk.Text(prof_f, bg=INPUT, fg=TEXT, insertbackground=TEXT,
                            relief="flat", font=("Arial", 10), bd=6,
                            width=24, height=7, wrap="word")
        notes_box.pack(padx=16, pady=(4, 8), fill="x")
        if health_notes:
            notes_box.insert("1.0", health_notes)

        def save_notes():
            update_health_notes(self.current_user_id, notes_box.get("1.0", "end-1c").strip())
            messagebox.showinfo("Saved", "Health notes updated.")

        tk.Button(prof_f, text="Save Notes", command=save_notes,
                  bg=ACCENT, fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=12, pady=4, cursor="hand2").pack(padx=16, anchor="w")

        tk.Frame(prof_f, bg=BORDER, height=1).pack(fill="x", padx=16, pady=16)

        tk.Button(prof_f, text="  Scan Medication Barcode",
                  command=lambda: [self._set_active("pro"),
                                   self.show_barcode_scanner_content()],
                  bg=INPUT, fg=TEXT, font=("Arial", 10, "bold"),
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(padx=16, fill="x")

        tk.Button(prof_f, text="  Identify Pill Imprint",
                  command=lambda: [self._set_active("pro"),
                                   self.show_pill_scanner_content()],
                  bg=INPUT, fg=TEXT, font=("Arial", 10, "bold"),
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(padx=16, fill="x", pady=(4, 0))

        # ── Right: activity ─────────────────────────────────────────────
        act_f = tk.Frame(layout, bg=BG)
        act_f.grid(row=0, column=1, sticky="nsew")
        act_f.grid_rowconfigure(0, weight=1)
        act_f.grid_rowconfigure(1, weight=1)
        act_f.grid_columnconfigure(0, weight=1)

        # ── Checkout history ────────────────────────────────────────────
        hist_f = tk.Frame(act_f, bg=BG)
        hist_f.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self._lbl(hist_f, "My Medications",
                  font=("Arial", 12, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 6))

        tbl_f = tk.Frame(hist_f, bg=CARD)
        tbl_f.pack(fill="both", expand=True)

        cols = ("Date", "Medication", "Qty")
        tree = ttk.Treeview(tbl_f, columns=cols, show="headings",
                            style="Dark.Treeview", selectmode="none", height=6)
        for col, w, anchor in [("Date", 110, "center"), ("Medication", 240, "w"), ("Qty", 70, "center")]:
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor=anchor)

        history = get_user_checkout_history(self.current_user_id, limit=20)
        if not history:
            tree.insert("", "end", values=("—", "No medications checked out yet", "—"))
        else:
            for item_name, amount, timestamp in history:
                tree.insert("", "end", values=(
                    timestamp[:10] if timestamp else "—",
                    item_name, amount,
                ))

        vsb = ttk.Scrollbar(tbl_f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        # ── Personal medications ────────────────────────────────────────
        pm_f = tk.Frame(act_f, bg=BG)
        pm_f.grid(row=1, column=0, sticky="nsew")

        hdr_row = tk.Frame(pm_f, bg=BG)
        hdr_row.pack(fill="x", pady=(0, 6))
        self._lbl(hdr_row, "Personal Medications",
                  font=("Arial", 12, "bold"), fg=TEXT, bg=BG).pack(side="left")
        tk.Button(hdr_row, text="Identify Pill",
                  command=lambda: [self._set_active("pro"),
                                   self.show_pill_scanner_content()],
                  bg=INPUT, fg=DIM, font=("Arial", 9, "bold"),
                  relief="flat", padx=8, pady=2,
                  cursor="hand2").pack(side="right", padx=(4, 0))
        tk.Button(hdr_row, text="Scan Barcode",
                  command=lambda: [self._set_active("pro"),
                                   self.show_barcode_scanner_content()],
                  bg=INPUT, fg=DIM, font=("Arial", 9, "bold"),
                  relief="flat", padx=8, pady=2,
                  cursor="hand2").pack(side="right", padx=(4, 0))

        # ── Inline add form ─────────────────────────────────────────────
        add_bar = tk.Frame(pm_f, bg=CARD, padx=10, pady=8)
        add_bar.pack(fill="x", pady=(0, 6))

        name_e   = self._placeholder_entry(add_bar, "Medication name", width=20)
        name_e.pack(side="left", padx=(0, 4))
        dosage_e = self._placeholder_entry(add_bar, "Dosage",          width=14)
        dosage_e.pack(side="left", padx=(0, 4))
        notes_e  = self._placeholder_entry(add_bar, "Notes (optional)", width=18)
        notes_e.pack(side="left", padx=(0, 8))

        pm_tbl_f = tk.Frame(pm_f, bg=CARD)
        pm_tbl_f.pack(fill="both", expand=True)

        pm_cols = ("Name", "Dosage", "Notes", "Added", "")
        pm_tree = ttk.Treeview(pm_tbl_f, columns=pm_cols, show="headings",
                               style="Dark.Treeview", selectmode="browse", height=5)
        for col, w, anchor in [
            ("Name",   180, "w"), ("Dosage", 110, "w"),
            ("Notes",  160, "w"), ("Added",   95, "center"), ("", 60, "center"),
        ]:
            pm_tree.heading(col, text=col)
            pm_tree.column(col, width=w, anchor=anchor)

        def _load_pm():
            for row in pm_tree.get_children():
                pm_tree.delete(row)
            meds = get_personal_medications(self.current_user_id)
            if not meds:
                pm_tree.insert("", "end",
                               values=("No personal medications saved", "", "", "", ""))
            else:
                for pm_id, name, dosage, notes, _, added in meds:
                    pm_tree.insert("", "end", iid=str(pm_id), values=(
                        name, dosage or "—", notes or "—",
                        added[:10] if added else "—", "✕ Remove",
                    ))

        def _add_manual():
            name   = name_e.get().strip()
            dosage = dosage_e.get().strip()
            notes  = notes_e.get().strip()
            if name in ("", "Medication name"):
                messagebox.showerror("Error", "Medication name is required.")
                return
            add_personal_medication(
                self.current_user_id, name,
                dosage=dosage if dosage != "Dosage"           else None,
                notes=notes   if notes  != "Notes (optional)" else None,
            )
            # clear fields
            for e, ph in [(name_e, "Medication name"), (dosage_e, "Dosage"),
                          (notes_e, "Notes (optional)")]:
                e.delete(0, "end")
                e.insert(0, ph)
                e.config(fg=DIM)
            _load_pm()

        tk.Button(add_bar, text="Add", command=_add_manual,
                  bg=GREEN, fg="white", font=("Arial", 9, "bold"),
                  relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="left")

        def _on_pm_click(event):
            item = pm_tree.identify_row(event.y)
            col  = pm_tree.identify_column(event.x)
            if item and col == "#5":
                try:
                    delete_personal_medication(int(item))
                    _load_pm()
                except ValueError:
                    pass

        pm_tree.bind("<ButtonRelease-1>", _on_pm_click)

        pm_vsb = ttk.Scrollbar(pm_tbl_f, orient="vertical", command=pm_tree.yview)
        pm_tree.configure(yscrollcommand=pm_vsb.set)
        pm_vsb.pack(side="right", fill="y")
        pm_tree.pack(fill="both", expand=True)
        _load_pm()

    # ── PILL IMPRINT SCANNER ───────────────────────────────────────────────

    def show_pill_scanner_content(self):
        import threading
        from pill_recognition import capture_pill_frame, detect_pill_attributes, lookup_rximage

        self._clear_content()
        cf = self.content_frame

        self._lbl(cf, "Pill Identifier",
                  font=("Arial", 14, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 12))

        layout = tk.Frame(cf, bg=BG)
        layout.pack(fill="both", expand=True)
        layout.grid_columnconfigure(0, weight=1)
        layout.grid_columnconfigure(1, weight=2)
        layout.grid_rowconfigure(0, weight=1)

        # ── Left: instructions + trigger ────────────────────────────────
        scan_f = tk.Frame(layout, bg=CARD)
        scan_f.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._lbl(scan_f, "How to use",
                  font=("Arial", 11, "bold"), fg=TEXT, bg=CARD).pack(anchor="w", padx=16, pady=(16, 8))
        for step in [
            "1. Click Open Scanner below",
            "2. Centre the pill in the circle",
            "3. Press SPACE to capture",
            "   Press Q to cancel",
            "",
            "The camera detects colour & shape",
            "automatically — even if blurry.",
            "",
            "Then type the imprint you can see",
            "on the pill with your own eyes.",
        ]:
            self._lbl(scan_f, step, font=("Arial", 10), fg=DIM,
                      bg=CARD).pack(anchor="w", padx=20, pady=1)

        tk.Frame(scan_f, bg=BORDER, height=1).pack(fill="x", padx=16, pady=16)

        # ── Right: result panel (scrollable) ────────────────────────────
        res_f = tk.Frame(layout, bg=CARD)
        res_f.grid(row=0, column=1, sticky="nsew")
        res_f.grid_rowconfigure(1, weight=1)
        res_f.grid_columnconfigure(0, weight=1)

        self._lbl(res_f, "Result",
                  font=("Arial", 11, "bold"), fg=TEXT,
                  bg=CARD).grid(row=0, column=0, columnspan=2,
                                sticky="w", padx=14, pady=(12, 8))

        canvas = tk.Canvas(res_f, bg=CARD, highlightthickness=0)
        vsb    = ttk.Scrollbar(res_f, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=1, column=0, sticky="nsew", padx=(14, 0), pady=(0, 12))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 12))

        res_body = tk.Frame(canvas, bg=CARD)
        _win = canvas.create_window((0, 0), window=res_body, anchor="nw")

        def _on_res_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            need = res_body.winfo_reqheight() > canvas.winfo_height()
            vsb.grid() if need else vsb.grid_remove()

        def _on_canvas_resize(e):
            canvas.itemconfig(_win, width=e.width)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        res_body.bind("<Configure>", _on_res_configure)
        canvas.bind("<Configure>", _on_canvas_resize)
        canvas.bind("<Enter>",  lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>",  lambda e: canvas.unbind_all("<MouseWheel>"))

        self._lbl(res_body, "Click 'Open Scanner' to begin.",
                  fg=DIM, bg=CARD, font=("Arial", 10)).pack(anchor="w")

        def _clear_result():
            for w in res_body.winfo_children():
                w.destroy()

        def _show_matches(matches, imprint_val, colour, shape):
            # Remove old match cards — keep attrs block, colour picker, divider, search row
            children = res_body.winfo_children()
            keep = 4
            for w in children[keep:]:
                w.destroy()

            if not matches:
                self._lbl(res_body, "No matches found — try a different imprint.",
                          fg=DIM, bg=CARD, font=("Arial", 10),
                          wraplength=320).pack(anchor="w", pady=(8, 0))
                return

            self._lbl(res_body,
                      f"{len(matches)} match{'es' if len(matches) != 1 else ''} found:",
                      font=("Arial", 9), fg=DIM, bg=CARD).pack(anchor="w", pady=(8, 4))

            is_admin = (self.current_user_role == "admin")

            for m in matches[:4]:
                name     = m.get("name", "Unknown")
                generic  = m.get("generic", "")
                strength = m.get("strength", "")
                form     = m.get("dosage_form", "")
                supplied = m.get("how_supplied", "")

                card = tk.Frame(res_body, bg=INPUT)
                card.pack(fill="x", pady=(0, 6))

                # Header: name + strength
                hdr = tk.Frame(card, bg=INPUT)
                hdr.pack(fill="x", padx=10, pady=(8, 2))
                self._lbl(hdr, name, font=("Arial", 11, "bold"),
                          fg=TEXT, bg=INPUT).pack(side="left")
                if strength:
                    self._lbl(hdr, f"  {strength}", font=("Arial", 10),
                              fg=YELLOW, bg=INPUT).pack(side="left")

                for label, value in [
                    ("Form",         form    or ""),
                    ("Generic name", generic or ""),
                    ("How supplied", supplied or ""),
                ]:
                    if not value:
                        continue
                    row = tk.Frame(card, bg=INPUT)
                    row.pack(fill="x", padx=10, pady=1)
                    self._lbl(row, f"{label}:", font=("Arial", 9),
                              fg=DIM, bg=INPUT).pack(anchor="nw", side="left")
                    self._lbl(row, value, font=("Arial", 9), fg=TEXT, bg=INPUT,
                              wraplength=260, justify="left").pack(side="left", padx=(6, 0))

                # ── Action buttons ────────────────────────────────────────
                btn_row = tk.Frame(card, bg=INPUT)
                btn_row.pack(fill="x", padx=10, pady=(6, 8))

                # Inline form container (hidden until a button is pressed)
                form_frame = tk.Frame(card, bg=INPUT)

                def _show_personal_form(card=card, form_frame=form_frame,
                                        drug_name=name, btn_row=btn_row):
                    for w in form_frame.winfo_children():
                        w.destroy()
                    form_frame.pack(fill="x", padx=10, pady=(0, 8))

                    self._lbl(form_frame, "Add to My Profile",
                              font=("Arial", 9, "bold"), fg=GREEN,
                              bg=INPUT).pack(anchor="w", pady=(0, 4))

                    name_var   = tk.StringVar(value=drug_name)
                    dosage_var = tk.StringVar()
                    expiry_var = tk.StringVar()

                    for lbl, var, ph in [
                        ("Name",   name_var,   drug_name),
                        ("Dosage", dosage_var, "e.g. 200mg"),
                        ("Expiry", expiry_var, "MM/DD/YYYY"),
                    ]:
                        r = tk.Frame(form_frame, bg=INPUT)
                        r.pack(fill="x", pady=1)
                        self._lbl(r, f"{lbl}:", font=("Arial", 9),
                                  fg=DIM, bg=INPUT).pack(side="left", padx=(0, 4))
                        e = tk.Entry(r, textvariable=var, bg=CARD, fg=TEXT,
                                     insertbackground=TEXT, relief="flat",
                                     font=("Arial", 9), bd=4, width=20)
                        e.pack(side="left")

                    def _save_personal():
                        n = name_var.get().strip()
                        if not n:
                            messagebox.showerror("Error", "Name is required.")
                            return
                        d = dosage_var.get().strip() or None
                        exp_raw = expiry_var.get().strip()
                        exp = None
                        if exp_raw and exp_raw != "MM/DD/YYYY":
                            for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
                                try:
                                    exp = datetime.datetime.strptime(
                                        exp_raw, fmt).strftime("%Y-%m-%d")
                                    break
                                except ValueError:
                                    continue
                            if not exp:
                                messagebox.showerror("Error", "Date format: MM/DD/YYYY")
                                return
                        add_personal_medication(
                            self.current_user_id, n, None, d, None, exp)
                        messagebox.showinfo("Saved", f"'{n}' added to your profile.")
                        form_frame.pack_forget()

                    act = tk.Frame(form_frame, bg=INPUT)
                    act.pack(anchor="w", pady=(4, 0))
                    tk.Button(act, text="Save", command=_save_personal,
                              bg=GREEN, fg="white", font=("Arial", 9, "bold"),
                              relief="flat", padx=8, pady=2,
                              cursor="hand2").pack(side="left", padx=(0, 4))
                    tk.Button(act, text="Cancel",
                              command=form_frame.pack_forget,
                              bg=INPUT, fg=DIM, font=("Arial", 9, "bold"),
                              relief="flat", padx=8, pady=2,
                              cursor="hand2").pack(side="left")

                tk.Button(btn_row, text="Add to My Profile",
                          command=_show_personal_form,
                          bg=GREEN, fg="white", font=("Arial", 9, "bold"),
                          relief="flat", padx=8, pady=3,
                          cursor="hand2").pack(side="left", padx=(0, 6))

                if is_admin:
                    def _show_inventory_form(form_frame=form_frame,
                                             drug_name=name):
                        for w in form_frame.winfo_children():
                            w.destroy()
                        form_frame.pack(fill="x", padx=10, pady=(0, 8))

                        self._lbl(form_frame, "Add to Ship Inventory",
                                  font=("Arial", 9, "bold"), fg=ACCENT,
                                  bg=INPUT).pack(anchor="w", pady=(0, 4))

                        name_var   = tk.StringVar(value=drug_name)
                        qty_var    = tk.StringVar()
                        expiry_var = tk.StringVar()

                        for lbl, var, ph in [
                            ("Name",     name_var,   drug_name),
                            ("Quantity", qty_var,    "e.g. 30"),
                            ("Expiry",   expiry_var, "MM/DD/YYYY"),
                        ]:
                            r = tk.Frame(form_frame, bg=INPUT)
                            r.pack(fill="x", pady=1)
                            self._lbl(r, f"{lbl}:", font=("Arial", 9),
                                      fg=DIM, bg=INPUT).pack(side="left", padx=(0, 4))
                            e = tk.Entry(r, textvariable=var, bg=CARD, fg=TEXT,
                                         insertbackground=TEXT, relief="flat",
                                         font=("Arial", 9), bd=4, width=20)
                            e.pack(side="left")

                        def _save_inventory():
                            n = name_var.get().strip()
                            if not n:
                                messagebox.showerror("Error", "Name is required.")
                                return
                            try:
                                qty = int(qty_var.get().strip())
                                if qty <= 0:
                                    raise ValueError
                            except ValueError:
                                messagebox.showerror(
                                    "Error", "Quantity must be a positive number.")
                                return
                            exp_raw = expiry_var.get().strip()
                            exp = None
                            if exp_raw and exp_raw != "MM/DD/YYYY":
                                for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
                                    try:
                                        exp = datetime.datetime.strptime(
                                            exp_raw, fmt).strftime("%Y-%m-%d")
                                        break
                                    except ValueError:
                                        continue
                                if not exp:
                                    messagebox.showerror(
                                        "Error", "Date format: MM/DD/YYYY")
                                    return
                            add_item(n, qty, exp)
                            messagebox.showinfo(
                                "Added", f"'{n}' (qty {qty}) added to inventory.")
                            form_frame.pack_forget()

                        act = tk.Frame(form_frame, bg=INPUT)
                        act.pack(anchor="w", pady=(4, 0))
                        tk.Button(act, text="Add", command=_save_inventory,
                                  bg=ACCENT, fg="white", font=("Arial", 9, "bold"),
                                  relief="flat", padx=8, pady=2,
                                  cursor="hand2").pack(side="left", padx=(0, 4))
                        tk.Button(act, text="Cancel",
                                  command=form_frame.pack_forget,
                                  bg=INPUT, fg=DIM, font=("Arial", 9, "bold"),
                                  relief="flat", padx=8, pady=2,
                                  cursor="hand2").pack(side="left")

                    tk.Button(btn_row, text="Add to Inventory",
                              command=_show_inventory_form,
                              bg=ACCENT, fg="white", font=("Arial", 9, "bold"),
                              relief="flat", padx=8, pady=3,
                              cursor="hand2").pack(side="left")

                tk.Frame(card, bg=INPUT, height=4).pack()

        COLOUR_OPTIONS = [
            ("WHITE",     "#f5f5f5"), ("YELLOW",    "#e8c830"),
            ("ORANGE",    "#d86820"), ("RED",        "#c02828"),
            ("PINK",      "#d87090"), ("BROWN",      "#7a5030"),
            ("GREEN",     "#30a040"), ("TURQUOISE",  "#20b0a0"),
            ("BLUE",      "#2858c0"), ("PURPLE",     "#7030b0"),
            ("GRAY",      "#808080"), ("BLACK",      "#202020"),
        ]

        def _show_attrs_and_search(colour, shape, colour_hex, frame):
            _clear_result()

            # mutable so do_search always reads the latest selection
            selected = [colour, colour_hex]

            # ── Detected colour + shape row ──────────────────────────────
            attrs = tk.Frame(res_body, bg=CARD)
            attrs.pack(fill="x", pady=(0, 6))

            swatch = tk.Frame(attrs, bg=colour_hex, width=28, height=28,
                              relief="flat", bd=1)
            swatch.pack(side="left", padx=(0, 8))
            swatch.pack_propagate(False)

            colour_lbl = self._lbl(attrs, f"{colour}  ·  {shape}",
                                   font=("Arial", 11, "bold"), fg=TEXT, bg=CARD)
            colour_lbl.pack(side="left")

            # ── Colour picker ────────────────────────────────────────────
            self._lbl(res_body, "Adjust colour:",
                      font=("Arial", 9), fg=DIM, bg=CARD).pack(anchor="w", pady=(4, 2))

            picker_frame = tk.Frame(res_body, bg=CARD)
            picker_frame.pack(anchor="w", pady=(0, 8))

            btn_refs = {}

            def _pick(name, hex_val):
                selected[0] = name
                selected[1] = hex_val
                swatch.config(bg=hex_val)
                colour_lbl.config(text=f"{name}  ·  {shape}")
                # highlight selected, dim others
                for n, b in btn_refs.items():
                    b.config(relief="sunken" if n == name else "flat",
                             bd=2 if n == name else 1)

            for i, (name, hex_val) in enumerate(COLOUR_OPTIONS):
                btn = tk.Frame(picker_frame, bg=hex_val, width=22, height=22,
                               relief="flat", bd=1, cursor="hand2")
                btn.grid(row=i // 6, column=i % 6, padx=2, pady=2)
                btn.pack_propagate(False)
                btn.bind("<Button-1>", lambda e, n=name, h=hex_val: _pick(n, h))
                btn_refs[name] = btn

            # highlight the auto-detected colour on load
            if colour in btn_refs:
                btn_refs[colour].config(relief="sunken", bd=2)

            tk.Frame(res_body, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))

            # ── Imprint entry + search ───────────────────────────────────
            search_row = tk.Frame(res_body, bg=CARD)
            search_row.pack(fill="x", pady=(0, 4))

            self._lbl(search_row, "Imprint:",
                      font=("Arial", 10), fg=DIM, bg=CARD).pack(side="left", padx=(0, 6))

            imprint_var = tk.StringVar()
            entry = tk.Entry(search_row, textvariable=imprint_var,
                             bg=INPUT, fg=TEXT, insertbackground=TEXT,
                             relief="flat", font=("Arial", 11), bd=6, width=14)
            entry.pack(side="left", padx=(0, 6))
            entry.focus_set()

            def do_search(*_):
                imprint_typed = imprint_var.get().strip().upper()
                def _run():
                    results = lookup_rximage(imprint_typed, selected[0], shape)
                    seen, unique = set(), []
                    for m in results:
                        mid = m.get("ndc11") or m.get("name", "")
                        if mid not in seen:
                            seen.add(mid)
                            unique.append(m)
                    self.root.after(0, lambda: _show_matches(
                        unique, imprint_typed, selected[0], shape))
                threading.Thread(target=_run, daemon=True).start()

            tk.Button(search_row, text="Search", command=do_search,
                      bg=ACCENT, fg="white", font=("Arial", 10, "bold"),
                      relief="flat", padx=10, pady=3,
                      cursor="hand2").pack(side="left")
            tk.Button(search_row, text="Scan Again", command=do_scan,
                      bg=INPUT, fg=DIM, font=("Arial", 10, "bold"),
                      relief="flat", padx=10, pady=3,
                      cursor="hand2").pack(side="left", padx=(6, 0))

            entry.bind("<Return>", do_search)

        def _detect_and_show(frame):
            colour, shape, colour_hex = detect_pill_attributes(frame)
            self.root.after(0, lambda: _show_attrs_and_search(
                colour, shape, colour_hex, frame))

        def do_scan():
            self.root.iconify()
            frame = capture_pill_frame()
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

            if frame is None:
                _clear_result()
                self._lbl(res_body, "Scan cancelled.",
                          fg=DIM, bg=CARD, font=("Arial", 10)).pack(anchor="w")
                return

            _clear_result()
            self._lbl(res_body, "Detecting colour & shape...",
                      fg=YELLOW, bg=CARD,
                      font=("Arial", 10, "italic")).pack(anchor="w")
            res_body.update_idletasks()
            threading.Thread(target=_detect_and_show, args=(frame,), daemon=True).start()

        tk.Button(scan_f, text="Open Scanner", command=do_scan,
                  bg=ACCENT, fg="white", font=("Arial", 12, "bold"),
                  relief="flat", padx=20, pady=10, cursor="hand2").pack(padx=16, fill="x")

    # ── BARCODE SCANNER ────────────────────────────────────────────────────

    def show_barcode_scanner_content(self):
        self._clear_content()
        cf = self.content_frame
        from barcode import scan_barcode

        self._lbl(cf, "Medication Barcode Scanner",
                  font=("Arial", 14, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 12))

        layout = tk.Frame(cf, bg=BG)
        layout.pack(fill="both", expand=True)
        layout.grid_columnconfigure(0, weight=1)
        layout.grid_columnconfigure(1, weight=2)
        layout.grid_rowconfigure(0, weight=1)

        # ── Left: scan trigger ──────────────────────────────────────────
        scan_f = tk.Frame(layout, bg=CARD)
        scan_f.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._lbl(scan_f, "How to scan",
                  font=("Arial", 11, "bold"), fg=TEXT, bg=CARD).pack(anchor="w", padx=16, pady=(16, 8))
        for step in [
            "1. Click Open Scanner below",
            "2. Hold barcode up to camera",
            "3. Keep steady — green box = detected",
            "4. Window closes automatically",
            "   Press Q to cancel",
        ]:
            self._lbl(scan_f, step, font=("Arial", 10), fg=DIM,
                      bg=CARD).pack(anchor="w", padx=20, pady=1)

        tk.Frame(scan_f, bg=BORDER, height=1).pack(fill="x", padx=16, pady=16)

        def do_scan():
            self.root.iconify()          # hide main window so scanner is visible
            barcode = scan_barcode()
            self.root.deiconify()        # restore main window
            self.root.lift()
            self.root.focus_force()
            if barcode:
                _show_result(barcode)
            else:
                _show_result(None)

        tk.Button(scan_f, text="Open Scanner", command=do_scan,
                  bg=ACCENT, fg="white", font=("Arial", 12, "bold"),
                  relief="flat", padx=20, pady=10, cursor="hand2").pack(padx=16, fill="x")

        # ── Right: result panel ─────────────────────────────────────────
        res_f = tk.Frame(layout, bg=CARD)
        res_f.grid(row=0, column=1, sticky="nsew")
        self._lbl(res_f, "Scan Result",
                  font=("Arial", 11, "bold"), fg=TEXT, bg=CARD).pack(anchor="w", padx=14, pady=(12, 8))

        res_body = tk.Frame(res_f, bg=CARD)
        res_body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._lbl(res_body, "Click 'Open Scanner' to begin.",
                  fg=DIM, bg=CARD, font=("Arial", 10)).pack(anchor="w")

        def _clear_result():
            for w in res_body.winfo_children():
                w.destroy()

        def _show_result(barcode_str):
            _clear_result()

            if barcode_str is None:
                self._lbl(res_body, "No barcode detected.",
                          fg=DIM, bg=CARD, font=("Arial", 10)).pack(anchor="w")
                return

            item = get_item_by_barcode(barcode_str)

            if item:
                # ── Ship supply item ────────────────────────────────────
                item_id, name, qty, exp, checked_out, _ = item
                qty_fg = RED if qty == 0 else (YELLOW if qty <= 5 else GREEN)

                tk.Frame(res_body, bg=ACCENT, height=3).pack(fill="x", pady=(0, 10))
                self._lbl(res_body, "SHIP SUPPLY",
                          fg=ACCENT, bg=CARD,
                          font=("Arial", 9, "bold")).pack(anchor="w")
                self._lbl(res_body, name,
                          font=("Arial", 13, "bold"), fg=TEXT,
                          bg=CARD).pack(anchor="w", pady=(2, 0))

                for label, value, vc in [
                    ("Barcode",         barcode_str,      DIM),
                    ("In Stock",        str(qty),         qty_fg),
                    ("Expires",         exp or "—",       TEXT),
                    ("Total Checkouts", str(checked_out), TEXT),
                ]:
                    self._lbl(res_body, label,
                              font=("Arial", 9), fg=DIM, bg=CARD).pack(anchor="w", pady=(6, 0))
                    self._lbl(res_body, value,
                              font=("Arial", 11, "bold"), fg=vc, bg=CARD).pack(anchor="w")

                btn_row = tk.Frame(res_body, bg=CARD)
                btn_row.pack(anchor="w", pady=(14, 0))
                if qty > 0:
                    def do_checkout(iid=item_id, q=qty):
                        amt = simpledialog.askinteger(
                            "Checkout", f"Amount (available: {q}):",
                            minvalue=1, parent=self.root)
                        if not amt:
                            return
                        ok, msg = checkout_item(iid, self.current_user_id, amt)
                        (messagebox.showinfo if ok else messagebox.showerror)("Checkout", msg)
                        if ok:
                            _show_result(barcode_str)
                    tk.Button(btn_row, text="Checkout", command=do_checkout,
                              bg=GREEN, fg="white", font=("Arial", 10, "bold"),
                              relief="flat", padx=12, pady=5,
                              cursor="hand2").pack(side="left", padx=(0, 6))
                tk.Button(btn_row, text="Scan Again", command=do_scan,
                          bg=INPUT, fg=TEXT, font=("Arial", 10, "bold"),
                          relief="flat", padx=12, pady=5,
                          cursor="hand2").pack(side="left")

            else:
                # ── Personal medication (not in ship supply at all) ─────
                personal = get_personal_medication_by_barcode(
                    self.current_user_id, barcode_str)

                if personal:
                    # Already saved — just show it
                    _, pm_name, pm_dosage, pm_notes = personal
                    tk.Frame(res_body, bg=GREEN, height=3).pack(fill="x", pady=(0, 10))
                    self._lbl(res_body, "MY PERSONAL MEDICATION",
                              fg=GREEN, bg=CARD,
                              font=("Arial", 9, "bold")).pack(anchor="w")
                    self._lbl(res_body, pm_name,
                              font=("Arial", 13, "bold"), fg=TEXT,
                              bg=CARD).pack(anchor="w", pady=(2, 0))
                    for label, value in [
                        ("Dosage", pm_dosage or "—"),
                        ("Notes",  pm_notes  or "—"),
                    ]:
                        self._lbl(res_body, label,
                                  font=("Arial", 9), fg=DIM,
                                  bg=CARD).pack(anchor="w", pady=(6, 0))
                        self._lbl(res_body, value,
                                  font=("Arial", 11, "bold"), fg=TEXT,
                                  bg=CARD).pack(anchor="w")
                    self._lbl(res_body,
                              "Visible only on your Profile page.",
                              fg=DIM, bg=CARD,
                              font=("Arial", 9, "italic")).pack(anchor="w", pady=(10, 0))
                    tk.Button(res_body, text="Scan Again", command=do_scan,
                              bg=INPUT, fg=TEXT, font=("Arial", 10, "bold"),
                              relief="flat", padx=12, pady=5,
                              cursor="hand2").pack(anchor="w", pady=(10, 0))

                else:
                    # New barcode — save to personal medications only
                    tk.Frame(res_body, bg=GREEN, height=3).pack(fill="x", pady=(0, 10))
                    self._lbl(res_body, "MY PERSONAL MEDICATION",
                              fg=GREEN, bg=CARD,
                              font=("Arial", 9, "bold")).pack(anchor="w")
                    self._lbl(res_body,
                              "Not part of ship supply.\n"
                              "Saved privately to your profile only.",
                              fg=DIM, bg=CARD,
                              font=("Arial", 9, "italic")).pack(anchor="w", pady=(2, 10))

                    pm_name_e   = self._placeholder_entry(res_body, "Medication name", width=24)
                    pm_name_e.pack(anchor="w", pady=2)
                    pm_dosage_e = self._placeholder_entry(res_body, "Dosage (e.g. 200mg)", width=24)
                    pm_dosage_e.pack(anchor="w", pady=2)
                    pm_notes_e  = self._placeholder_entry(res_body, "Notes (optional)", width=24)
                    pm_notes_e.pack(anchor="w", pady=2)

                    def save_personal():
                        name = pm_name_e.get().strip()
                        if name in ("", "Medication name"):
                            messagebox.showerror("Error", "Medication name is required.")
                            return
                        dosage = pm_dosage_e.get().strip()
                        notes  = pm_notes_e.get().strip()
                        add_personal_medication(
                            self.current_user_id, name, barcode_str,
                            dosage if dosage != "Dosage (e.g. 200mg)" else None,
                            notes  if notes  != "Notes (optional)"    else None,
                        )
                        _show_result(barcode_str)

                    tk.Button(res_body, text="Save to My Profile",
                              command=save_personal,
                              bg=GREEN, fg="white", font=("Arial", 10, "bold"),
                              relief="flat", padx=12, pady=5,
                              cursor="hand2").pack(anchor="w", pady=(8, 0))


    # ── MEDICAL DOCS ───────────────────────────────────────────────────────

    def show_medical_docs_content(self):
        self._clear_content()
        cf = self.content_frame

        self._lbl(cf, "Medical Documentation",
                  font=("Arial", 15, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 10))

        users = get_all_users()

        layout = tk.Frame(cf, bg=BG)
        layout.pack(fill="both", expand=True)
        layout.grid_columnconfigure(0, weight=1)
        layout.grid_columnconfigure(1, weight=3)
        layout.grid_rowconfigure(0, weight=1)

        # ── Left: user list ─────────────────────────────────────────────
        list_f = tk.Frame(layout, bg=CARD)
        list_f.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._lbl(list_f, "Crew Members",
                  font=("Arial", 10), fg=DIM, bg=CARD).pack(anchor="w", padx=12, pady=(10, 6))

        role_colors = {"admin": ACCENT, "medic": YELLOW, "crew": GREEN}

        detail_frame = tk.Frame(layout, bg=BG)
        detail_frame.grid(row=0, column=1, sticky="nsew")

        selected_btn = {"current": None}

        def show_user(user_id, username, role, health_notes, btn):
            # reset previous selection
            if selected_btn["current"]:
                selected_btn["current"].config(bg=CARD)
            btn.config(bg=ACCENT)
            selected_btn["current"] = btn

            # clear detail panel
            for w in detail_frame.winfo_children():
                w.destroy()

            # ── Detail header ────────────────────────────────────────
            hdr = tk.Frame(detail_frame, bg=CARD)
            hdr.pack(fill="x", pady=(0, 8))

            self._lbl(hdr, "◉", font=("Arial", 28), fg=DIM,
                      bg=CARD).pack(side="left", padx=(14, 8), pady=10)

            info = tk.Frame(hdr, bg=CARD)
            info.pack(side="left", pady=10)
            self._lbl(info, username,
                      font=("Arial", 13, "bold"), fg=TEXT, bg=CARD).pack(anchor="w")
            rc = role_colors.get(role, DIM)
            self._lbl(info, role.upper(),
                      font=("Arial", 9, "bold"), fg=rc, bg=CARD).pack(anchor="w")

            # ── Health notes ─────────────────────────────────────────
            notes_card = tk.Frame(detail_frame, bg=CARD)
            notes_card.pack(fill="x", pady=(0, 8))
            self._lbl(notes_card, "Medical Notes",
                      font=("Arial", 10), fg=DIM, bg=CARD).pack(anchor="w", padx=12, pady=(10, 4))

            fresh_row = get_health_notes(user_id)
            current_notes = (fresh_row[2] if fresh_row else None) or ""

            if self.current_user_role in ("medic", "admin"):
                notes_box = tk.Text(notes_card, bg=INPUT, fg=TEXT, insertbackground=TEXT,
                                    relief="flat", font=("Arial", 10), bd=6,
                                    width=40, height=5, wrap="word")
                notes_box.pack(padx=12, pady=(0, 4), fill="x")
                if current_notes:
                    notes_box.insert("1.0", current_notes)

                def save_medical_notes(uid=user_id, box=notes_box):
                    update_health_notes(uid, box.get("1.0", "end-1c").strip())
                    messagebox.showinfo("Saved", "Medical notes updated.")

                tk.Button(notes_card, text="Save Notes", command=save_medical_notes,
                          bg=ACCENT, fg="white", font=("Arial", 10, "bold"),
                          relief="flat", padx=10, pady=3, cursor="hand2").pack(anchor="w", padx=12, pady=(0, 10))
            else:
                notes_text = current_notes or "No medical notes on file."
                self._lbl(notes_card, notes_text,
                          font=("Arial", 10), fg=TEXT, bg=CARD,
                          wraplength=540, justify="left").pack(anchor="w", padx=12, pady=(0, 10))

            # ── Bottom: personal meds + checkout history side by side
            bottom = tk.Frame(detail_frame, bg=BG)
            bottom.pack(fill="both", expand=True)
            bottom.grid_columnconfigure(0, weight=1)
            bottom.grid_columnconfigure(1, weight=1)
            bottom.grid_rowconfigure(0, weight=1)

            # Personal medications
            pm_f = tk.Frame(bottom, bg=CARD)
            pm_f.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            self._lbl(pm_f, "Personal Medications",
                      font=("Arial", 10), fg=DIM, bg=CARD).pack(anchor="w", padx=10, pady=(10, 4))

            pm_tree = ttk.Treeview(pm_f,
                                   columns=("Name", "Dosage", "Notes"),
                                   show="headings", style="Dark.Treeview",
                                   selectmode="none", height=8)
            for col, w in [("Name", 140), ("Dosage", 100), ("Notes", 140)]:
                pm_tree.heading(col, text=col)
                pm_tree.column(col, width=w, anchor="w")

            meds = get_personal_medications(user_id)
            if not meds:
                pm_tree.insert("", "end", values=("No personal medications", "", ""))
            else:
                for _, name, dosage, notes, _, _ in meds:
                    pm_tree.insert("", "end",
                                   values=(name, dosage or "—", notes or "—"))

            pm_vsb = ttk.Scrollbar(pm_f, orient="vertical", command=pm_tree.yview)
            pm_tree.configure(yscrollcommand=pm_vsb.set)
            pm_vsb.pack(side="right", fill="y")
            pm_tree.pack(fill="both", expand=True, padx=(10, 0), pady=(0, 10))

            # Checkout history
            ch_f = tk.Frame(bottom, bg=CARD)
            ch_f.grid(row=0, column=1, sticky="nsew")
            self._lbl(ch_f, "Checkout History",
                      font=("Arial", 10), fg=DIM, bg=CARD).pack(anchor="w", padx=10, pady=(10, 4))

            ch_tree = ttk.Treeview(ch_f,
                                   columns=("Date", "Item", "Qty"),
                                   show="headings", style="Dark.Treeview",
                                   selectmode="none", height=8)
            for col, w, anchor in [("Date", 100, "center"), ("Item", 160, "w"), ("Qty", 50, "center")]:
                ch_tree.heading(col, text=col)
                ch_tree.column(col, width=w, anchor=anchor)

            history = get_user_checkout_history(user_id, limit=30)
            if not history:
                ch_tree.insert("", "end", values=("—", "No checkouts yet", "—"))
            else:
                for item_name, amount, timestamp in history:
                    ch_tree.insert("", "end", values=(
                        timestamp[:10] if timestamp else "—",
                        item_name, amount,
                    ))

            ch_vsb = ttk.Scrollbar(ch_f, orient="vertical", command=ch_tree.yview)
            ch_tree.configure(yscrollcommand=ch_vsb.set)
            ch_vsb.pack(side="right", fill="y")
            ch_tree.pack(fill="both", expand=True, padx=(10, 0), pady=(0, 10))

        # Build user buttons
        for user_id, username, role, health_notes in users:
            rc = role_colors.get(role, DIM)
            row_f = tk.Frame(list_f, bg=CARD, cursor="hand2")
            row_f.pack(fill="x", padx=6, pady=2)

            btn = tk.Button(
                row_f, anchor="w",
                text=f"  {username}",
                font=("Arial", 10, "bold"), fg=TEXT, bg=CARD,
                relief="flat", bd=0, padx=8, pady=6, cursor="hand2",
                activebackground=ACCENT, activeforeground="white",
            )
            btn.pack(side="left", fill="x", expand=True)
            tk.Label(row_f, text=role.upper(),
                     font=("Arial", 8), fg=rc, bg=CARD,
                     padx=6).pack(side="right")

            btn.config(command=lambda uid=user_id, un=username, r=role,
                       hn=health_notes, b=btn: show_user(uid, un, r, hn, b))

        if not users:
            self._lbl(list_f, "No users registered.",
                      fg=DIM, bg=CARD, font=("Arial", 10)).pack(padx=12, pady=12)
        else:
            # Auto-select first user
            first = list_f.winfo_children()
            if len(first) > 1:
                first_btn = first[1].winfo_children()[0]
                uid, un, r, hn = users[0]
                show_user(uid, un, r, hn, first_btn)

    # ── CALENDAR ───────────────────────────────────────────────────────────

    def show_calendar_content(self):
        self._clear_content()
        cf = self.content_frame

        try:
            from tkcalendar import Calendar as TkCal
        except ImportError:
            self._lbl(cf, "tkcalendar not available.", fg=RED, bg=BG).pack()
            return

        today = datetime.date.today()
        left  = tk.Frame(cf, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 16))

        cal = TkCal(left, selectmode="day",
                    year=today.year, month=today.month, day=today.day,
                    background=CARD, foreground=TEXT,
                    selectbackground=ACCENT, selectforeground="white",
                    headersbackground=NAV, headersforeground=TEXT,
                    normalbackground=CARD, normalforeground=TEXT,
                    weekendbackground=CARD, weekendforeground=DIM,
                    othermonthbackground=BG, othermonthforeground=BORDER,
                    font=("Arial", 11), borderwidth=0, showweeknumbers=False)
        cal.pack()

        # Right panel: events
        right = tk.Frame(cf, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._lbl(right, "Mission Events",
                  font=("Arial", 14, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 8))

        # Event list
        list_f = tk.Frame(right, bg=CARD)
        list_f.pack(fill="both", expand=True)

        ev_tree = ttk.Treeview(list_f, columns=("Date", "Title"), show="headings",
                               style="Dark.Treeview", selectmode="browse", height=10)
        ev_tree.heading("Date",  text="Date")
        ev_tree.heading("Title", text="Title")
        ev_tree.column("Date",  width=110, anchor="center")
        ev_tree.column("Title", width=260, anchor="w")
        ev_tree.pack(fill="both", expand=True, padx=4, pady=4)

        def refresh_events():
            for row in ev_tree.get_children():
                ev_tree.delete(row)
            for eid, title, edate, _ in get_calendar_events():
                ev_tree.insert("", "end", iid=str(eid), values=(edate, title))

        refresh_events()

        # Add / delete controls
        ctrl = tk.Frame(right, bg=BG)
        ctrl.pack(fill="x", pady=(8, 0))

        title_var = tk.StringVar()
        tk.Entry(ctrl, textvariable=title_var, bg=INPUT, fg=TEXT,
                 insertbackground=TEXT, relief="flat", bd=5,
                 font=("Arial", 10), width=26).pack(side="left", padx=(0, 6))

        def add_event():
            title = title_var.get().strip()
            if not title:
                messagebox.showwarning("Missing Title", "Enter an event title.")
                return
            selected_date = cal.get_date()
            # tkcalendar returns MM/DD/YY by default; normalise to YYYY-MM-DD
            try:
                dt = datetime.datetime.strptime(selected_date, "%m/%d/%y")
                date_str = dt.strftime("%Y-%m-%d")
            except ValueError:
                date_str = selected_date
            add_calendar_event(title, date_str)
            title_var.set("")
            refresh_events()

        def delete_event():
            sel = ev_tree.selection()
            if not sel:
                return
            delete_calendar_event(int(sel[0]))
            refresh_events()

        tk.Button(ctrl, text="Add Event", command=add_event,
                  bg=ACCENT, fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=10, pady=4, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(ctrl, text="Delete", command=delete_event,
                  bg=RED, fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=10, pady=4, cursor="hand2").pack(side="left")


    # ── MANAGE USERS ───────────────────────────────────────────────────────

    def show_manage_users_content(self):
        self._clear_content()
        cf = self.content_frame

        self._lbl(cf, "Manage Users",
                  font=("Arial", 15, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 10))

        table_wrap = tk.Frame(cf, bg=CARD)
        table_wrap.pack(fill="both", expand=True)

        col_weights = [3, 2, 3, 1]
        headers     = ["Username", "Current Role", "Change Role", ""]

        hdr = tk.Frame(table_wrap, bg=ACCENT)
        hdr.pack(fill="x")
        for i, (text, w) in enumerate(zip(headers, col_weights)):
            tk.Label(hdr, text=text, bg=ACCENT, fg="white",
                     font=("Arial", 10, "bold")).grid(row=0, column=i,
                     sticky="ew", padx=8, pady=8)
            hdr.grid_columnconfigure(i, weight=w)

        body_canvas = tk.Canvas(table_wrap, bg=CARD, highlightthickness=0)
        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=body_canvas.yview)
        body_canvas.configure(yscrollcommand=vsb.set)
        body_canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        inner = tk.Frame(body_canvas, bg=CARD)
        win   = body_canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>", lambda e: body_canvas.configure(
            scrollregion=body_canvas.bbox("all")))
        body_canvas.bind("<Configure>", lambda e: body_canvas.itemconfig(win, width=e.width))

        role_colors = {"admin": ACCENT, "medic": YELLOW, "crew": GREEN}
        ROLES       = ["crew", "medic", "admin"]

        users = get_all_users()

        def _delete_user(user_id, username, row_f, divider):
            if user_id == self.current_user_id:
                messagebox.showerror("Error", "You cannot delete your own account.")
                return
            if not messagebox.askyesno(
                "Delete User — Cannot Be Undone",
                f"Permanently delete '{username}'?\n\n"
                f"This will erase:\n"
                f"  • Their account and login\n"
                f"  • All personal medications\n"
                f"  • All checkout and session history\n"
                f"  • Their face recognition data\n\n"
                f"The face model will need retraining afterward.",
                icon="warning"
            ):
                return
            delete_user_completely(user_id)
            row_f.destroy()
            divider.destroy()
            messagebox.showinfo(
                "Deleted",
                f"'{username}' and all their data have been removed.\n"
                f"Retrain the face model from the registration screen."
            )

        def _set_role(user_id, username, var, role_lbl):
            new_role = var.get()
            if messagebox.askyesno(
                "Confirm",
                f"Change '{username}' to {new_role.upper()}?"
            ):
                update_user_role(user_id, new_role)
                role_lbl.config(text=new_role.upper(),
                                fg=role_colors.get(new_role, DIM))
                messagebox.showinfo("Updated", f"{username} is now {new_role.upper()}.")

        for idx, (user_id, username, role, _) in enumerate(users):
            row_bg = CARD if idx % 2 == 0 else "#141d27"
            row_f   = tk.Frame(inner, bg=row_bg)
            row_f.pack(fill="x")
            for i, w in enumerate(col_weights):
                row_f.grid_columnconfigure(i, weight=w)
            divider = tk.Frame(inner, bg=BORDER, height=1)
            divider.pack(fill="x")

            tk.Label(row_f, text=username, bg=row_bg, fg=TEXT,
                     font=("Arial", 10), anchor="w").grid(
                row=0, column=0, sticky="ew", padx=(12, 4), pady=10)

            role_lbl = tk.Label(row_f, text=role.upper(),
                                bg=row_bg, fg=role_colors.get(role, DIM),
                                font=("Arial", 10, "bold"), anchor="center")
            role_lbl.grid(row=0, column=1, sticky="ew", padx=4, pady=10)

            ctrl = tk.Frame(row_f, bg=row_bg)
            ctrl.grid(row=0, column=2, sticky="ew", padx=6, pady=6)

            var = tk.StringVar(value=role)
            for r in ROLES:
                tk.Radiobutton(ctrl, text=r.capitalize(), variable=var, value=r,
                               bg=row_bg, fg=TEXT, selectcolor=INPUT,
                               activebackground=row_bg, activeforeground=TEXT,
                               font=("Arial", 9)).pack(side="left", padx=4)

            tk.Button(ctrl, text="Apply",
                      command=lambda uid=user_id, un=username, v=var, lbl=role_lbl: _set_role(uid, un, v, lbl),
                      bg=ACCENT, fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=8, pady=2, cursor="hand2").pack(side="left", padx=(8, 0))

            is_self = (user_id == self.current_user_id)
            tk.Button(row_f, text="Delete",
                      command=lambda uid=user_id, un=username, rf=row_f, dv=divider:
                          _delete_user(uid, un, rf, dv),
                      bg=BORDER if is_self else RED,
                      fg=DIM    if is_self else "white",
                      font=("Arial", 9, "bold"), relief="flat",
                      padx=8, pady=2, cursor="hand2",
                      state="disabled" if is_self else "normal"
                      ).grid(row=0, column=3, sticky="ew", padx=6, pady=6)

        if not users:
            self._lbl(inner, "No users registered.",
                      fg=DIM, bg=CARD, font=("Arial", 10)).pack(padx=12, pady=20)


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app  = App(root)
    root.mainloop()
