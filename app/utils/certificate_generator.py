"""
Certificate Generator Utility
Generates personalized certificates by overlaying participant names on PNG templates.
Uses Pillow for image manipulation.
Compatible with cPanel shared hosting (pure Python).
"""
import os
import io
import logging

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError as e:
    PIL_AVAILABLE = False
    logging.error(f"Pillow not installed: {e}")

# Base directories
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_CURRENT_DIR)
_BUNDLED_FONTS_DIR = os.path.join(_APP_DIR, 'static', 'fonts')

# Available fonts mapping: key -> (Display Name, [List of filenames to try])
AVAILABLE_FONTS = {
    'arial': ('Arial', ['DejaVuSans.ttf', 'arial.ttf', 'Arial.ttf', 'LiberationSans-Regular.ttf']),
    'arial_bold': ('Arial Bold', ['DejaVuSans-Bold.ttf', 'arialbd.ttf', 'Arial Bold.ttf']),
    'times': ('Times New Roman', ['DejaVuSerif.ttf', 'times.ttf', 'Times New Roman.ttf', 'LiberationSerif-Regular.ttf']),
    'times_bold': ('Times New Roman Bold', ['DejaVuSerif-Bold.ttf', 'timesbd.ttf', 'Times New Roman Bold.ttf']),
    'georgia': ('Georgia', ['DejaVuSerif.ttf', 'georgia.ttf']),
    'verdana': ('Verdana', ['DejaVuSans.ttf', 'verdana.ttf']),
    'tahoma': ('Tahoma', ['DejaVuSans.ttf', 'tahoma.ttf']),
    'courier': ('Courier New', ['DejaVuSansMono.ttf', 'cour.ttf', 'Courier New.ttf']),
}

def get_available_fonts():
    """Return dictionary of available fonts for configuration UI"""
    return AVAILABLE_FONTS


def get_font(font_name, font_size):
    """
    Get ImageFont object. Prioritizes bundled fonts.
    """
    font_info = AVAILABLE_FONTS.get(font_name.lower(), AVAILABLE_FONTS['arial'])
    font_files = font_info[1]
    
    # Check bundled fonts FIRST (and let Pillow fallback search if path fails)
    for filename in font_files:
        path = os.path.join(_BUNDLED_FONTS_DIR, filename)
        try:
            # removing exists check because Pillow might find it in system paths even if path is wrong
            return ImageFont.truetype(filename, font_size) 
        except Exception:
            try:
                # Try full path
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue

    # Fallback to system fonts explicit paths
    system_paths = [
        '/usr/share/fonts/truetype/dejavu/',
        '/usr/share/fonts/truetype/',
        '/usr/local/share/fonts/',
    ]
    
    for filename in font_files:
        for sys_dir in system_paths:
            path = os.path.join(sys_dir, filename)
            if os.path.exists(path):
                try:
                    logging.info(f"Loading system font: {path}")
                    return ImageFont.truetype(path, font_size)
                except:
                    continue
                    
    logging.warning(f"No suitable font found for {font_name}. Using default.")
    return ImageFont.load_default()


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return (0, 0, 0)


def generate_certificate_png(template_path, participant_name, x_percent, y_percent, 
                             font_size=70, font_color='#000000', font_name='times'):
    # Force Hardcoded values as requested to fix persistent issues
    font_size = 70
    font_name = 'times'

    if not PIL_AVAILABLE: return None
    
    try:
        if not os.path.exists(template_path):
            logging.error(f"Template missing: {template_path}")
            return None

        with Image.open(template_path) as template:
            if template.mode != 'RGBA':
                template = template.convert('RGBA')
            
            certificate = template.copy()
            draw = ImageDraw.Draw(certificate)
            width, height = certificate.size
            
            x = (x_percent / 100) * width
            y = (y_percent / 100) * height
            
            font = get_font(font_name, font_size)
            color = hex_to_rgb(font_color)
            
            # Determine text size
            try:
                # Newer Pillow
                bbox = draw.textbbox((0, 0), participant_name, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except AttributeError:
                # Older Pillow fallback
                text_width, text_height = draw.textsize(participant_name, font=font)
            
            text_x = x - (text_width / 2)
            text_y = y - (text_height / 2)
            
            draw.text((text_x, text_y), participant_name, fill=color, font=font)
            
            # Convert back to RGB/PNG
            if certificate.mode == 'RGBA':
                background = Image.new('RGB', certificate.size, (255, 255, 255))
                background.paste(certificate, mask=certificate.split()[3])
                certificate = background
            
            output = io.BytesIO()
            certificate.save(output, format='PNG', quality=95)
            output.seek(0)
            return output.getvalue()
            
    except Exception as e:
        logging.error(f"Certificate generation error: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None

def get_template_dimensions(template_path):
    if not PIL_AVAILABLE or not os.path.exists(template_path): return None
    try:
        with Image.open(template_path) as img: return img.size
    except: return None

def get_template_preview_image(template_path, max_width=800):
    if not PIL_AVAILABLE or not os.path.exists(template_path): return None
    try:
        with Image.open(template_path) as img:
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)))
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
    except: return None

# Backward compatibility
def generate_certificate(*args, **kwargs):
    return generate_certificate_png(*args, **kwargs)
