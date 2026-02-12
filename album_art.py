from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageEnhance
import random
import os
import math

def generate_cover_art(mood, genre, tempo, output_path):
    """
    Generates a V2 HIGH-QUALITY procedural album cover.
    Features: Gradients, Bokeh/Glow, Compositing, Texture.
    """
    width, height = 800, 800
    
    # 1. Palette Selection
    colors = get_palette(mood, genre)
    bg_start, bg_end = colors[0], colors[1]
    accents = colors[2:]
    
    # 2. Base Gradient Layer
    base = Image.new('RGBA', (width, height), color=bg_start)
    draw = ImageDraw.Draw(base)
    
    # Draw Vertical Gradient
    for y in range(height):
        ratio = y / height
        r = int(bg_start[0] * (1 - ratio) + bg_end[0] * ratio)
        g = int(bg_start[1] * (1 - ratio) + bg_end[1] * ratio)
        b = int(bg_start[2] * (1 - ratio) + bg_end[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
    # 3. "Bokeh" Background Elements (Blurred)
    # Creates depth and atmosphere
    overlay = Image.new('RGBA', (width, height), (0,0,0,0))
    ov_draw = ImageDraw.Draw(overlay)
    
    for _ in range(15):
        x = random.randint(-100, width+100)
        y = random.randint(-100, height+100)
        rad = random.randint(100, 400)
        color = random.choice(accents)
        # Low opacity for blend
        fill = (color[0], color[1], color[2], 50) 
        ov_draw.ellipse([x-rad, y-rad, x+rad, y+rad], fill=fill)
        
    # Heavy Blur for smooth background effect
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=60))
    base = Image.alpha_composite(base, overlay)

    # 4. Stylized Foreground Shapes (Sharper)
    fg_layer = Image.new('RGBA', (width, height), (0,0,0,0))
    fg_draw = ImageDraw.Draw(fg_layer)
    
    shape_count = int(tempo / 15) + 3 # 120bpm -> ~11 shapes
    
    for i in range(shape_count):
        cx = random.randint(50, width-50)
        cy = random.randint(50, height-50)
        size = random.randint(20, 150)
        color = random.choice(accents)
        
        # Add random transparency 100-200
        fill_col = (color[0], color[1], color[2], random.randint(100, 220))
        
        # Shape Logic based on Vibe
        if mood == "Energetic" or genre in ["Rock", "Electronic"]:
            # Polygons / Shards / Lines
            if random.random() > 0.5:
                # Triangle
                points = [
                    (cx, cy - size),
                    (cx - size, cy + size),
                    (cx + size, cy + size)
                ]
                fg_draw.polygon(points, fill=fill_col, outline=(255,255,255, 50))
            else:
                # Rotated Square
                rect = Image.new('RGBA', (size*2, size*2), (0,0,0,0))
                d = ImageDraw.Draw(rect)
                d.rectangle([0,0,size*2,size*2], fill=fill_col)
                rect = rect.rotate(random.randint(0, 90))
                fg_layer.paste(rect, (cx-size, cy-size), rect)
                continue # Skip standard draw
                
        elif mood == "Sad" or mood == "Calm" or genre == "Jazz":
            # Circles / Curves / Soft
             fg_draw.ellipse([cx-size, cy-size, cx+size, cy+size], fill=fill_col)
             
        else: # Pop / Happy
            # Bubbles and rounded rects
            fg_draw.rounded_rectangle([cx-size, cy-size, cx+size, cy+size], radius=20, fill=fill_col)

    base = Image.alpha_composite(base, fg_layer)

    # 5. Central Branding / Focal Point
    # A distinct border or frame to make it look like "Album Art"
    frame_layer = Image.new('RGBA', (width, height), (0,0,0,0))
    frame_draw = ImageDraw.Draw(frame_layer)
    center_x, center_y = width // 2, height // 2
    
    # Modern "Glass" card in center
    card_w, card_h = 300, 300
    frame_draw.rectangle(
        [center_x - card_w//2, center_y - card_h//2, center_x + card_w//2, center_y + card_h//2],
        outline=(255,255,255, 180), width=3
    )
    # Inner thin line
    frame_draw.rectangle(
        [center_x - card_w//2 + 10, center_y - card_h//2 + 10, center_x + card_w//2 - 10, center_y + card_h//2 - 10],
        outline=(255,255,255, 80), width=1
    )
    
    base = Image.alpha_composite(base, frame_layer)

    # 6. Final Polish: Noise & Contrast
    # Add subtle noise for "print" texture
    noise = Image.effect_noise((width, height), 15).convert('L').convert('RGBA')
    noise.putalpha(15) # Very subtle grain
    base = Image.alpha_composite(base, noise)
    
    # Save
    base = base.convert('RGB') # Remove alpha for saving
    base.save(output_path, quality=95)
    return os.path.basename(output_path)

def get_palette(mood, genre):
    # Format: [BgStart, BgEnd, Accent1, Accent2, Accent3]
    
    # Cyber / Electronic
    if genre == "Electronic" or "Cyber" in str(mood):
        return [
            (10, 10, 30), (0, 0, 0),       # Dark Blue -> Black
            (0, 255, 255), (255, 0, 255), (50, 255, 50) # Cyan, Magenta, Green
        ]
        
    if mood == "Energetic" or genre == "Rock":
        return [
            (30, 0, 0), (0, 0, 0),        # Dark Red -> Black
            (255, 50, 0), (255, 200, 0), (200, 0, 50) # Orange, Yellow, Red
        ]
        
    if mood == "Sad" or mood == "Dark":
        return [
            (20, 25, 40), (5, 5, 10),     # Midnight -> Deep Black
            (80, 100, 160), (100, 120, 140), (200, 200, 255) # Muted Blues
        ]
        
    if mood == "Calm" or genre == "Jazz":
        return [
            (255, 250, 240), (220, 240, 220), # Cream -> Sage
            (100, 160, 120), (200, 180, 100), (140, 180, 160) # Earth tones
        ]
        
    # Happy / Pop (Default)
    return [
        (255, 100, 150), (255, 200, 100), # Pink -> Orange
        (255, 255, 0), (0, 255, 255), (255, 255, 255) # Brights
    ]
