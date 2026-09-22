"""
Script to generate minimalist Hedgehog & Book Pages logo and favicons for HedgeDoc.
Complete Redesign according to exact specifications:
- Exactly 13 edges/rays converging at 1 single point at the bottom-left.
- Angles between all edges are divided completely evenly (equal angular spacing).
- Sector 0 forms the sleek, refined hedgehog head (no awkward extra corners, no bulky thickness).
- All 13 edges are rendered in black with clean, delicate 3.6px strokes and rounded linecaps.
- 100% mathematical precision and seamless integration.
"""

from pathlib import Path
import math
from PIL import Image, ImageDraw

def create_svg(size=512, color="#18181B"):
    # Single convergence point at the bottom-left
    ox = 185
    oy = 345
    r_outer = 210
    stroke_w = 3.6
    
    num_edges = 13
    start_ang = 62.0
    end_ang = 0.0
    delta_ang = (start_ang - end_ang) / (num_edges - 1)
    
    # Calculate all 13 outer points
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
    
    # Sleek hedgehog head formed by Sector 0 (between Edge 0 and Edge 1)
    p0x, p0y = pts[0]
    p1x, p1y = pts[1]
    svg.append(f'  <!-- Refined Hedgehog Head: Sector 0 -->')
    svg.append(f'  <polygon points="{ox},{oy} {p0x:.1f},{p0y:.1f} {p1x:.1f},{p1y:.1f}" fill="{color}" />')
    
    # All 13 evenly spaced black edges radiating from the bottom-left point
    svg.append(f'  <!-- 13 Black Edges Converging at Bottom-Left ({ox}, {oy}) -->')
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
    
    pts = []
    for i in range(num_edges):
        ang = start_ang - i * delta_ang
        rad = math.radians(ang)
        frac = i / (num_edges - 1)
        curr_r = r_outer * (1.0 + 0.02 * math.sin(frac * math.pi))
        x2 = ox + curr_r * math.cos(rad)
        y2 = oy - curr_r * math.sin(rad)
        pts.append((x2, y2))
        
    # 1. Fill Sector 0 as the sleek hedgehog head
    draw.polygon([(ox, oy), pts[0], pts[1]], fill=color)
    
    # 2. Draw all 13 black edges radiating from (ox, oy)
    for i in range(num_edges):
        x2, y2 = pts[i]
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
