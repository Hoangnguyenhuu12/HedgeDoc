"""
Script to generate minimalist Hedgehog & Book Pages logo and favicons for HedgeDoc.
Pure Line-Art Design:
- Exactly 13 clean, delicate edges converging at 1 single point at the bottom-left.
- Angles between all 13 edges are divided completely evenly.
- Minimalist linear elegance.
- High-contrast, centered favicon optimized for browser tabs in dark and light modes.
"""

from pathlib import Path
import math
from PIL import Image, ImageDraw


def create_svg(size=512, color="#18181B"):
    ox = 185
    oy = 345
    r_outer = 210
    stroke_w = 3.6
    
    num_edges = 13
    start_ang = 62.0
    end_ang = 0.0
    delta_ang = (start_ang - end_ang) / (num_edges - 1)
    
    pts = []
    for i in range(num_edges):
        ang = start_ang - i * delta_ang
        rad = math.radians(ang)
        frac = i / (num_edges - 1)
        curr_r = r_outer * (1.0 + 0.02 * math.sin(frac * math.pi))
        x2 = ox + curr_r * math.cos(rad)
        y2 = oy - curr_r * math.sin(rad)
        pts.append((x2, y2))
        
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">')
    svg.append('  <!-- Background: transparent -->')
    svg.append(f'  <!-- 13 Edges Converging at Bottom-Left ({ox}, {oy}) -->')
    for i in range(num_edges):
        x2, y2 = pts[i]
        svg.append(f'  <line x1="{ox}" y1="{oy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{stroke_w}" stroke-linecap="round" />')
        
    svg.append('</svg>')
    return '\n'.join(svg)


def render_png(size=512, color=(24, 24, 27, 255), bg_color=(255, 255, 255, 0)):
    scale = 4
    img_size = size * scale
    img = Image.new("RGBA", (img_size, img_size), bg_color)
    draw = ImageDraw.Draw(img)
    
    ox = 185 * scale
    oy = 345 * scale
    r_outer = 210 * scale
    stroke_w = int(3.6 * scale)
    r_cap = stroke_w / 2.0
    
    num_edges = 13
    start_ang = 62.0
    end_ang = 0.0
    delta_ang = (start_ang - end_ang) / (num_edges - 1)
    
    for i in range(num_edges):
        ang = start_ang - i * delta_ang
        rad = math.radians(ang)
        frac = i / (num_edges - 1)
        curr_r = r_outer * (1.0 + 0.02 * math.sin(frac * math.pi))
        x2 = ox + curr_r * math.cos(rad)
        y2 = oy - curr_r * math.sin(rad)
        draw.line([(ox, oy), (x2, y2)], fill=color, width=stroke_w)
        draw.ellipse([x2 - r_cap, y2 - r_cap, x2 + r_cap, y2 + r_cap], fill=color)
        
    draw.ellipse([ox - r_cap, oy - r_cap, ox + r_cap, oy + r_cap], fill=color)
    
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


def render_favicon(size=128):
    """
    Render a high-contrast, beautifully centered favicon for browser tabs.
    Features:
    - Dark obsidian rounded squircle background (#09090B).
    - Crisp white/light-zinc (#FAFAFA) spines.
    - Centered bounding box with balanced padding.
    - High stroke clarity at small favicon resolutions.
    """
    scale = 4
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. Dark squircle background
    radius = int(canvas_size * 0.22)
    # Draw rounded rectangle for modern app icon look
    draw.rounded_rectangle(
        [(0, 0), (canvas_size - 1, canvas_size - 1)],
        radius=radius,
        fill=(9, 9, 11, 255),  # Obsidian dark background #09090B
        outline=(39, 39, 42, 255),  # Subtle zinc border #27272A
        width=int(2 * scale)
    )
    
    # 2. Compute geometry for centered hedgehog fan
    # Original fan spans: x: 0 -> r_outer, y: 0 -> r_outer * sin(62 deg)
    num_edges = 13
    start_ang = 62.0
    end_ang = 0.0
    delta_ang = (start_ang - end_ang) / (num_edges - 1)
    
    # Compute bounding box in normalized coordinates (origin at 0,0)
    pts_norm = []
    max_x = 0.0
    min_y = 0.0  # y goes upward (negative in canvas coords)
    
    for i in range(num_edges):
        ang = start_ang - i * delta_ang
        rad = math.radians(ang)
        frac = i / (num_edges - 1)
        r = 1.0 * (1.0 + 0.02 * math.sin(frac * math.pi))
        x = r * math.cos(rad)
        y = -r * math.sin(rad)
        pts_norm.append((x, y))
        if x > max_x:
            max_x = x
        if y < min_y:
            min_y = y
            
    fan_w = max_x  # ~ 1.0
    fan_h = -min_y  # ~ 0.88
    
    # Fit into canvas with padding
    padding = canvas_size * 0.20
    avail_w = canvas_size - 2 * padding
    avail_h = canvas_size - 2 * padding
    
    fit_scale = min(avail_w / fan_w, avail_h / fan_h)
    
    # Target center
    target_cx = canvas_size / 2.0
    target_cy = canvas_size / 2.0
    
    # Bounding box center relative to origin:
    box_cx = (fan_w / 2.0) * fit_scale
    box_cy = (-fan_h / 2.0) * fit_scale  # negative because min_y is negative
    
    # Origin placement
    ox = target_cx - box_cx - (canvas_size * 0.03)  # subtle optical balance
    oy = target_cy - box_cy
    
    stroke_w = max(int(2.8 * scale), 3)
    r_cap = stroke_w / 2.0
    stroke_color = (250, 250, 250, 255)  # Clean crisp white #FAFAFA
    
    for x_norm, y_norm in pts_norm:
        x2 = ox + x_norm * fit_scale
        y2 = oy + y_norm * fit_scale
        draw.line([(ox, oy), (x2, y2)], fill=stroke_color, width=stroke_w)
        draw.ellipse([x2 - r_cap, y2 - r_cap, x2 + r_cap, y2 + r_cap], fill=stroke_color)
        
    draw.ellipse([ox - r_cap, oy - r_cap, ox + r_cap, oy + r_cap], fill=stroke_color)
    
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


if __name__ == "__main__":
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # 1. Save SVG
    svg_content = create_svg()
    (assets_dir / "logo.svg").write_text(svg_content, encoding="utf-8")
    (static_dir / "logo.svg").write_text(svg_content, encoding="utf-8")
    print("Saved logo.svg")
    
    # 2. Render high-res PNG (512x512)
    logo_png = render_png(size=512)
    logo_png.save(assets_dir / "logo.png", format="PNG")
    logo_png.save(static_dir / "logo.png", format="PNG")
    print("Saved logo.png")
    
    # 3. Render Favicon PNG (128x128 and 64x64)
    fav_128 = render_favicon(size=128)
    fav_128.save(assets_dir / "favicon.png", format="PNG")
    fav_128.save(static_dir / "favicon.png", format="PNG")
    print("Saved favicon.png")
    
    # 4. Save ICO
    fav_64 = render_favicon(size=64)
    fav_64.save(assets_dir / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    fav_64.save(static_dir / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("Saved favicon.ico")
