"""
Certificate Generator Utility
Generates personalized certificates by overlaying participant names on PNG templates.
Uses Pillow for image manipulation.
Compatible with cPanel shared hosting (pure Python, no native dependencies).
"""
import os
import io
import logging

# Try importing Pillow
PIL_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError as e:
    logging.error(f"Pillow not installed: {e}")


# Available fonts for certificate names
# Maps font key to (Display Name, Font File Pattern, CSS Font Family)
AVAILABLE_FONTS = {
    'arial': ('Arial', ['arial.ttf', 'Arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf', 'FreeSans.ttf']),
    'arial_bold': ('Arial Bold', ['arialbd.ttf', 'Arial Bold.ttf', 'DejaVuSans-Bold.ttf', 'LiberationSans-Bold.ttf', 'FreeSansBold.ttf']),
    'times': ('Times New Roman', ['times.ttf', 'Times New Roman.ttf', 'DejaVuSerif.ttf', 'LiberationSerif-Regular.ttf', 'FreeSerif.ttf']),
    'times_bold': ('Times New Roman Bold', ['timesbd.ttf', 'Times New Roman Bold.ttf', 'DejaVuSerif-Bold.ttf', 'LiberationSerif-Bold.ttf', 'FreeSerifBold.ttf']),
    'georgia': ('Georgia', ['georgia.ttf', 'Georgia.ttf', 'DejaVuSerif.ttf', 'LiberationSerif-Regular.ttf']),
    'verdana': ('Verdana', ['verdana.ttf', 'Verdana.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']),
    'tahoma': ('Tahoma', ['tahoma.ttf', 'Tahoma.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']),
    'courier': ('Courier New', ['cour.ttf', 'Courier New.ttf', 'DejaVuSansMono.ttf', 'LiberationMono-Regular.ttf', 'FreeMono.ttf']),
    'trebuchet': ('Trebuchet MS', ['trebuc.ttf', 'Trebuchet MS.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']),
    'palatino': ('Palatino Linotype', ['pala.ttf', 'Palatino Linotype.ttf', 'DejaVuSerif.ttf', 'LiberationSerif-Regular.ttf']),
    'garamond': ('Garamond', ['gara.ttf', 'Garamond.ttf', 'DejaVuSerif.ttf', 'LiberationSerif-Regular.ttf']),
    'bookman': ('Bookman Old Style', ['bookos.ttf', 'Bookman Old Style.ttf', 'DejaVuSerif.ttf']),
    'century': ('Century Gothic', ['GOTHIC.TTF', 'Century Gothic.ttf', 'DejaVuSans.ttf']),
    'lucida': ('Lucida Console', ['lucon.ttf', 'Lucida Console.ttf', 'DejaVuSansMono.ttf']),
}

# Get the path to bundled fonts (app/static/fonts/)
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(_CURRENT_DIR)), 'static', 'fonts')

# Font search directories - bundled fonts first for cPanel compatibility
FONT_DIRS = [
    # Bundled fonts (most reliable for cPanel/shared hosting)
    _STATIC_FONTS_DIR,
    os.path.join(os.path.dirname(_CURRENT_DIR), 'static', 'fonts'),
    # Linux
    '/usr/share/fonts/truetype/dejavu/',
    '/usr/share/fonts/truetype/liberation/',
    '/usr/share/fonts/truetype/freefont/',
    '/usr/share/fonts/truetype/msttcorefonts/',
    '/usr/share/fonts/truetype/',
    '/usr/local/share/fonts/',
    # macOS
    '/System/Library/Fonts/',
    '/Library/Fonts/',
    '~/Library/Fonts/',
    # Windows
    'C:/Windows/Fonts/',
]

# Map old font names to new equivalents for backward compatibility
FONT_NAME_MAP = {
    'helv': 'arial',
    'hebo': 'arial_bold',
    'tiro': 'times',
    'tiit': 'times',
    'tibo': 'times_bold',
    'cour': 'courier',
    'cobo': 'courier',
    'symb': 'arial',
    'Helvetica': 'arial',
    'Helvetica-Bold': 'arial_bold',
    'Times-Roman': 'times',
    'Times-Italic': 'times',
    'Times-Bold': 'times_bold',
    'Courier': 'courier',
    'Courier-Bold': 'courier',
    'helvetica': 'arial',
}


def get_available_fonts():
    """Return dictionary of available fonts for UI dropdown."""
    return {k: v[0] for k, v in AVAILABLE_FONTS.items()}


def hex_to_rgb(hex_color):
    """
    Convert hex color to RGB tuple (0-255 range).
    
    Args:
        hex_color: Hex color string (e.g., '#FF0000' or 'FF0000')
    
    Returns:
        tuple: RGB values as integers (0-255 range)
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return (0, 0, 0)  # Default to black
    
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
    except ValueError:
        return (0, 0, 0)


def map_font_name(font_name):
    """
    Map old font names to new equivalents.
    Returns the mapped font name.
    """
    if font_name in FONT_NAME_MAP:
        return FONT_NAME_MAP[font_name]
    if font_name.lower() in AVAILABLE_FONTS:
        return font_name.lower()
    return 'arial'  # Default fallback


def find_font_file(font_name):
    """
    Find the actual font file path for a given font name.
    
    Args:
        font_name: Key from AVAILABLE_FONTS
    
    Returns:
        str: Path to font file, or None if not found
    """
    mapped_font = map_font_name(font_name)
    
    if mapped_font not in AVAILABLE_FONTS:
        mapped_font = 'arial'
    
    font_files = AVAILABLE_FONTS[mapped_font][1]
    
    # Search through font directories
    for font_dir in FONT_DIRS:
        expanded_dir = os.path.expanduser(font_dir)
        if not os.path.exists(expanded_dir):
            continue
        
        for font_file in font_files:
            font_path = os.path.join(expanded_dir, font_file)
            if os.path.exists(font_path):
                return font_path
            
            # Also search subdirectories
            for root, dirs, files in os.walk(expanded_dir):
                if font_file in files:
                    return os.path.join(root, font_file)
    
    return None


def get_font(font_name, font_size):
    """
    Get a PIL ImageFont object for the specified font.
    Falls back to default font if specified font not available.
    
    Args:
        font_name: Name of the font (key from AVAILABLE_FONTS)
        font_size: Size of the font
    
    Returns:
        ImageFont object
    """
    font_path = find_font_file(font_name)
    
    if font_path:
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception as e:
            logging.warning(f"Could not load font {font_path}: {e}")
    
    # Fallback: Try common paths directly
    fallback_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    
    for fallback_path in fallback_fonts:
        if os.path.exists(fallback_path):
            try:
                return ImageFont.truetype(fallback_path, font_size)
            except Exception:
                continue
    
    # Last resort: default font
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_certificate_png(template_path, participant_name, x_percent, y_percent, 
                             font_size=36, font_color='#000000', font_name='arial'):
    """
    Generate a personalized certificate PNG by overlaying the participant's name
    on the template image.
    
    Args:
        template_path: Path to the PNG template file
        participant_name: Name to overlay on the certificate
        x_percent: X position as percentage (0-100) from left
        y_percent: Y position as percentage (0-100) from top
        font_size: Font size for the name (default 36)
        font_color: Hex color for the name text (default black)
        font_name: Font name from AVAILABLE_FONTS (default 'arial')
    
    Returns:
        bytes: Generated PNG as bytes, or None if error
    """
    if not PIL_AVAILABLE:
        logging.error("Cannot generate certificate: Pillow is not installed")
        return None
    
    if not os.path.exists(template_path):
        logging.error(f"Template file not found: {template_path}")
        return None
    
    try:
        # Open the template image
        with Image.open(template_path) as template:
            # Convert to RGBA if necessary
            if template.mode != 'RGBA':
                template = template.convert('RGBA')
            
            # Create a copy to draw on
            certificate = template.copy()
            draw = ImageDraw.Draw(certificate)
            
            # Get image dimensions
            width, height = certificate.size
            
            # Calculate absolute position from percentages
            x = (x_percent / 100) * width
            y = (y_percent / 100) * height
            
            # Get the font
            font = get_font(font_name, font_size)
            
            # Get text color
            color = hex_to_rgb(font_color)
            
            # Get text bounding box for centering
            if font:
                bbox = draw.textbbox((0, 0), participant_name, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(participant_name) * 10
                text_height = 20
            
            # Center the text at the specified position
            text_x = x - (text_width / 2)
            text_y = y - (text_height / 2)
            
            # Draw the name
            draw.text((text_x, text_y), participant_name, fill=color, font=font)
            
            # Convert to RGB for PNG output (remove alpha)
            if certificate.mode == 'RGBA':
                # Create white background
                background = Image.new('RGB', certificate.size, (255, 255, 255))
                background.paste(certificate, mask=certificate.split()[3])
                certificate = background
            
            # Save to bytes
            output = io.BytesIO()
            certificate.save(output, format='PNG', quality=95)
            output.seek(0)
            
            return output.getvalue()
    
    except Exception as e:
        import traceback
        logging.error(f"Certificate generation failed: {e}")
        logging.error(traceback.format_exc())
        return None


def get_template_dimensions(template_path):
    """
    Get the dimensions of a template image.
    
    Args:
        template_path: Path to the template image file
    
    Returns:
        tuple: (width, height) in pixels, or None if error
    """
    if not PIL_AVAILABLE:
        return None
    
    if not os.path.exists(template_path):
        return None
    
    try:
        with Image.open(template_path) as img:
            return img.size
    except Exception as e:
        logging.error(f"Could not get template dimensions: {e}")
        return None


def get_template_preview_image(template_path, max_width=800):
    """
    Get a preview image of the template.
    
    Args:
        template_path: Path to the template image file
        max_width: Maximum width for the preview
    
    Returns:
        bytes: PNG image data, or None if error
    """
    if not PIL_AVAILABLE:
        return None
    
    if not os.path.exists(template_path):
        return None
    
    try:
        with Image.open(template_path) as img:
            # Resize if necessary
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            
            return output.getvalue()
    
    except Exception as e:
        logging.error(f"Could not create template preview: {e}")
        return None


# Backward compatibility
def generate_certificate(*args, **kwargs):
    """Deprecated: Use generate_certificate_png instead."""
    return generate_certificate_png(*args, **kwargs)
