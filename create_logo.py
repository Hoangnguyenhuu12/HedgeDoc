"""
Script to generate minimalist Hedgehog & Book Pages logo and favicons for HedgeDoc.
Architecture:
- 100% Seamless single-body geometry.
- Single continuous triangle for head and body.
- Uniform baseline matching spine stroke width (no steps, no gaps).
- Spines radiate directly from pivot (cx, cy) to outer radius in an elegant fan.
- Matching rounded stroke caps for all endpoints.
"""

from pathlib import Path
import math
from PIL import Image, ImageDraw

def create_svg(size=512, color="#18181B"):
    cx = 220
    cy = 340
    r_outer = 190
    nose_x = 115
    
    start_angle = 63.0
    end_angle = 0.0
    num_spines = 11
    stroke_w = 8.5
    
    # Peak at 48% of r_outer along the top spine
    r_peak = r_outer * 0.48
    rad_start = math.radians(start_angle)
    peak_x = cx + r_peak * math.cos(rad_start)
    peak_y = cy - r_peak * math.sin(rad_start)
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">')
    svg.append('  <!-- Background: transparent -->')
    
    # Unified head polygon with stroke for perfect baseline alignment and rounded corners
    svg.append(f'  <polygon points="{nose_x},{cy} {peak_x:.1f},{peak_y:.1f} {cx},{cy}" fill="{color}" stroke="{color}" stroke-width="{stroke_w}" stroke-linejoin="round" stroke-linecap="round" />')
    
    # Spines radiating directly from pivot (cx, cy) - ZERO GAP
    for i in range(num_spines):
        frac = i / (num_spines - 1)
        ang = start_angle - frac * (start_angle - end_angle)
        rad = math.radians(ang)
        curr_r = r_outer * (1.0 + 0.03 * math.sin(frac * math.pi))
        x2 = cx + curr_r * math.cos(rad)
        y2 = cy - curr_r * math.sin(rad)
        svg.append(f'  <line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{stroke_w}" stroke-linecap="round" />')
        
    svg.append('</svg>')
    return '\n'.join(svg)


def render_png(size=512, color=(24, 24, 27, 255), bg_color=(255, 255, 255, 0)):
    scale = 4
    img_size = size * scale
    img = Image.new("RGBA", (img_size, img_size), bg_color)
    draw = ImageDraw.Draw(img)
    
    cx = 220 * scale
    cy = 340 * scale
    r_outer = 190 * scale
    nose_x = 115 * scale
    
    start_angle = 63.0
    end_angle = 0.0
    num_spines = 11
    stroke_w = int(8.5 * scale)
    r_cap = stroke_w / 2.0
    
    r_peak = r_outer * 0.48
    rad_start = math.radians(start_angle)
    peak_x = cx + r_peak * math.cos(rad_start)
    peak_y = cy - r_peak * math.sin(rad_start)
    
    # 1. Fill polygon
    draw.polygon([(nose_x, cy), (peak_x, peak_y), (cx, cy)], fill=color)
    
    # 2. Stroke outline with matching thickness for uniform baseline
    draw.line([(nose_x, cy), (cx, cy)], fill=color, width=stroke_w)
    draw.line([(nose_x, cy), (peak_x, peak_y)], fill=color, width=stroke_w)
    draw.line([(peak_x, peak_y), (cx, cy)], fill=color, width=stroke_w)
    draw.ellipse([nose_x - r_cap, cy - r_cap, nose_x + r_cap, cy + r_cap], fill=color)
    draw.ellipse([peak_x - r_cap, peak_y - r_cap, peak_x + r_cap, peak_y + r_cap], fill=color)
    draw.ellipse([cx - r_cap, cy - r_cap, cx + r_cap, cy + r_cap], fill=color)
    
    # 3. Spines fanning from (cx, cy)
    for i in range(num_spines):
        frac = i / (num_spines - 1)
        ang = start_angle - frac * (start_angle - end_angle)
        rad = math.radians(ang)
        curr_r = r_outer * (1.0 + 0.03 * math.sin(frac * math.pi))
        x2 = cx + curr_r * math.cos(rad)
        y2 = cy - curr_r * math.sin(rad)
        
        draw.line([(cx, cy), (x2, y2)], fill=color, width=stroke_w)
        draw.ellipse([x2 - r_cap, y2 - r_cap, x2 + r_cap, y2 + r_cap], fill=color)
        
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
