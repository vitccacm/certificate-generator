import os
import urllib.request
import ssl
import sys

# Directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, 'app', 'static', 'fonts')

if not os.path.exists(FONTS_DIR):
    os.makedirs(FONTS_DIR)
    print(f"Created directory: {FONTS_DIR}")

# Font URLs (Using reliable GitHub raw links or Google Fonts)
# Using DejaVu Sans as a robust fallback for everything
# Using Google Fonts Raw Links (High Availability)
FONTS = {
    # Noto Sans is a perfect metric-compatible replacement for DejaVu/Arial checks
    'DejaVuSans.ttf': 'https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Regular.ttf',
    'DejaVuSans-Bold.ttf': 'https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Bold.ttf',
    
    # Tinos is metric-compatible with Times New Roman
    'times.ttf': 'https://github.com/google/fonts/raw/main/apache/tinos/Tinos-Regular.ttf',
    'timesbd.ttf': 'https://github.com/google/fonts/raw/main/apache/tinos/Tinos-Bold.ttf',
    
    # Also save as DejaVuSerif for backward compatibility with my code
    'DejaVuSerif.ttf': 'https://github.com/google/fonts/raw/main/apache/tinos/Tinos-Regular.ttf',
    
    # Simple Arial fallback
    'arial.ttf': 'https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Regular.ttf'
}

def download_file(url, filename):
    filepath = os.path.join(FONTS_DIR, filename)
    if os.path.exists(filepath):
        print(f"Skipping {filename} (already exists)")
        return

    print(f"Downloading {filename}...")
    try:
        # Ignore SSL errors for old python/systems
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(url, context=ctx) as response:
            with open(filepath, 'wb') as out_file:
                out_file.write(response.read())
        print(f"Successfully downloaded {filename}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")

if __name__ == "__main__":
    print(f"Downloading fonts to {FONTS_DIR}...")
    for filename, url in FONTS.items():
        download_file(url, filename)
    print("Done! Fonts updated.")
    
    # Verify
    print("Files in fonts dir:")
    print(os.listdir(FONTS_DIR))
