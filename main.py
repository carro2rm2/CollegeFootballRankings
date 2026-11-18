import json
import threading
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox

SEASON = 2026
START_DATE = f"{SEASON}0820"
END_DATE = f"{SEASON}1231"
BASE_RATINGS = {
    "FBS Power Conference": 1800,
    "FBS Other": 1600,
    "FCS": 1300,
    "Division II/III": 900,
}
POWER_CONFERENCES = {"ACC", "Big 12", "Big Ten", "SEC"}
HOME_ADVANTAGE = 55
K_FACTOR = 32
API = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"


def get_json(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "CollegeFootballRankings/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_team_tier(team, group_id):
    if str(group_id) == "80":
        groups = team.get("groups") or {}
        conference = groups.get("name", "") or ""
        if conference in POWER_CONFERENCES:
            return "FBS Power Conference", conference
        return "FBS Other", conference
    if str(group_id) == "81":
        return "FCS", ""
    return "Division II/III", ""


def load_season_games(status_callback):
    all_games = {}
    # ESPN group IDs: 80=FBS, 81=FCS, 35=combined Division II/III.
    for group_id, label in [
        ("80", "FBS"), ("81", "FCS"), ("35", "Division II/III")
    ]:
        status_callback(f"Downloading {label} results...")
        params = urllib.parse.urlencode({
            "dates": f"{START_DATE}-{END_DATE}",
            "groups": group_id,
            "limit": "1000",
        })
        data = get_json(f"{API}?{params}")
        for event in data.get("events", []):
            all_games[event.get("id")] = (event, group_id)

    games = []
    teams = {}
    for event, group_id in all_games.values():
        competitions = event.get("competitions", [])
        if not competitions:
            continue
        competition = competitions[0]
        status = (competition.get("status") or {}).get("type", {})
        if not status.get("completed", False):
            continue
        competitors = competition.get("competitors", [])
        if len(competitors) != 2:
            continue

        parsed = []
        for item in competitors:
            team = item.get("team", {})
            team_id = str(team.get("id", ""))
            if not team_id:
                continue
            tier, conference = get_team_tier(team, group_id)
            name = team.get("displayName") or team.get("name") or "Unknown"
            teams[team_id] = {
                "id": team_id, "name": name, "tier": tier,
                "conference": conference, "rating": BASE_RATINGS[tier],
                "wins": 0, "losses": 0, "games": 0,
            }
            parsed.append({
                "id": team_id,
                "home": item.get("homeAway") == "home",
                "winner": item.get("winner", False),
            })
        if len(parsed) != 2:
            continue
        winner = next((x["id"] for x in parsed if x["winner"]), None)
        if winner is not None:
            games.append({
                "id": event.get("id"),
                "date": event.get("date", ""),
                "teams": parsed,
                "winner": winner,
            })

    # Chronological Elo updates. Scores and winning margin are never read.
    games.sort(key=lambda game: game["date"])
    for game in games:
        a, b = game["teams"]
        ta, tb = teams[a["id"]], teams[b["id"]]
        home_adjustment = HOME_ADVANTAGE if a["home"] else (
            -HOME_ADVANTAGE if b["home"] else 0
        )
        expected_a = 1 / (
            1 + 10 ** ((tb["rating"] - (ta["rating"] + home_adjustment)) / 400)
        )
        actual_a = 1.0 if game["winner"] == a["id"] else 0.0
        change = K_FACTOR * (actual_a - expected_a)
        ta["rating"] += change
        tb["rating"] -= change
        ta["games"] += 1
        tb["games"] += 1
        if actual_a:
            ta["wins"] += 1
            tb["losses"] += 1
        else:
            tb["wins"] += 1
            ta["losses"] += 1

    return list(teams.values()), len(games)


class RankingsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("College Football National Power Rankings")
        self.root.geometry("1050x700")
        self.root.minsize(800, 520)
        self.teams = []

        header = ttk.Frame(root, padding=12)
        header.pack(fill="x")
        ttk.Label(
            header, text="College Football Power Rankings",
            font=("Segoe UI", 19, "bold")
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=f"{SEASON} season • Win/loss results only • No margin-of-victory points"
        ).pack(anchor="w", pady=(3, 8))

        controls = ttk.Frame(root, padding=(12, 0, 12, 8))
        controls.pack(fill="x")
        ttk.Label(controls, text="Show:").pack(side="left")
        self.division = tk.StringVar(value="All teams")
        self.filter = ttk.Combobox(
            controls, textvariable=self.division, state="readonly", width=22,
            values=[
                "All teams", "FBS Power Conference", "FBS Other",
                "FCS", "Division II/III"
            ]
        )
        self.filter.pack(side="left", padx=7)
        self.filter.bind("<<ComboboxSelected>>", lambda _e: self.render())
        ttk.Label(controls, text="Find team:").pack(side="left", padx=(18, 4))
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.render())
        ttk.Entry(controls, textvariable=self.search, width=22).pack(side="left")
        self.refresh_button = ttk.Button(
            controls, text="Refresh 2026 results", command=self.refresh
        )
        self.refresh_button.pack(side="right")

        self.status = tk.StringVar(
            value="Click Refresh to download this season's completed games."
        )
        ttk.Label(root, textvariable=self.status, padding=(12, 4)).pack(fill="x")

        columns = ("rank", "team", "tier", "record", "rating", "games")
        self.table = ttk.Treeview(root, columns=columns, show="headings")
        headings = {
            "rank": ("Rank", 65), "team": ("Team", 290),
            "tier": ("Division / tier", 210), "record": ("Record", 110),
            "rating": ("Power rating", 120), "games": ("Games", 80)
        }
        for col, (label, width) in headings.items():
            self.table.heading(col, text=label)
            self.table.column(
                col, width=width,
                anchor="w" if col in ("team", "tier") else "center"
            )
        self.table.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.table.tag_configure("top", font=("Segoe UI", 10, "bold"))
        ttk.Label(
            root,
            text=("Starting ratings are explicit assumptions, not poll rankings. "
                  "ESPN groups Division II and III together in this feed."),
            padding=(12, 6), wraplength=1000
        ).pack(fill="x")

    def refresh(self):
        self.refresh_button.config(state="disabled")
        self.status.set("Connecting to ESPN and downloading completed games...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        try:
            teams, count = load_season_games(
                lambda message: self.root.after(0, self.status.set, message)
            )
            self.root.after(0, self._refresh_done, teams, count, None)
        except Exception as exc:
            self.root.after(0, self._refresh_done, None, 0, str(exc))

    def _refresh_done(self, teams, count, error):
        self.refresh_button.config(state="normal")
        if error:
            self.status.set("Could not update results.")
            messagebox.showerror(
                "Data download failed",
                "ESPN's public scoreboard feed could not be reached or parsed.\n\n"
                + error + "\n\nCheck your internet connection and try again."
            )
            return
        self.teams = sorted(teams, key=lambda team: team["rating"], reverse=True)
        self.status.set(
            f"Updated: {len(teams)} teams • {count} completed games • "
            "sorted by power rating"
        )
        self.render()

    def render(self):
        for row in self.table.get_children():
            self.table.delete(row)
        selected = self.division.get()
        search = self.search.get().strip().lower()
        filtered = [
            team for team in self.teams
            if (selected == "All teams" or team["tier"] == selected)
            and search in team["name"].lower()
        ]
        for rank, team in enumerate(filtered, 1):
            record = f'{team["wins"]}-{team["losses"]}'
            self.table.insert(
                "", "end",
                values=(
                    rank, team["name"], team["tier"], record,
                    f'{team["rating"]:.1f}', team["games"]
                ),
                tags=("top",) if rank <= 25 and selected == "All teams" else ()
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = RankingsApp(root)
    root.mainloop()
