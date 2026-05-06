import argparse
import math
from pathlib import Path


def read_snp(path):
    nums = []
    rows = []
    nports = None
    for line in Path(path).read_text(errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("!"):
            continue
        if s.startswith("#"):
            continue
        if "!" in s:
            s = s.split("!", 1)[0].strip()
        if not s:
            continue
        nums.extend(float(x) for x in s.split())
        if nports is None:
            suffix = Path(path).suffix.lower()
            nports = int(suffix[2:-1]) if suffix.startswith(".s") and suffix.endswith("p") else 3
        width = 1 + 2 * nports * nports
        while len(nums) >= width:
            rec = nums[:width]
            nums = nums[width:]
            mags = [rec[i] for i in range(1, width, 2)]
            rows.append((rec[0], mags))
    return rows


def mag_db(rows, idx):
    return [(f, 20 * math.log10(max(mags[idx], 1e-300))) for f, mags in rows]


def write_svg(series, out_path, title):
    width, height = 1200, 760
    left, right, top, bottom = 90, 35, 70, 85
    plot_w = width - left - right
    plot_h = height - top - bottom
    xs = [x for values, _color, _name in series for x, _y in values]
    ys = [y for values, _color, _name in series for _x, y in values]
    x0, x1 = min(xs), max(xs)
    y0, y1 = -50, 5

    def px(x):
        return left + (x - x0) / (x1 - x0) * plot_w

    def py(y):
        return top + (y1 - y) / (y1 - y0) * plot_h

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="38" font-family="Segoe UI, Arial" font-size="26" fill="#111">{title}</text>',
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fbfbfb" stroke="#222" stroke-width="1"/>',
    ]
    for gy in range(math.ceil(y0 / 10) * 10, math.floor(y1 / 10) * 10 + 1, 10):
        y = py(gy)
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" stroke="#ddd"/>')
        lines.append(f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" font-family="Segoe UI, Arial" font-size="14" fill="#555">{gy}</text>')
    for gx in range(math.ceil(x0 / 5) * 5, math.floor(x1 / 5) * 5 + 1, 5):
        x = px(gx)
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_h}" stroke="#eee"/>')
        lines.append(f'<text x="{x:.2f}" y="{top + plot_h + 25}" text-anchor="middle" font-family="Segoe UI, Arial" font-size="14" fill="#555">{gx}</text>')
    lines.append(f'<text x="{left + plot_w / 2}" y="{height - 25}" text-anchor="middle" font-family="Segoe UI, Arial" font-size="18">Frequency (GHz)</text>')
    lines.append(f'<text x="24" y="{top + plot_h / 2}" transform="rotate(-90 24 {top + plot_h / 2})" text-anchor="middle" font-family="Segoe UI, Arial" font-size="18">Magnitude (dB)</text>')

    for values, color, name in series:
        pts = " ".join(f"{px(x):.2f},{py(max(y0, min(y1, y))):.2f}" for x, y in values)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{pts}"/>')
    lx, ly = left + plot_w - 170, top + 25
    for values, color, name in series:
        lines.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 35}" y2="{ly}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<text x="{lx + 45}" y="{ly + 5}" font-family="Segoe UI, Arial" font-size="16" fill="#111">{name}</text>')
        ly += 24
    lines.append("</svg>")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snp")
    parser.add_argument("out")
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    rows = read_snp(args.snp)
    if not rows:
        raise SystemExit("no data")
    # 3-port Touchstone order: S11,S21,S31,S12,S22,S32,S13,S23,S33
    series = [
        (mag_db(rows, 0), "#333333", "S11"),
        (mag_db(rows, 1), "#d62728", "S21"),
        (mag_db(rows, 2), "#1f77b4", "S31"),
    ]
    write_svg(series, args.out, args.title or Path(args.snp).stem)


if __name__ == "__main__":
    main()
