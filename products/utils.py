import requests
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os

def apply_frame_to_image(image_url, frame_path):
    """
    Downloads image from url, applies frame from frame_path, returns ContentFile.
    """
    try:
        # Download Image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        
        # Open Frame
        if not os.path.exists(frame_path):
            print(f"Frame file not found: {frame_path}")
            return None
            
        frame = Image.open(frame_path).convert("RGBA")
        
        # Resize frame to match image size
        frame = frame.resize(img.size, Image.Resampling.LANCZOS)
        
        # Overlay
        # img is the base, frame is the overlay
        img.paste(frame, (0, 0), frame)
        
        # Convert back to RGB (remove alpha) for JPEG saving
        final_img = Image.new("RGB", img.size, (255, 255, 255))
        final_img.paste(img, mask=img.split()[3]) # Use alpha channel as mask
        
        output = BytesIO()
        # Save as JPEG
        final_img.save(output, format='JPEG', quality=95)
        
        # Generate a filename
        filename = os.path.basename(image_url.split('?')[0]) # Remove query params
        if not filename.lower().endswith('.jpg') and not filename.lower().endswith('.jpeg'):
            filename += '.jpg'
            
        return ContentFile(output.getvalue(), name=f"framed_{filename}")
        
    except Exception as e:
        print(f"Error processing image {image_url}: {e}")
        return None
