"""
Certificate Generator Utility
Generates personalized certificates by overlaying participant names on PDF templates.
Uses PyMuPDF (fitz) for PDF manipulation.
"""
import os
import io
import fitz  # PyMuPDF


# Available fonts for certificate names
# PyMuPDF built-in fonts that work universally
AVAILABLE_FONTS = {
    'helv': 'Helvetica',
    'hebo': 'Helvetica Bold',
    'tiro': 'Times Roman',
    'tiit': 'Times Italic',
    'tibo': 'Times Bold',
    'cour': 'Courier',
    'cobo': 'Courier Bold',
    'symb': 'Symbol',
}


def get_available_fonts():
    """Return dictionary of available fonts for UI dropdown."""
    return AVAILABLE_FONTS


def hex_to_rgb(hex_color):
    """
    Convert hex color to RGB tuple (0-1 range for PyMuPDF).
    
    Args:
        hex_color: Hex color string (e.g., '#FF0000' or 'FF0000')
    
    Returns:
        tuple: RGB values as floats (0-1 range)
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return (0, 0, 0)  # Default to black
    
    try:
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        return (r, g, b)
    except ValueError:
        return (0, 0, 0)


def generate_certificate(template_path, participant_name, x_percent, y_percent, 
                         font_size=36, font_color='#000000', font_name='helv'):
    """
    Generate a personalized certificate PDF by overlaying the participant's name
    on the template PDF.
    
    Args:
        template_path: Path to the PDF template file
        participant_name: Name to overlay on the certificate
        x_percent: X position as percentage (0-100) from left
        y_percent: Y position as percentage (0-100) from top
        font_size: Font size for the name (default 36)
        font_color: Hex color for the name text (default black)
        font_name: Font name from AVAILABLE_FONTS (default 'helv')
    
    Returns:
        bytes: Generated PDF as bytes, or None if error
    """
    if not os.path.exists(template_path):
        return None
    
    # Validate font name
    if font_name not in AVAILABLE_FONTS:
        font_name = 'helv'
    
    try:
        # Open the template PDF
        doc = fitz.open(template_path)
        
        if len(doc) == 0:
            doc.close()
            return None
        
        # Work on the first page
        page = doc[0]
        rect = page.rect
        
        # Calculate absolute position from percentages
        x = (x_percent / 100) * rect.width
        y = (y_percent / 100) * rect.height
        
        # Convert hex color to RGB
        color = hex_to_rgb(font_color)
        
        # Create text position point
        point = fitz.Point(x, y)
        
        # Insert the name text centered at the position
        # For centering, we need to calculate text width
        text_length = fitz.get_text_length(participant_name, fontname=font_name, fontsize=font_size)
        centered_x = x - (text_length / 2)
        point = fitz.Point(centered_x, y)
        
        # Insert text on the page
        page.insert_text(
            point,
            participant_name,
            fontsize=font_size,
            color=color,
            fontname=font_name
        )
        
        # Save to bytes
        output = io.BytesIO()
        doc.save(output)
        doc.close()
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        print(f"Error generating certificate: {e}")
        return None


def get_template_dimensions(template_path):
    """
    Get the dimensions of the first page of a PDF template.
    
    Args:
        template_path: Path to the PDF template file
    
    Returns:
        tuple: (width, height) in points, or None if error
    """
    if not os.path.exists(template_path):
        return None
    
    try:
        doc = fitz.open(template_path)
        if len(doc) == 0:
            doc.close()
            return None
        
        page = doc[0]
        width = page.rect.width
        height = page.rect.height
        doc.close()
        
        return (width, height)
    except Exception:
        return None


def get_template_preview_image(template_path, max_width=800):
    """
    Generate a preview image of the first page of a PDF template.
    
    Args:
        template_path: Path to the PDF template file
        max_width: Maximum width of the preview image
    
    Returns:
        bytes: PNG image as bytes, or None if error
    """
    if not os.path.exists(template_path):
        return None
    
    try:
        doc = fitz.open(template_path)
        if len(doc) == 0:
            doc.close()
            return None
        
        page = doc[0]
        
        # Calculate zoom to fit max_width
        zoom = max_width / page.rect.width
        mat = fitz.Matrix(zoom, zoom)
        
        # Render page to image
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        
        doc.close()
        return img_bytes
        
    except Exception as e:
        print(f"Error generating preview: {e}")
        return None
