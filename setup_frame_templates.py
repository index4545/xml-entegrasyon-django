import os
from PIL import Image, ImageDraw

def create_frames():
    base_dir = os.path.join(os.getcwd(), 'media', 'frame_templates')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    size = (1200, 1200)
    
    # 1. Red Bold
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    border_width = 40
    # Draw rectangle border
    # Top
    draw.rectangle([(0, 0), (size[0], border_width)], fill='red')
    # Bottom
    draw.rectangle([(0, size[1]-border_width), (size[0], size[1])], fill='red')
    # Left
    draw.rectangle([(0, 0), (border_width, size[1])], fill='red')
    # Right
    draw.rectangle([(size[0]-border_width, 0), (size[0], size[1])], fill='red')
    
    img.save(os.path.join(base_dir, 'frame_red_bold.png'))
    print("Created frame_red_bold.png")

    # 2. Blue Double
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Outer Blue
    w1 = 30
    draw.rectangle([(0, 0), (size[0], size[1])], outline='blue', width=w1)
    
    # Inner Blue (gap of 10px)
    gap = 10
    inset = w1 + gap
    w2 = 15
    draw.rectangle([(inset, inset), (size[0]-inset, size[1]-inset)], outline='darkblue', width=w2)
    
    img.save(os.path.join(base_dir, 'frame_blue_double.png'))
    print("Created frame_blue_double.png")

    # 3. Corner Badge (Orange)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (size[0], size[1])], outline='orange', width=20)
    
    # Triangle Top Left
    triangle_size = 250
    draw.polygon([(0, 0), (triangle_size, 0), (0, triangle_size)], fill='orange')
    
    # Text simulation (White lines)
    draw.line([(20, 20), (100, 100)], fill='white', width=5)
    
    img.save(os.path.join(base_dir, 'frame_orange_badge.png'))
    print("Created frame_orange_badge.png")

    # 4. Elegant Black
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Outer
    draw.rectangle([(0, 0), (size[0], size[1])], outline='black', width=10)
    
    # Inner thin
    inset = 25
    draw.rectangle([(inset, inset), (size[0]-inset, size[1]-inset)], outline='black', width=2)
    
    img.save(os.path.join(base_dir, 'frame_elegant_black.png'))
    print("Created frame_elegant_black.png")

if __name__ == "__main__":
    create_frames()
