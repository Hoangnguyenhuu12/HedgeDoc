"""
Script to generate minimalist Hedgehog & Book Pages logo and favicons for HedgeDoc.
Pure Line-Art Design:
- Exactly 13 clean, delicate black edges converging at 1 single point at the bottom-left.
- Angles between all 13 edges are divided completely evenly.
- No bulky filled shapes: pure, refined, minimalist linear elegance.
- All edges have uniform 3.6px stroke width and rounded linecaps.
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
    svg.append(f'  <!-- 13 Pure Black Edges Converging at Bottom-Left ({ox}, {oy}) -->')
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
    
    # 3. Render Favicon PNG (64x64)
    fav_64 = render_png(size=64)
    fav_64.save(assets_dir / "favicon.png", format="PNG")
    fav_64.save(static_dir / "favicon.png", format="PNG")
    print("Saved favicon.png")
    
    # 4. Save ICO
    fav_64.save(assets_dir / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    fav_64.save(static_dir / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("Saved favicon.ico")
