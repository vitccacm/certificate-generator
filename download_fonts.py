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
FONTS = {
    'DejaVuSans.ttf': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf',
    'DejaVuSans-Bold.ttf': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf',
    'DejaVuSerif.ttf': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSerif.ttf', # For Times
    'DejaVuSerif-Bold.ttf': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSerif-Bold.ttf',
    'LiberationSans-Regular.ttf': 'https://github.com/liberationfonts/liberation-fonts/raw/master/liberation-fonts-ttf/LiberationSans-Regular.ttf' # For Arial
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
