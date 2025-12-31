
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from PIL import Image, ImageDraw, ImageFont
    print("PIL Imported successfully")
except ImportError:
    print("PIL NOT INSTALLED")
    sys.exit(1)

# Manually define paths based on cPanel structure
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'app')
STATIC_FONTS_DIR = os.path.join(APP_DIR, 'static', 'fonts')

print(f"Checking Fonts Directory: {STATIC_FONTS_DIR}")

if os.path.exists(STATIC_FONTS_DIR):
    print("Directory exists.")
    files = os.listdir(STATIC_FONTS_DIR)
    print(f"Files: {files}")
else:
    print("Directory DOES NOT EXIST.")

# Try to load a specific font
font_path = os.path.join(STATIC_FONTS_DIR, 'DejaVuSans.ttf')
print(f"Attempting to load: {font_path}")

try:
    font = ImageFont.truetype(font_path, 50)
    print("SUCCESS: Font loaded via direct path.")
    
    # Test drawing size
    dummy_img = Image.new('RGB', (100, 100))
    draw = ImageDraw.Draw(dummy_img)
    try:
        # Newer Pillow
        bbox = draw.textbbox((0, 0), "Test", font=font)
        height = bbox[3] - bbox[1]
    except:
        # Older Pillow
        w, height = draw.textsize("Test", font=font)
        
    print(f"Text Height for 50px font: {height}px (Should be ~40-60)")
    
except Exception as e:
    print(f"FAILURE: {e}")
    print("Attempting load_default()...")
    font = ImageFont.load_default()
    try:
        w, height = draw.textsize("Test", font=font)
    except:
         bbox = draw.textbbox((0, 0), "Test", font=font)
         height = bbox[3] - bbox[1]
    print(f"Default Font Height: {height}px (Likely ~11)")

