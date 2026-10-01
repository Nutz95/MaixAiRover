"""Generate align curve SVG assets from ship ball_follow knobs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"

H_DZ = 0.04
SPIN_FULL = 0.22
SPIN_CURVE = 0.55
Y_TOL = 0.03
Y_TARGET = 0.50
APP_CURVE = 0.40
RET_CURVE = 0.40
APP_FULL = 0.50
RET_FULL = 0.40
MIN_DIST_ERR = 0.02
TOO_CLOSE_Y = 0.90


def spin_signed(x: float) -> float:
  err = abs(x - 0.5)
  if err <= H_DZ:
    return 0.0
  mag = min(1.0, (err / SPIN_FULL) ** SPIN_CURVE)
  return mag if x >= 0.5 else -mag


def y_signed(y: float) -> float:
  """+1 approach (ball high), -1 retreat (ball low)."""
  enter_lo = Y_TARGET - Y_TOL
  enter_hi = Y_TARGET + Y_TOL
  if enter_lo <= y <= enter_hi:
    return 0.0
  if y < enter_lo:
    err = max(MIN_DIST_ERR, Y_TARGET - y)
    return min(1.0, (err / APP_FULL) ** APP_CURVE)
  err = max(MIN_DIST_ERR, y - Y_TARGET)
  return -min(1.0, (err / RET_FULL) ** RET_CURVE)


def _path(points: list[tuple[float, float]]) -> str:
  return "M " + " L ".join(f"{px:.1f},{py:.1f}" for px, py in points)


def write_y_cross_section() -> None:
  w, h = 544, 200
  mid = h / 2
  pts: list[tuple[float, float]] = []
  for i in range(41):
    y = i / 40
    c = y_signed(y)
    pts.append((y * w, mid - c * mid))
  enter_lo = (Y_TARGET - Y_TOL) * w
  enter_hi = (Y_TARGET + Y_TOL) * w
  svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 300" role="img" aria-label="Forward retreat authority vs ball Y">
  <rect width="640" height="300" fill="#0f1419"/>
  <text x="16" y="24" fill="#9aa4af" font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">Y authority (approach up, retreat down) - curve 0.40 / tol +/-0.03</text>
  <g transform="translate(48,40)">
    <rect width="{w}" height="{h}" fill="#161c22" stroke="#2a3340"/>
    <line x1="0" y1="{mid}" x2="{w}" y2="{mid}" stroke="#2a3340"/>
    <line x1="0" y1="0" x2="{w}" y2="0" stroke="#2a3340"/>
    <line x1="0" y1="{h}" x2="{w}" y2="{h}" stroke="#2a3340"/>
    <rect x="{enter_lo:.2f}" y="0" width="{enter_hi - enter_lo:.2f}" height="{h}" fill="#3d4450" opacity="0.35"/>
    <line x1="{Y_TARGET * w}" y1="0" x2="{Y_TARGET * w}" y2="{h}" stroke="#c5ced6" stroke-dasharray="6 4"/>
    <path fill="none" stroke="#5ec8a0" stroke-width="2.5" d="{_path(pts)}"/>
    <text x="-8" y="8" fill="#6b7680" font-size="11" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">+app</text>
    <text x="-8" y="{mid + 4}" fill="#6b7680" font-size="11" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">0</text>
    <text x="-8" y="{h}" fill="#6b7680" font-size="11" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">-ret</text>
    <text x="16" y="{h + 18}" fill="#6b7680" font-size="11" font-family="ui-sans-serif,system-ui,sans-serif">y=0 top</text>
    <text x="{Y_TARGET * w}" y="{h + 18}" fill="#c5ced6" font-size="11" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">y=0.5</text>
    <text x="{w - 16}" y="{h + 18}" fill="#6b7680" font-size="11" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">y=1 bottom</text>
  </g>
  <g font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">
    <line x1="48" y1="278" x2="78" y2="278" stroke="#5ec8a0" stroke-width="2.5"/>
    <text x="86" y="282" fill="#c5ced6">approach_curve = retreat_curve = 0.40</text>
  </g>
</svg>
"""
  (IMG / "align_y_cross_section.svg").write_text(svg, encoding="utf-8")


def _blend_cell(spin_mag: float, y_cmd: float) -> str:
  """RGB from spin (orange) + approach (green) + retreat (coral)."""
  # base dark
  r, g, b = 22, 28, 34
  if y_cmd > 0:
    # approach green
    r = int(r + (94 - r) * y_cmd)
    g = int(g + (200 - g) * y_cmd)
    b = int(b + (160 - b) * y_cmd)
  elif y_cmd < 0:
    t = -y_cmd
    r = int(r + (220 - r) * t)
    g = int(g + (96 - g) * t)
    b = int(b + (80 - b) * t)
  # overlay spin as orange lift
  if spin_mag > 0:
    r = min(255, int(r + (240 - r) * spin_mag * 0.55))
    g = min(255, int(g + (160 - g) * spin_mag * 0.35))
    b = min(255, int(b + (80 - b) * spin_mag * 0.15))
  return f"#{r:02x}{g:02x}{b:02x}"


def write_xy_combined() -> None:
  cols, rows = 16, 12
  cell_w, cell_h = 34, 23
  plot_w, plot_h = cols * cell_w, rows * cell_h
  cells = []
  arrows = []
  for j in range(rows):
    y = (j + 0.5) / rows
    for i in range(cols):
      x = (i + 0.5) / cols
      sx = spin_signed(x)
      sy = y_signed(y)
      fill = _blend_cell(abs(sx), sy)
      px = i * cell_w
      py = j * cell_h
      cells.append(
        f'<rect x="{px}" y="{py}" width="{cell_w}" height="{cell_h}" fill="{fill}"/>'
      )
      # arrow in command space: +spin right, +approach up on page (negate image-y convention for approach)
      cx = px + cell_w / 2
      cy = py + cell_h / 2
      # screen: dx = spin, dy = -approach (so approach points up)
      dx = sx * 12
      dy = -sy * 10
      if abs(dx) < 0.4 and abs(dy) < 0.4:
        arrows.append(
          f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.6" fill="#6b7680"/>'
        )
      else:
        arrows.append(
          f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx + dx:.1f}" y2="{cy + dy:.1f}" '
          f'stroke="#e8eef4" stroke-width="1.4" stroke-linecap="round"/>'
        )
        # simple arrow head tip
        arrows.append(
          f'<circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="1.4" fill="#e8eef4"/>'
        )

  dead_x0 = (0.5 - H_DZ) * plot_w
  dead_w = (2 * H_DZ) * plot_w
  band_y0 = (Y_TARGET - Y_TOL) * plot_h
  band_h = (2 * Y_TOL) * plot_h
  svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 420" role="img" aria-label="Combined XY ball-follow authority heatmap with command arrows">
  <rect width="680" height="420" fill="#0f1419"/>
  <text x="16" y="24" fill="#9aa4af" font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">Combined FOV: color = Y drive, orange lift = |spin|, arrows = command (spin x, approach up / retreat down)</text>
  <g transform="translate(48,40)">
    {"".join(cells)}
    {"".join(arrows)}
    <rect x="0" y="0" width="{plot_w}" height="{plot_h}" fill="none" stroke="#2a3340"/>
    <rect x="{dead_x0:.2f}" y="0" width="{dead_w:.2f}" height="{plot_h}" fill="none" stroke="#c5ced6" stroke-width="1.2"/>
    <rect x="0" y="{band_y0:.2f}" width="{plot_w}" height="{band_h:.2f}" fill="none" stroke="#c5ced6" stroke-width="1.2"/>
    <line x1="{plot_w / 2}" y1="0" x2="{plot_w / 2}" y2="{plot_h}" stroke="#e8eef4" stroke-width="1.2" stroke-dasharray="6 4"/>
    <line x1="0" y1="{plot_h / 2}" x2="{plot_w}" y2="{plot_h / 2}" stroke="#e8eef4" stroke-width="1.2" stroke-dasharray="6 4"/>
    <text x="{plot_w / 2}" y="{plot_h + 18}" fill="#c5ced6" font-size="11" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">x center</text>
    <text x="8" y="{plot_h / 2 - 6}" fill="#c5ced6" font-size="11" font-family="ui-sans-serif,system-ui,sans-serif">y mid</text>
    <text x="8" y="14" fill="#6b7680" font-size="11" font-family="ui-sans-serif,system-ui,sans-serif">top</text>
    <text x="8" y="{plot_h - 6}" fill="#6b7680" font-size="11" font-family="ui-sans-serif,system-ui,sans-serif">bottom</text>
  </g>
  <g font-family="ui-sans-serif,system-ui,sans-serif" font-size="12" transform="translate(48,370)">
    <rect x="0" y="0" width="14" height="14" fill="#5ec8a0"/>
    <text x="20" y="12" fill="#c5ced6">approach</text>
    <rect x="110" y="0" width="14" height="14" fill="#dc6050"/>
    <text x="130" y="12" fill="#c5ced6">retreat</text>
    <rect x="210" y="0" width="14" height="14" fill="#f0a050"/>
    <text x="230" y="12" fill="#c5ced6">|spin| lift</text>
    <circle cx="360" cy="7" r="2" fill="#6b7680"/>
    <text x="370" y="12" fill="#c5ced6">hold (in band)</text>
  </g>
</svg>
"""
  (IMG / "align_xy_combined.svg").write_text(svg, encoding="utf-8")


def main() -> None:
  IMG.mkdir(parents=True, exist_ok=True)
  write_y_cross_section()
  write_xy_combined()
  print("wrote", IMG / "align_y_cross_section.svg")
  print("wrote", IMG / "align_xy_combined.svg")


if __name__ == "__main__":
  main()
