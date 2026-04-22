#!/usr/bin/env python3
"""
Fetches real METR time-horizon data and generates the SVG chart snippet
for the presentation. Prints the complete HTML div to stdout.
"""
import urllib.request, re, math

# ── Fetch data ────────────────────────────────────────────────────────────────
url = 'https://metr.org/assets/benchmark_results_1_1.yaml'
raw = urllib.request.urlopen(url).read().decode()

all_models = []
blocks = re.split(r'\n  (?=\w[\w_]+:\n    benchmark_name:)', raw)
for block in blocks:
    key_m  = re.match(r'(\w[\w_]+):', block)
    date_m = re.search(r'release_date: (\d{4}-\d{2}-\d{2})', block)
    p50_m  = re.search(
        r'p50_horizon_length:\n\s+ci_high:.*?\n\s+ci_low:.*?\n\s+estimate: ([\d.]+)',
        block)
    if key_m and date_m and p50_m:
        all_models.append((date_m.group(1), float(p50_m.group(1)), key_m.group(1)))

all_models.sort()

# ── Which models to show, and their display labels ────────────────────────────
SELECTED = {
    'gpt2':                               'GPT-2',
    'gpt_3_5_turbo_instruct':             'GPT-3.5',
    'gpt_4':                              'GPT-4',
    'gpt_4o_inspect':                     'GPT-4o',
    'claude_3_5_sonnet_20241022_inspect': 'Claude 3.5S',
    'o1_inspect':                         'o1',
    'claude_3_7_sonnet_inspect':          'Claude 3.7',
    'o3_inspect':                         'o3',
    'claude_opus_4_5_inspect':            'Claude Opus 4.5',
    'claude_opus_4_6_inspect':            'Claude Opus 4.6',
}

points = [(d, p, SELECTED[k]) for d, p, k in all_models if k in SELECTED]

# ── SVG layout ────────────────────────────────────────────────────────────────
# Plot area
PX_LEFT, PX_RIGHT = 80, 740
PY_TOP,  PY_BOT   = 10, 270

# X axis: year range
YEAR_MIN, YEAR_MAX = 2019.0, 2027.0

# Y axis: log scale in minutes.  Tick labels we want to show:
Y_TICKS = [
    (0.05,  '3 sec'),   # so GPT-2 fits
    (1,     '1 min'),
    (10,    '10 min'),
    (60,    '1 hr'),
    (600,   '10 hr'),
    (6000,  '100 hr'),
    (10080, '1 week'),
]
LOG_MIN = math.log10(Y_TICKS[0][0])
LOG_MAX = math.log10(Y_TICKS[-1][0])

def date_to_x(datestr):
    y, m, d = map(int, datestr.split('-'))
    frac = y + (m - 1) / 12 + (d - 1) / 365.0
    return PX_LEFT + (frac - YEAR_MIN) / (YEAR_MAX - YEAR_MIN) * (PX_RIGHT - PX_LEFT)

def minutes_to_y(minutes):
    lv = math.log10(max(minutes, Y_TICKS[0][0]))
    frac = (lv - LOG_MIN) / (LOG_MAX - LOG_MIN)
    return PY_BOT - frac * (PY_BOT - PY_TOP)

# Era boundary lines (in minutes) — must match slide text
ERA_BOUNDARIES_MIN = [10, 240]  # below 10 min = Autocomplete, 10-240 min = Supervised, >240 min = Autonomous

# Colors per era — match slide accent colors exactly
def dot_color(minutes):
    if minutes < ERA_BOUNDARIES_MIN[0]:
        return '#8b949e'   # gray  — Autocomplete
    elif minutes < ERA_BOUNDARIES_MIN[1]:
        return '#58a6ff'   # blue  — Supervised
    else:
        return '#7ee787'   # green — Autonomous

# ── Year x-positions for axis labels ─────────────────────────────────────────
YEAR_LABELS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
year_x = {yr: date_to_x(f'{yr}-07-01') for yr in YEAR_LABELS}

# ── Per-label offsets to avoid crowding ──────────────────────────────────────
# (dx relative to dot right edge, dy relative to dot center)
LABEL_OFFSETS = {
    'GPT-2':            (4,   4),
    'GPT-3.5':          (4,   4),
    'GPT-4':            (4,   4),
    'GPT-4o':           (4,   4),
    'Claude 3.5S':      (4,  14),   # push down — o1 label is just above
    'o1':               (4,  -6),   # push up
    'Claude 3.7':       (4,  14),   # push down — o3 label is just above
    'o3':               (4,  -6),   # push up
    'Claude Opus 4.5':  (4,  14),   # push down — label below dot, 4.6 label is above
    'Claude Opus 4.6':  (4,  -6),   # push up
}

# ── Compute all coordinates ───────────────────────────────────────────────────
dot_data = []
for datestr, p50_min, label in points:
    cx = date_to_x(datestr)
    cy = minutes_to_y(p50_min)
    col = dot_color(p50_min)
    r = 5 if p50_min < 10 else 6
    dot_data.append((cx, cy, r, col, label, datestr, p50_min))

era_y = [minutes_to_y(m) for m in ERA_BOUNDARIES_MIN]
tick_y = [(minutes_to_y(m), lbl) for m, lbl in Y_TICKS]

# ── Print debug info ──────────────────────────────────────────────────────────
print("=== Debug: dot positions ===")
for cx, cy, r, col, label, date, p50 in dot_data:
    print(f"  {label:20s}  date={date}  p50={p50:8.2f}min  cx={cx:.0f}  cy={cy:.0f}  col={col}")

print("\n=== Era boundary y-values ===")
for m, y in zip(ERA_BOUNDARIES_MIN, era_y):
    print(f"  {m} min  →  y={y:.1f}")

print("\n=== Y tick positions ===")
for y, lbl in tick_y:
    print(f"  y={y:.1f}  label={lbl}")

# ── Build SVG ─────────────────────────────────────────────────────────────────
# Right-side era annotations start at x=744
ERA_X = 744
ERA_LABEL_X = 754
# Era 1: Autocomplete  (below first boundary)
era1_y_bot = PY_BOT
era1_y_top = era_y[0]
# Era 2: Supervised    (between boundaries)
era2_y_bot = era_y[0]
era2_y_top = era_y[1]
# Era 3: Autonomous    (above second boundary)
era3_y_bot = era_y[1]
era3_y_top = minutes_to_y(dot_data[-1][6])  # top of highest dot

def bracket(x, y_top, y_bot, color):
    return (
        f'<line x1="{x}" y1="{y_top:.0f}" x2="{x}" y2="{y_bot:.0f}" stroke="{color}" stroke-width="1.2"/>'
        f'<line x1="{x}" y1="{y_top:.0f}" x2="{x+5}" y2="{y_top:.0f}" stroke="{color}" stroke-width="1.2"/>'
        f'<line x1="{x}" y1="{y_bot:.0f}" x2="{x+5}" y2="{y_bot:.0f}" stroke="{color}" stroke-width="1.2"/>'
    )

svg_lines = []

# Background rect
svg_lines.append(f'<rect x="{PX_LEFT}" y="{PY_TOP}" width="{PX_RIGHT-PX_LEFT}" height="{PY_BOT-PY_TOP}" rx="4" fill="#161b22" stroke="#30363d"/>')

# Horizontal grid lines at each tick
for ty, _ in tick_y:
    svg_lines.append(f'<line x1="{PX_LEFT}" y1="{ty:.0f}" x2="{PX_RIGHT}" y2="{ty:.0f}" stroke="#30363d" stroke-dasharray="3,4"/>')

# Y axis labels
for ty, lbl in tick_y:
    svg_lines.append(f'<text x="{PX_LEFT-4}" y="{ty+4:.0f}" fill="#8b949e" font-size="13" text-anchor="end" font-family="Inter,sans-serif">{lbl}</text>')

# X axis labels (only years with data or notable years)
for yr in YEAR_LABELS:
    tx = year_x[yr]
    if PX_LEFT <= tx <= PX_RIGHT:
        svg_lines.append(f'<text x="{tx:.0f}" y="{PY_BOT+18}" fill="#8b949e" font-size="13" text-anchor="middle" font-family="Inter,sans-serif">{yr}</text>')

# Dots and labels
for cx, cy, r, col, label, date, p50 in dot_data:
    svg_lines.append(f'<!-- {label} {date} {p50:.1f}min -->')
    svg_lines.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="{col}"/>')
    # Use per-label offset if defined, else default to right of dot
    dx, dy = LABEL_OFFSETS.get(label, (r + 4, 4))
    lx = cx + r + dx if dx >= 0 else cx + dx
    ly = cy + dy
    svg_lines.append(f'<text x="{lx:.0f}" y="{ly:.0f}" fill="{col}" font-size="13" font-family="Inter,sans-serif" font-weight="600">{label}</text>')

# Era boundary dashed lines extending to right annotations
for ey in era_y:
    svg_lines.append(f'<line x1="{PX_RIGHT}" y1="{ey:.0f}" x2="898" y2="{ey:.0f}" stroke="#30363d" stroke-width="1" stroke-dasharray="3,3"/>')

# Era brackets and labels
# Era 1: Autocomplete (gray)
mid1 = (era1_y_top + era1_y_bot) / 2
svg_lines.append(bracket(ERA_X, era1_y_top, era1_y_bot, '#8b949e'))
svg_lines.append(f'<text x="{ERA_LABEL_X}" y="{mid1-8:.0f}" fill="#8b949e" font-size="13" font-family="Inter,sans-serif" font-weight="600">Autocomplete</text>')
svg_lines.append(f'<text x="{ERA_LABEL_X}" y="{mid1+8:.0f}" fill="#8b949e" font-size="12" font-family="Inter,sans-serif">write a line at a time</text>')

# Era 2: Supervised (blue)
mid2 = (era2_y_top + era2_y_bot) / 2
svg_lines.append(bracket(ERA_X, era2_y_top, era2_y_bot, '#58a6ff'))
svg_lines.append(f'<text x="{ERA_LABEL_X}" y="{mid2-12:.0f}" fill="#58a6ff" font-size="13" font-family="Inter,sans-serif" font-weight="600">Supervised agent</text>')
svg_lines.append(f'<text x="{ERA_LABEL_X}" y="{mid2+4:.0f}" fill="#58a6ff" font-size="12" font-family="Inter,sans-serif">tell it what to do,</text>')
svg_lines.append(f'<text x="{ERA_LABEL_X}" y="{mid2+19:.0f}" fill="#58a6ff" font-size="12" font-family="Inter,sans-serif">watch it work</text>')

# Era 3: Autonomous (green)
mid3 = (era3_y_top + era3_y_bot) / 2
svg_lines.append(bracket(ERA_X, era3_y_top, era3_y_bot, '#7ee787'))
svg_lines.append(f'<text x="{ERA_LABEL_X}" y="{mid3-12:.0f}" fill="#7ee787" font-size="13" font-family="Inter,sans-serif" font-weight="600">Autonomous agent</text>')
svg_lines.append(f'<text x="{ERA_LABEL_X}" y="{mid3+4:.0f}" fill="#7ee787" font-size="12" font-family="Inter,sans-serif">draft a plan, hand off,</text>')
svg_lines.append(f'<text x="{ERA_LABEL_X}" y="{mid3+19:.0f}" fill="#7ee787" font-size="12" font-family="Inter,sans-serif">come back to a PR</text>')

# Source note
svg_lines.append(f'<text x="{PX_RIGHT}" y="{PY_BOT+32}" fill="#8b949e" font-size="10" text-anchor="end" font-family="Inter,sans-serif">Source: METR (metr.org) — 50% task-completion time horizon</text>')

svg_inner = '\n      '.join(svg_lines)

output = f'''  <div style="width:100%;max-width:860px;">
    <svg viewBox="0 0 900 320" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">
      {svg_inner}
    </svg>
  </div>'''

print("\n=== OUTPUT HTML ===")
print(output)
