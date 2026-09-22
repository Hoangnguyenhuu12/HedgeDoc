"""
Script to generate minimalist Hedgehog & Book Pages logo and favicons for HedgeDoc.
Updated architecture:
- Exactly ONE single triangle for the hedgehog's head/body (no double triangles).
- The triangle's tip extends forward to form the snout on the baseline.
- The spines/book pages fan out from the rear pivot in a clean circular arc.
"""

from pathlib import Path
import math
from PIL import Image, ImageDraw

def create_svg(size=512, color="#18181B"):
    # Center / pivot coordinates
    cx = 225
    cy = 340
    snout_tip_x = 110
    snout_tip_y = cy
    
    start_angle_deg = 67.0
    end_angle_deg = 0.0
    
    # Head peak along the top spine
    r_head = 78
    rad_peak = math.radians(start_angle_deg)
    head_peak_x = cx + r_head * math.cos(rad_peak)
    head_peak_y = cy - r_head * math.sin(rad_peak)
    
    r_outer = 190
    r_inner = 30
    num_spines = 11
    stroke_width = 8.5
    
    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">')
    svg_lines.append('  <!-- Background: transparent -->')
    
    # Exactly ONE single head/body triangle
    # Points: Snout tip (110, 340) -> Head peak -> Pivot (225, 340)
    snout_pts = f"{snout_tip_x},{snout_tip_y} {head_peak_x:.1f},{head_peak_y:.1f} {cx},{cy}"
    svg_lines.append(f'  <polygon points="{snout_pts}" fill="{color}" />')
    
    # Spines (rays / book pages)
    for i in range(num_spines):
        frac = i / (num_spines - 1)
        angle_deg = start_angle_deg - frac * (start_angle_deg - end_angle_deg)
        rad = math.radians(angle_deg)
        
        curr_r_outer = r_outer * (1.0 + 0.03 * math.sin(frac * math.pi))
        
        # Start spine at r_inner (or at r_head for the top spine)
        eff_r_inner = r_head if i == 0 else r_inner
        x1 = cx + eff_r_inner * math.cos(rad)
        y1 = cy - eff_r_inner * math.sin(rad)
        x2 = cx + curr_r_outer * math.cos(rad)
        y2 = cy - curr_r_outer * math.sin(rad)
        
        svg_lines.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" />')
        
    svg_lines.append('</svg>')
    return "\n".join(svg_lines)


def render_png(size=512, color=(24, 24, 27, 255), bg_color=(255, 255, 255, 0)):
    # Render with 4x supersampling for ultra smooth antialiasing
    scale = 4
    img_size = size * scale
    img = Image.new("RGBA", (img_size, img_size), bg_color)
    draw = ImageDraw.Draw(img)
    
    cx = 225 * scale
    cy = 340 * scale
    snout_tip_x = 110 * scale
    snout_tip_y = cy
    
    start_angle_deg = 67.0
    end_angle_deg = 0.0
    
    r_head = 78 * scale
    rad_peak = math.radians(start_angle_deg)
    head_peak_x = cx + r_head * math.cos(rad_peak)
    head_peak_y = cy - r_head * math.sin(rad_peak)
    
    # Single triangle
    draw.polygon([(snout_tip_x, snout_tip_y), (head_peak_x, head_peak_y), (cx, cy)], fill=color)
    
    # Spines
    num_spines = 11
    stroke_w = int(8.5 * scale)
    r_outer = 190 * scale
    r_inner = 30 * scale
    
    for i in range(num_spines):
        frac = i / (num_spines - 1)
        angle_deg = start_angle_deg - frac * (start_angle_deg - end_angle_deg)
        rad = math.radians(angle_deg)
        
        curr_r_outer = r_outer * (1.0 + 0.03 * math.sin(frac * math.pi))
        eff_r_inner = r_head if i == 0 else r_inner
        
        x1 = cx + eff_r_inner * math.cos(rad)
        y1 = cy - eff_r_inner * math.sin(rad)
        x2 = cx + curr_r_outer * math.cos(rad)
        y2 = cy - curr_r_outer * math.sin(rad)
        
        draw.line([(x1, y1), (x2, y2)], fill=color, width=stroke_w)
        r_cap = stroke_w / 2.0
        draw.ellipse([x2 - r_cap, y2 - r_cap, x2 + r_cap, y2 + r_cap], fill=color)
        draw.ellipse([x1 - r_cap, y1 - r_cap, x1 + r_cap, y1 + r_cap], fill=color)
        
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


if __name__ == "__main__":
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # 1. Save SVG to assets and static
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
