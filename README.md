# College Football National Power Rankings

A Python desktop app that ranks college football teams using the current season's game results.

## Features

- Downloads completed 2026 games from ESPN's public scoreboard feed.
- Includes FBS, FCS, and ESPN's combined Division II/III group.
- Calculates an Elo-style power rating.
- Shows national rankings, division/tier filters, records, and team search.
- Refreshes when you click **Refresh 2026 results**.

## Ranking philosophy

This is a **power ranking**, not a standings table.

- A win or loss is the only game-result input.
- **Winning margin is ignored completely.** A 70-point win and a one-point win receive the same result.
- Opponent strength matters through the opponent's rating.
- Home-field advantage is a small fixed adjustment.
- Games are processed chronologically.
- Elo update constant: K = 32.

## Experimental starting ratings

| Tier | Starting rating |
|---|---:|
| FBS Power Conference (ACC, Big 12, Big Ten, SEC) | 1800 |
| Other FBS | 1600 |
| FCS | 1300 |
| Division II/III | 900 |

These are explicit starting assumptions, not poll rankings. Results can move teams above or below teams that began in a higher tier. We should test and tune these assumptions rather than treat them as final.

**Data limitation:** ESPN's scoreboard feed groups Division II and Division III together in this version, so they are displayed as one category.

## Run the app

1. Install Python 3.
2. Download `main.py`.
3. Open it in Thonny.
4. Press Run.
5. Click **Refresh 2026 results**.

Only Python's standard library is used. No API key or paid service is required.

## Data source

ESPN public scoreboard endpoint:
`https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard`

This is not an official guaranteed-stability API. If ESPN changes its feed, the downloader may need an update.
