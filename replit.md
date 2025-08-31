# MTG Proxy Forge

## Overview

MTG Proxy Forge is a Flask-based web application that converts Magic: The Gathering Arena card lists into professional-quality printable PDFs. The application allows users to paste card lists in various formats, preview and select different card editions, and generate high-resolution PDFs optimized for proxy card printing with cutting guides and professional layouts.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Single Page Application**: Built with vanilla HTML5, CSS3, and JavaScript
- **Bootstrap Dark Theme**: Uses Bootstrap with dark theme for responsive UI
- **No Frontend Framework**: Deliberately uses plain JavaScript to maintain simplicity
- **Real-time Updates**: Dynamic content updates without page reloads using fetch API

### Backend Architecture
- **Flask Microframework**: Lightweight Python web framework for API endpoints
- **Modular Service Layer**: Separated concerns with dedicated service classes:
  - `ScryfallService`: Handles external API communication with rate limiting
  - `PDFGenerator`: Manages high-quality PDF creation with ReportLab
  - `CardParser`: Processes MTG Arena format card lists with regex patterns
- **RESTful API Design**: Clean API endpoints for card processing and PDF generation

### Card Processing Pipeline
- **Multi-format Parser**: Supports various MTG Arena list formats using regex patterns
- **Card Consolidation**: Automatically merges duplicate cards from the same set
- **Edition Management**: Fetches all available card editions from Scryfall API
- **Portuguese Priority**: Prioritizes Portuguese card names and images when available

### PDF Generation System
- **Professional Layout**: 3x3 grid layout (9 cards per A4 page)
- **Standard Card Dimensions**: Precise 63mm × 88mm card sizing
- **Quality Options**: Multiple DPI settings (economy: 150, standard: 300, professional: 600)
- **Cutting Guides**: Includes cutting lines and corner radius markers for professional finishing
- **Image Processing**: Downloads and processes high-resolution card images with PIL

### Data Flow
1. User inputs card list in textarea
2. Frontend sends list to `/api/process-list` endpoint
3. Backend parses cards and fetches metadata from Scryfall
4. Frontend displays cards with edition selection dropdowns
5. User selects desired editions and requests PDF generation
6. Backend generates professional PDF with cutting guides
7. PDF is served as downloadable file

## External Dependencies

### Third-party APIs
- **Scryfall API**: Primary data source for card information, images, and edition data
  - Rate limiting implemented (100ms between requests)
  - Portuguese language prioritization
  - Comprehensive card metadata retrieval

### Python Libraries
- **Flask**: Web framework and routing
- **Requests**: HTTP client for external API calls
- **ReportLab**: Professional PDF generation with precise layout control
- **PIL (Pillow)**: Image processing and manipulation
- **Werkzeug**: WSGI utilities and middleware

### Frontend Dependencies
- **Bootstrap**: CSS framework with dark theme
- **Font Awesome**: Icon library for UI elements
- **Vanilla JavaScript**: No additional frameworks required

### Infrastructure
- **Replit Environment**: Designed for Replit hosting
- **Session Management**: Flask sessions for user state
- **Temporary File Handling**: Secure temporary file management for PDF generation
- **Logging**: Comprehensive logging throughout the application stack