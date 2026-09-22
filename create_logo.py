"""
Script to generate minimalist Hedgehog & Book Pages logo and favicons for HedgeDoc.
Updated refined design:
- Sleek, slender triangle profile (no bulkiness).
- 100% straight top edge from nose tip to the outer apex (no bend/kink/curve).
- Spines fan smoothly from apex down to horizontal baseline.
- 100% seamless integration at pivot and baseline.
"""

from pathlib import Path
import math
from PIL import Image, ImageDraw

def create_svg(size=512, color="#18181B"):
    cx = 205
    cy = 345
    r_outer = 190
    nose_offset = 82
    nose_x = cx - nose_offset
    
    start_angle = 62.0
    end_angle = 0.0
    num_spines = 11
    stroke_w = 8.0
    
    # Apex of the first spine and top vertex of the triangle
    rad_start = math.radians(start_angle)
    top_x = cx + r_outer * math.cos(rad_start)
    top_y = cy - r_outer * math.sin(rad_start)
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">')
    svg.append('  <!-- Background: transparent -->')
    
    # Slender triangle with perfectly straight top edge
    svg.append(f'  <polygon points="{nose_x},{cy} {top_x:.1f},{top_y:.1f} {cx},{cy}" fill="{color}" stroke="{color}" stroke-width="{stroke_w}" stroke-linejoin="round" stroke-linecap="round" />')
    
    # Spines radiating directly from pivot (cx, cy)
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
    
    cx = 205 * scale
    cy = 345 * scale
    r_outer = 190 * scale
    nose_offset = 82 * scale
    nose_x = cx - nose_offset
    
    start_angle = 62.0
    end_angle = 0.0
    num_spines = 11
    stroke_w = int(8.0 * scale)
    r_cap = stroke_w / 2.0
    
    rad_start = math.radians(start_angle)
    top_x = cx + r_outer * math.cos(rad_start)
    top_y = cy - r_outer * math.sin(rad_start)
    
    # 1. Fill polygon
    draw.polygon([(nose_x, cy), (top_x, top_y), (cx, cy)], fill=color)
    
    # 2. Outline with matching stroke width
    draw.line([(nose_x, cy), (cx, cy)], fill=color, width=stroke_w)
    draw.line([(nose_x, cy), (top_x, top_y)], fill=color, width=stroke_w)
    draw.ellipse([nose_x - r_cap, cy - r_cap, nose_x + r_cap, cy + r_cap], fill=color)
    draw.ellipse([top_x - r_cap, top_y - r_cap, top_x + r_cap, top_y + r_cap], fill=color)
    
    # 3. Spines radiating from (cx, cy)
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
