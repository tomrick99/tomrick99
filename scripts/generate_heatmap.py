#!/usr/bin/env python3
"""Generate a safe, self-contained animated SVG for the GitHub profile README."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "contributions.json"
OUTPUT_PATH = ROOT / "assets" / "contribution-flow.svg"

CELL = 10
GAP = 5
LEFT = 72
TOP = 98
COLORS = ["#242836", "#354760", "#4f75a3", "#6d78c9", "#9b7ae3"]


def longest_streak(days: list[dict]) -> int:
    longest = current = 0
    for day in days:
        if int(day.get("count", 0)) > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def build_svg(payload: dict) -> str:
    days = sorted(payload.get("contributions", []), key=lambda day: day["date"])[-371:]
    if not days:
        raise ValueError("No contribution days found")

    first_weekday = (datetime.fromisoformat(days[0]["date"]).weekday() + 1) % 7
    total = sum(int(day.get("count", 0)) for day in days)
    active = sum(1 for day in days if int(day.get("count", 0)) > 0)
    streak = longest_streak(days)

    cells = []
    month_labels = []
    seen_months = set()
    pulse_index = 0

    for index, day in enumerate(days):
        grid_index = index + first_weekday
        week, weekday = divmod(grid_index, 7)
        x = LEFT + week * (CELL + GAP)
        y = TOP + weekday * (CELL + GAP)
        level = max(0, min(4, int(day.get("level", 0))))
        date = html.escape(day["date"])
        count = int(day.get("count", 0))
        delay = min(1.7, week * 0.028 + weekday * 0.012)
        pulse = ""
        if level >= 3 and pulse_index < 6:
            pulse_delay = 2.8 + pulse_index * 0.43
            pulse = (
                f'<circle class="ripple" cx="{x + CELL / 2}" cy="{y + CELL / 2}" '
                f'r="4" style="animation-delay:{pulse_delay:.2f}s" />'
            )
            pulse_index += 1
        cells.append(
            f'<g><title>{date}: {count} contributions</title>'
            f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
            f'fill="{COLORS[level]}" style="animation-delay:{delay:.3f}s" />{pulse}</g>'
        )

        parsed = datetime.fromisoformat(day["date"])
        month_key = (parsed.year, parsed.month)
        if parsed.day <= 7 and month_key not in seen_months:
            seen_months.add(month_key)
            month_labels.append(
                f'<text x="{x}" y="{TOP - 17}" class="month">{parsed.strftime("%b")}</text>'
            )

    width = LEFT + 53 * (CELL + GAP) + 34
    year_range = f'{days[0]["date"][:4]}—{days[-1]["date"][:4]}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="250" viewBox="0 0 {width} 250" role="img" aria-labelledby="title desc">
  <title id="title">tomrick99 contribution flow</title>
  <desc id="desc">An animated heatmap of {total} GitHub contributions across {active} active days.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111521"/><stop offset="1" stop-color="#0b0e17"/></linearGradient>
    <linearGradient id="scan" x1="0" x2="1"><stop stop-color="#65dcf7" stop-opacity="0"/><stop offset=".5" stop-color="#8e7be7" stop-opacity=".22"/><stop offset="1" stop-color="#65dcf7" stop-opacity="0"/></linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="2.8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <clipPath id="panel"><rect width="{width}" height="250" rx="20"/></clipPath>
  </defs>
  <style>
    text {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    .cell {{ opacity:0; transform-box:fill-box; transform-origin:center; animation:enter .48s cubic-bezier(.2,.8,.2,1.2) forwards; }}
    .scan {{ animation:scan 3.4s cubic-bezier(.3,.7,.2,1) .15s both; }}
    .ripple {{ fill:none; stroke:#9b82e9; opacity:0; animation:ripple 3.6s ease-out infinite; }}
    .month {{ fill:#697086; font-size:9px; letter-spacing:.06em; }}
    @keyframes enter {{ 0%{{opacity:0;transform:scale(.25) translateY(4px)}} 60%{{opacity:1;transform:scale(1.18)}} 100%{{opacity:1;transform:scale(1)}} }}
    @keyframes scan {{ 0%{{transform:translateX(-190px);opacity:0}} 20%{{opacity:1}} 85%{{opacity:.8}} 100%{{transform:translateX({width + 190}px);opacity:0}} }}
    @keyframes ripple {{ 0%,48%{{r:4;opacity:0}} 55%{{opacity:.65}} 76%,100%{{r:16;opacity:0}} }}
    @media (prefers-reduced-motion:reduce) {{ .cell{{animation:none;opacity:1}} .scan,.ripple{{display:none}} }}
  </style>
  <g clip-path="url(#panel)">
    <rect width="{width}" height="250" rx="20" fill="url(#bg)"/>
    <circle cx="{width - 80}" cy="25" r="110" fill="#795cd6" opacity=".055"/>
    <text x="30" y="38" fill="#f0f2fb" font-size="17" font-weight="600">Contribution flow</text>
    <text x="30" y="59" fill="#777e94" font-size="10">@tomrick99 · {year_range}</text>
    <text x="{width - 30}" y="41" text-anchor="end" fill="#aeb4c8" font-size="11">{total} contributions · {active} active days · {streak}d streak</text>
    {''.join(month_labels)}
    <text x="31" y="{TOP + 27}" class="month">Mon</text><text x="31" y="{TOP + 57}" class="month">Wed</text><text x="31" y="{TOP + 87}" class="month">Fri</text>
    {''.join(cells)}
    <rect class="scan" x="-160" y="74" width="160" height="125" fill="url(#scan)" filter="url(#glow)"/>
    <text x="30" y="226" fill="#626a7f" font-size="9">Private activity appears as anonymous daily totals when enabled on GitHub.</text>
    <g transform="translate({width - 190},219)"><text fill="#626a7f" font-size="8">QUIET</text>
      <rect x="42" y="-7" width="8" height="8" rx="2" fill="{COLORS[0]}"/><rect x="56" y="-7" width="8" height="8" rx="2" fill="{COLORS[1]}"/><rect x="70" y="-7" width="8" height="8" rx="2" fill="{COLORS[2]}"/><rect x="84" y="-7" width="8" height="8" rx="2" fill="{COLORS[3]}"/><rect x="98" y="-7" width="8" height="8" rx="2" fill="{COLORS[4]}"/><text x="116" fill="#626a7f" font-size="8">BUSY</text>
    </g>
  </g>
  <rect x=".5" y=".5" width="{width - 1}" height="249" rx="19.5" fill="none" stroke="#c4cdff" stroke-opacity=".1"/>
</svg>'''


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_svg(payload), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
