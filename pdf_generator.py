import os
import tempfile
import logging
import requests
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO
import math

logger = logging.getLogger(__name__)

class PDFGenerator:
    """Professional PDF generator for MTG proxy cards"""
    
    # MTG card dimensions in mm
    CARD_WIDTH_MM = 63
    CARD_HEIGHT_MM = 88
    
    # A4 dimensions in mm
    A4_WIDTH_MM = 210
    A4_HEIGHT_MM = 297
    
    # Grid configuration
    CARDS_PER_ROW = 3
    CARDS_PER_COL = 3
    CARDS_PER_PAGE = 9
    
    # DPI settings
    DPI_SETTINGS = {
        'economy': 150,
        'standard': 300,
        'professional': 600
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MTG-Proxy-Forge/1.0'
        })
    
    def generate_pdf(self, cards, output_path, config=None):
        """Generate professional-quality PDF with cutting guides"""
        try:
            # Default configuration
            default_config = {
                'dpi': 'professional',
                'cutting_lines': True,
                'corner_guides': True,
                'bleed_margin': False,
                'line_thickness': 0.25
            }
            
            if config:
                default_config.update(config)
            config = default_config
            
            logger.info(f"Generating PDF with {len(cards)} card types, DPI: {config['dpi']}")
            
            # Expand cards based on quantity
            expanded_cards = []
            for card in cards:
                if card.get('image_url') and not card.get('error'):
                    for _ in range(card['quantity']):
                        expanded_cards.append(card)
            
            if not expanded_cards:
                logger.error("No valid cards to generate PDF")
                return False
            
            total_pages = math.ceil(len(expanded_cards) / self.CARDS_PER_PAGE)
            logger.info(f"Generating {total_pages} pages for {len(expanded_cards)} total cards")
            
            # Calculate dimensions
            dpi = self.DPI_SETTINGS[config['dpi']]
            card_width_pts = (self.CARD_WIDTH_MM * dpi) / 25.4  # Convert mm to points at specified DPI
            card_height_pts = (self.CARD_HEIGHT_MM * dpi) / 25.4
            
            # Calculate page layout
            total_cards_width = self.CARDS_PER_ROW * self.CARD_WIDTH_MM
            total_cards_height = self.CARDS_PER_COL * self.CARD_HEIGHT_MM
            
            margin_x = (self.A4_WIDTH_MM - total_cards_width) / 2
            margin_y = (self.A4_HEIGHT_MM - total_cards_height) / 2
            
            # Create PDF
            c = canvas.Canvas(output_path, pagesize=A4)
            
            # Process each page
            for page in range(total_pages):
                logger.info(f"Generating page {page + 1}/{total_pages}")
                
                start_idx = page * self.CARDS_PER_PAGE
                end_idx = min(start_idx + self.CARDS_PER_PAGE, len(expanded_cards))
                page_cards = expanded_cards[start_idx:end_idx]
                
                # Draw cards on current page
                self._draw_page(c, page_cards, margin_x, margin_y, config)
                
                if page < total_pages - 1:
                    c.showPage()
            
            c.save()
            logger.info(f"PDF saved successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return False
    
    def _draw_page(self, canvas_obj, cards, margin_x, margin_y, config):
        """Draw a single page with cards and guides"""
        
        # Draw cutting lines first (behind cards)
        if config['cutting_lines']:
            self._draw_cutting_lines(canvas_obj, margin_x, margin_y, config['line_thickness'])
        
        # Draw cards
        for i, card in enumerate(cards):
            row = i // self.CARDS_PER_ROW
            col = i % self.CARDS_PER_ROW
            
            x = margin_x + (col * self.CARD_WIDTH_MM)
            y = self.A4_HEIGHT_MM - margin_y - ((row + 1) * self.CARD_HEIGHT_MM)  # Flip Y coordinate
            
            self._draw_card(canvas_obj, card, x, y)
        
        # Draw corner guides
        if config['corner_guides']:
            self._draw_corner_guides(canvas_obj, margin_x, margin_y)
    
    def _draw_cutting_lines(self, canvas_obj, margin_x, margin_y, line_thickness):
        """Draw cutting lines between cards"""
        canvas_obj.setLineWidth(line_thickness)
        canvas_obj.setStrokeColor(colors.grey)  # Dark gray
        
        # Vertical lines
        for i in range(1, self.CARDS_PER_ROW):
            x = margin_x + (i * self.CARD_WIDTH_MM)
            y_start = margin_y - 3  # Extend 3mm beyond cards
            y_end = margin_y + (self.CARDS_PER_COL * self.CARD_HEIGHT_MM) + 3
            
            canvas_obj.line(x * mm, y_start * mm, x * mm, y_end * mm)
        
        # Horizontal lines
        for i in range(1, self.CARDS_PER_COL):
            y = margin_y + (i * self.CARD_HEIGHT_MM)
            x_start = margin_x - 3  # Extend 3mm beyond cards
            x_end = margin_x + (self.CARDS_PER_ROW * self.CARD_WIDTH_MM) + 3
            
            canvas_obj.line(x_start * mm, y * mm, x_end * mm, y * mm)
    
    def _draw_corner_guides(self, canvas_obj, margin_x, margin_y):
        """Draw corner radius guides (3mm radius)"""
        canvas_obj.setLineWidth(0.25)
        canvas_obj.setStrokeColor(colors.lightgrey)
        
        corner_radius = 3  # mm
        
        for row in range(self.CARDS_PER_COL):
            for col in range(self.CARDS_PER_ROW):
                card_x = margin_x + (col * self.CARD_WIDTH_MM)
                card_y = margin_y + (row * self.CARD_HEIGHT_MM)
                
                # Four corners of each card
                corners = [
                    (card_x, card_y),  # Bottom-left
                    (card_x + self.CARD_WIDTH_MM, card_y),  # Bottom-right
                    (card_x, card_y + self.CARD_HEIGHT_MM),  # Top-left
                    (card_x + self.CARD_WIDTH_MM, card_y + self.CARD_HEIGHT_MM)  # Top-right
                ]
                
                for i, (cx, cy) in enumerate(corners):
                    # Draw small arc indicators at each corner
                    if i == 0:  # Bottom-left
                        canvas_obj.arc((cx) * mm, (cy) * mm, (cx + corner_radius) * mm, (cy + corner_radius) * mm, 0, 90)
                    elif i == 1:  # Bottom-right
                        canvas_obj.arc((cx - corner_radius) * mm, (cy) * mm, (cx) * mm, (cy + corner_radius) * mm, 90, 180)
                    elif i == 2:  # Top-left
                        canvas_obj.arc((cx) * mm, (cy - corner_radius) * mm, (cx + corner_radius) * mm, (cy) * mm, 270, 360)
                    elif i == 3:  # Top-right
                        canvas_obj.arc((cx - corner_radius) * mm, (cy - corner_radius) * mm, (cx) * mm, (cy) * mm, 180, 270)
    
    def _draw_card(self, canvas_obj, card, x_mm, y_mm):
        """Draw individual card image"""
        try:
            image_url = card.get('image_url')
            if not image_url:
                logger.warning(f"No image URL for card: {card.get('name', 'Unknown')}")
                self._draw_placeholder(canvas_obj, card, x_mm, y_mm)
                return
            
            # Download and process image
            image_data = self._download_image(image_url)
            if not image_data:
                logger.warning(f"Failed to download image for: {card.get('name', 'Unknown')}")
                self._draw_placeholder(canvas_obj, card, x_mm, y_mm)
                return
            
            # Open image with PIL
            img = Image.open(BytesIO(image_data))
            
            # Ensure image is RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate dimensions maintaining aspect ratio
            img_width, img_height = img.size
            target_aspect = self.CARD_WIDTH_MM / self.CARD_HEIGHT_MM
            img_aspect = img_width / img_height
            
            if img_aspect > target_aspect:
                # Image is wider, fit to height
                new_height = self.CARD_HEIGHT_MM * mm
                new_width = new_height * img_aspect
                offset_x = -(new_width - self.CARD_WIDTH_MM * mm) / 2
                offset_y = 0
            else:
                # Image is taller, fit to width
                new_width = self.CARD_WIDTH_MM * mm
                new_height = new_width / img_aspect
                offset_x = 0
                offset_y = -(new_height - self.CARD_HEIGHT_MM * mm) / 2
            
            # Save image to temporary file for ReportLab
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            img.save(temp_img.name, 'JPEG', quality=95)
            temp_img.close()
            
            # Draw image
            canvas_obj.drawImage(
                temp_img.name,
                x_mm * mm + offset_x,
                y_mm * mm + offset_y,
                width=new_width,
                height=new_height,
                preserveAspectRatio=True
            )
            
            # Clean up temporary file
            os.unlink(temp_img.name)
            
        except Exception as e:
            logger.error(f"Error drawing card {card.get('name', 'Unknown')}: {str(e)}")
            self._draw_placeholder(canvas_obj, card, x_mm, y_mm)
    
    def _draw_placeholder(self, canvas_obj, card, x_mm, y_mm):
        """Draw placeholder for missing/failed card images"""
        # Draw border
        canvas_obj.setStrokeColor(colors.black)
        canvas_obj.setFillColor(colors.lightgrey)
        canvas_obj.rect(x_mm * mm, y_mm * mm, self.CARD_WIDTH_MM * mm, self.CARD_HEIGHT_MM * mm, fill=1)
        
        # Draw text
        canvas_obj.setFillColor(colors.black)
        canvas_obj.setFont("Helvetica", 8)
        text = card.get('name', 'Unknown Card')
        text_width = canvas_obj.stringWidth(text, "Helvetica", 8)
        
        # Center text
        text_x = (x_mm + self.CARD_WIDTH_MM/2) * mm - text_width/2
        text_y = (y_mm + self.CARD_HEIGHT_MM/2) * mm
        
        canvas_obj.drawString(text_x, text_y, text)
    
    def _download_image(self, url):
        """Download image from URL with error handling"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"Failed to download image: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image: {str(e)}")
            return None
import logging
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

class PDFGenerator:
    """Generator for MTG proxy PDFs"""
    
    def __init__(self):
        pass
    
    def generate_pdf(self, cards, filename, config=None):
        """Generate PDF with card proxies"""
        try:
            # Create a simple PDF for now
            c = canvas.Canvas(filename, pagesize=A4)
            c.drawString(100, 750, "MTG Proxy Cards")
            
            y = 700
            for card in cards:
                card_text = f"{card.get('quantity', 1)}x {card.get('name', 'Unknown Card')}"
                c.drawString(100, y, card_text)
                y -= 20
                if y < 100:
                    c.showPage()
                    y = 750
            
            c.save()
            logger.info(f"PDF generated successfully: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return False
