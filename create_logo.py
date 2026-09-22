"""
Script to generate minimalist Hedgehog & Book Pages logo and favicons for HedgeDoc.
Matches the geometric, minimal aesthetic:
- Triangular snout on the left with horizontal base.
- Dark hub/wedge at the base.
- 10-11 clean radiating spines/book pages in a smooth circular arc down to horizontal baseline.
"""

from pathlib import Path
import math
from PIL import Image, ImageDraw

def create_svg(size=512, color="#18181B"):
    # Center / pivot coordinates
    # Let the base line be at y = 340
    # Snout tip at (120, 340)
    # Pivot point at (210, 340)
    # Outer radius of spines = 200
    
    cx = 220
    cy = 340
    snout_tip_x = 110
    snout_tip_y = 340
    snout_top_x = 200
    snout_top_y = 235
    
    # Radians for the spines: from ~68 deg down to 0 deg
    num_spines = 11
    start_angle_deg = 68.0
    end_angle_deg = 0.0
    
    r_outer = 190
    r_inner = 35  # originates slightly outside the pivot or from the hub
    
    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">')
    svg_lines.append('  <!-- Background: transparent -->')
    
    # Snout triangle
    # Points: snout_tip (110, 340), pivot (220, 340), forehead (195, 230)
    snout_pts = f"{snout_tip_x},{snout_tip_y} {cx},{cy} {snout_top_x},{snout_top_y}"
    svg_lines.append(f'  <polygon points="{snout_pts}" fill="{color}" />')
    
    # Hub / center wedge
    # A small pie or wedge at pivot to anchor the spines
    hub_pts = [f"{cx},{cy}"]
    for i in range(20):
        a = math.radians(start_angle_deg * (1 - i/19))
        hx = cx + 38 * math.cos(a)
        hy = cy - 38 * math.sin(a)
        hub_pts.append(f"{hx:.1f},{hy:.1f}")
    svg_lines.append(f'  <polygon points="{" ".join(hub_pts)}" fill="{color}" />')
    
    # Spines (rays)
    stroke_width = 8.5
    for i in range(num_spines):
        frac = i / (num_spines - 1)
        angle_deg = start_angle_deg - frac * (start_angle_deg - end_angle_deg)
        rad = math.radians(angle_deg)
        
        # Outer radius subtly adjusted to form a gentle hedgehog / page curve
        # slightly more extended in the middle
        curr_r_outer = r_outer * (1.0 + 0.04 * math.sin(frac * math.pi))
        
        x1 = cx + (r_inner + 5) * math.cos(rad)
        y1 = cy - (r_inner + 5) * math.sin(rad)
        x2 = cx + curr_r_outer * math.cos(rad)
        y2 = cy - curr_r_outer * math.sin(rad)
        
        svg_lines.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" />')
        
    svg_lines.append('</svg>')
    return "\n".join(svg_lines)


def render_png(size=512, color=(24, 24, 27, 255), bg_color=(255, 255, 255, 0)):
    # Render at 4x supersampling for ultra smooth antialiasing
    scale = 4
    img_size = size * scale
    img = Image.new("RGBA", (img_size, img_size), bg_color)
    draw = ImageDraw.Draw(img)
    
    cx = 220 * scale
    cy = 340 * scale
    snout_tip = (110 * scale, 340 * scale)
    snout_base = (cx, cy)
    snout_top = (195 * scale, 230 * scale)
    
    # Draw snout polygon
    draw.polygon([snout_tip, snout_base, snout_top], fill=color)
    
    # Hub polygon
    start_angle_deg = 68.0
    end_angle_deg = 0.0
    hub_pts = [(cx, cy)]
    for i in range(30):
        a = math.radians(start_angle_deg * (1 - i/29))
        hx = cx + 38 * scale * math.cos(a)
        hy = cy - 38 * scale * math.sin(a)
        hub_pts.append((hx, hy))
    draw.polygon(hub_pts, fill=color)
    
    # Spines
    num_spines = 11
    stroke_w = int(8.5 * scale)
    r_outer = 190 * scale
    r_inner = 35 * scale
    
    for i in range(num_spines):
        frac = i / (num_spines - 1)
        angle_deg = start_angle_deg - frac * (start_angle_deg - end_angle_deg)
        rad = math.radians(angle_deg)
        
        curr_r_outer = r_outer * (1.0 + 0.04 * math.sin(frac * math.pi))
        
        x1 = cx + (r_inner + 5 * scale) * math.cos(rad)
        y1 = cy - (r_inner + 5 * scale) * math.sin(rad)
        x2 = cx + curr_r_outer * math.cos(rad)
        y2 = cy - curr_r_outer * math.sin(rad)
        
        draw.line([(x1, y1), (x2, y2)], fill=color, width=stroke_w)
        # Add rounded caps
        r_cap = stroke_w / 2.0
        draw.ellipse([x2 - r_cap, y2 - r_cap, x2 + r_cap, y2 + r_cap], fill=color)
        draw.ellipse([x1 - r_cap, y1 - r_cap, x1 + r_cap, y1 + r_cap], fill=color)
        
    # Downsample with Lanczos filter for crisp antialiasing
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


if __name__ == "__main__":
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    # 1. Save SVG
    svg_content = create_svg()
    (assets_dir / "logo.svg").write_text(svg_content, encoding="utf-8")
    print("Saved assets/logo.svg")
    
    # 2. Render high-res PNG (512x512)
    logo_png = render_png(size=512)
    logo_png.save(assets_dir / "logo.png", format="PNG")
    print("Saved assets/logo.png")
    
    # 3. Render Favicon PNG (64x64 and 32x32)
    fav_64 = render_png(size=64)
    fav_64.save(assets_dir / "favicon.png", format="PNG")
    print("Saved assets/favicon.png")
    
    # 4. Save ICO
    fav_64.save(assets_dir / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("Saved assets/favicon.ico")
