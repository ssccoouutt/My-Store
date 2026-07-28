# ============================================
# COMPLETE STORE SCRIPT - RENDER DEPLOYMENT
# ============================================

import threading
import time
import json
import os
import base64
import re
from flask import Flask, render_template_string, request, jsonify, send_file
import requests
import logging
from PIL import Image
from io import BytesIO
import urllib.parse

# ============================================
# CONFIGURATION - HARDCODED
# ============================================

TELEGRAM_BOT_TOKEN = "8898921110:AAFGHyoOkhpo8lC1UbbA7SyaMWSd1qmFNcE"
WHATSAPP_NUMBER = "923400315734"  # Without + sign
ADMIN_CHAT_ID = "990321391"

# File to store products
PRODUCTS_FILE = "products.json"
IMAGES_FOLDER = "product_images"

# Create images folder if it doesn't exist
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# ============================================
# INITIALIZE PRODUCTS
# ============================================

def load_products():
    """Load products from JSON file"""
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'r') as f:
            return json.load(f)
    return []  # Start with empty products

def save_products(products):
    """Save products to JSON file"""
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(products, f, indent=2)

# Load products
products = load_products()
next_product_id = max([p["id"] for p in products]) + 1 if products else 1

# ============================================
# FLASK WEB APP
# ============================================

app = Flask(__name__)

# HTML Template with 2 columns mobile, 3 columns desktop
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>🛒 Premium Store</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            min-height: 100vh;
            padding: 0;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .header h1 {
            color: white;
            font-size: 1.8em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .header h1 span {
            font-weight: 300;
            font-size: 0.6em;
            opacity: 0.8;
            display: block;
        }
        
        .header-stats {
            color: white;
            background: rgba(255,255,255,0.15);
            padding: 8px 16px;
            border-radius: 30px;
            backdrop-filter: blur(10px);
            font-size: 0.85em;
            white-space: nowrap;
        }
        
        .header-stats strong {
            font-size: 1.2em;
        }
        
        /* Main Container */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 15px 10px;
        }
        
        /* Filter/Search Bar */
        .controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 20px;
            background: white;
            padding: 12px 18px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .controls .count {
            color: #555;
            font-size: 0.9em;
        }
        
        .controls .count strong {
            color: #667eea;
            font-size: 1.1em;
        }
        
        .controls input {
            padding: 8px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 0.9em;
            width: 200px;
            transition: all 0.3s ease;
            outline: none;
        }
        
        .controls input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Products Grid - Responsive */
        .products-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Product Card */
        .product-card {
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 2px 15px rgba(0,0,0,0.06);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            position: relative;
        }
        
        .product-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }
        
        /* Product Image */
        .product-image-container {
            position: relative;
            height: 200px;
            overflow: hidden;
            background: #f8f9fa;
        }
        
        .product-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }
        
        .product-card:hover .product-image {
            transform: scale(1.05);
        }
        
        .product-image-placeholder {
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #e0e0e0 0%, #f0f0f0 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3em;
            color: #999;
        }
        
        .product-badge {
            position: absolute;
            top: 10px;
            right: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.7em;
            font-weight: 600;
            box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        
        /* Product Content */
        .product-content {
            padding: 14px 16px 18px;
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .product-name {
            font-size: 1.05em;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 6px;
            line-height: 1.3;
            min-height: 2.6em;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .product-prices {
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin: 6px 0 10px;
            flex-wrap: wrap;
        }
        
        .product-price-pkr {
            font-size: 1.5em;
            font-weight: 800;
            color: #667eea;
        }
        
        .product-price-pkr::before {
            content: 'Rs. ';
            font-weight: 600;
        }
        
        .product-price-usd {
            font-size: 0.85em;
            color: #888;
            font-weight: 500;
        }
        
        .product-price-usd::before {
            content: '$';
        }
        
        .product-description {
            color: #555;
            font-size: 0.82em;
            line-height: 1.5;
            margin: 6px 0 10px;
            flex: 1;
            min-height: 2.8em;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .product-instructions {
            background: #f8f9fa;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.78em;
            color: #666;
            margin: 6px 0 12px;
            border-left: 3px solid #667eea;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .product-instructions::before {
            content: '📋 ';
        }
        
        /* Buy Button */
        .buy-btn {
            background: #25D366;
            color: white;
            border: none;
            padding: 12px 16px;
            border-radius: 50px;
            font-size: 0.9em;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            margin-top: auto;
            box-shadow: 0 4px 15px rgba(37, 211, 102, 0.25);
        }
        
        .buy-btn:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 25px rgba(37, 211, 102, 0.35);
            background: #20b85f;
        }
        
        .buy-btn::before {
            content: '💬';
            font-size: 1em;
        }
        
        /* Empty State */
        .empty-message {
            grid-column: 1 / -1;
            text-align: center;
            padding: 60px 20px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.06);
        }
        
        .empty-message .icon {
            font-size: 3em;
            margin-bottom: 15px;
            display: block;
        }
        
        .empty-message h2 {
            color: #333;
            font-size: 1.3em;
            margin-bottom: 8px;
        }
        
        .empty-message p {
            color: #888;
            font-size: 0.95em;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 20px 15px;
            color: #888;
            font-size: 0.8em;
            margin-top: 15px;
            border-top: 1px solid #e0e0e0;
        }
        
        /* ============================================
           RESPONSIVE BREAKPOINTS
           ============================================ */
        
        /* Mobile: 2 columns */
        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.3em;
            }
            
            .header h1 span {
                font-size: 0.55em;
            }
            
            .header-stats {
                font-size: 0.7em;
                padding: 6px 12px;
            }
            
            .controls {
                flex-direction: row;
                flex-wrap: wrap;
                padding: 10px 14px;
            }
            
            .controls .count {
                font-size: 0.8em;
            }
            
            .controls input {
                width: 140px;
                font-size: 0.8em;
                padding: 6px 14px;
            }
            
            .products-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
            }
            
            .product-image-container {
                height: 150px;
            }
            
            .product-content {
                padding: 10px 12px 14px;
            }
            
            .product-name {
                font-size: 0.9em;
                min-height: 2.2em;
            }
            
            .product-price-pkr {
                font-size: 1.2em;
            }
            
            .product-price-usd {
                font-size: 0.75em;
            }
            
            .product-description {
                font-size: 0.75em;
                min-height: 2.4em;
            }
            
            .product-instructions {
                font-size: 0.7em;
                padding: 6px 10px;
            }
            
            .buy-btn {
                font-size: 0.8em;
                padding: 10px 12px;
            }
            
            .product-badge {
                font-size: 0.6em;
                padding: 3px 10px;
                top: 8px;
                right: 8px;
            }
            
            .product-image-placeholder {
                font-size: 2em;
            }
        }
        
        /* Very small phones: still 2 columns but smaller */
        @media (max-width: 400px) {
            .products-grid {
                gap: 8px;
            }
            
            .product-image-container {
                height: 120px;
            }
            
            .product-name {
                font-size: 0.8em;
            }
            
            .product-price-pkr {
                font-size: 1em;
            }
            
            .product-description {
                font-size: 0.7em;
            }
            
            .product-instructions {
                font-size: 0.65em;
                padding: 4px 8px;
            }
            
            .buy-btn {
                font-size: 0.7em;
                padding: 8px 10px;
            }
            
            .controls input {
                width: 100px;
                font-size: 0.7em;
            }
        }
        
        /* Tablet: 2 columns */
        @media (min-width: 769px) and (max-width: 1024px) {
            .products-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
            }
            
            .product-image-container {
                height: 220px;
            }
        }
        
        /* Desktop: 3 columns */
        @media (min-width: 1025px) {
            .products-grid {
                grid-template-columns: repeat(3, 1fr);
                gap: 25px;
            }
            
            .product-image-container {
                height: 250px;
            }
            
            .header h1 {
                font-size: 2.2em;
            }
            
            .container {
                padding: 25px 20px;
            }
        }
        
        /* Large Desktop: still 3 columns but wider */
        @media (min-width: 1400px) {
            .products-grid {
                gap: 30px;
            }
            
            .product-image-container {
                height: 280px;
            }
        }
        
        /* Scrollbar Style */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f0f2f5;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #764ba2;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="header-content">
            <h1>
                🛒 Premium Store
                <span>Quality Products at Best Prices</span>
            </h1>
            <div class="header-stats">
                📦 <strong>{{ products|length }}</strong> Products
            </div>
        </div>
    </div>
    
    <!-- Main Container -->
    <div class="container">
        <!-- Controls -->
        <div class="controls">
            <div class="count">
                Showing <strong>{{ products|length }}</strong> products
            </div>
            <input type="text" id="searchInput" placeholder="🔍 Search..." onkeyup="filterProducts()">
        </div>
        
        <!-- Products Grid -->
        <div class="products-grid" id="productsGrid">
            {% if products %}
                {% for product in products %}
                <div class="product-card" data-name="{{ product.name|lower }}" data-id="{{ product.id }}">
                    <div class="product-image-container">
                        {% if product.image_base64 %}
                            <img src="data:image/jpeg;base64,{{ product.image_base64 }}" class="product-image" alt="{{ product.name }}">
                        {% else %}
                            <div class="product-image-placeholder">🛍️</div>
                        {% endif %}
                        <span class="product-badge">⭐ Featured</span>
                    </div>
                    
                    <div class="product-content">
                        <div class="product-name">{{ product.name }}</div>
                        
                        <div class="product-prices">
                            <span class="product-price-pkr">{{ "%.0f"|format(product.price_pkr) }}</span>
                            <span class="product-price-usd">{{ "%.2f"|format(product.price_usd) }}</span>
                        </div>
                        
                        <div class="product-description">{{ product.description }}</div>
                        
                        <div class="product-instructions">{{ product.instructions }}</div>
                        
                        <a href="https://wa.me/{{ whatsapp_number }}?text={{ product.whatsapp_message | urlencode }}" 
                           target="_blank" 
                           class="buy-btn">
                            Buy Now
                        </a>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty-message">
                    <span class="icon">📭</span>
                    <h2>No Products Available</h2>
                    <p>Check back later for new products!</p>
                </div>
            {% endif %}
        </div>
        
        <div class="footer">
            <p>🏪 Powered by Telegram Bot | Admin Dashboard Available</p>
        </div>
    </div>
    
    <script>
        function filterProducts() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const cards = document.getElementsByClassName('product-card');
            let visibleCount = 0;
            
            for (let card of cards) {
                const name = card.getAttribute('data-name');
                if (name.includes(filter)) {
                    card.style.display = '';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            }
            
            // Update count
            const countElement = document.querySelector('.controls .count strong');
            if (countElement) {
                countElement.textContent = visibleCount;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(
        HTML_TEMPLATE,
        products=products,
        whatsapp_number=WHATSAPP_NUMBER
    )

@app.route('/api/products')
def api_products():
    """API endpoint to get products"""
    return jsonify(products)

@app.route('/images/<filename>')
def get_image(filename):
    """Serve product images"""
    try:
        return send_file(os.path.join(IMAGES_FOLDER, filename))
    except:
        return "Image not found", 404

# ============================================
# TELEGRAM BOT - USING REQUESTS
# ============================================

def send_telegram_message(chat_id, text, parse_mode='Markdown'):
    """Send a message using Telegram Bot API directly"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return None

def download_telegram_file(file_id):
    """Download a file from Telegram"""
    try:
        # Get file path
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
        response = requests.get(url, params={'file_id': file_id})
        file_info = response.json()
        
        if not file_info.get('ok'):
            return None
        
        file_path = file_info['result']['file_path']
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        
        # Download file
        response = requests.get(file_url)
        return response.content
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

def get_telegram_updates(offset=None):
    """Get updates from Telegram Bot API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    try:
        response = requests.get(url, params=params)
        return response.json().get('result', [])
    except Exception as e:
        print(f"Error getting updates: {e}")
        return []

def process_telegram_command(update):
    """Process incoming Telegram commands"""
    try:
        message = update.get('message', {})
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        # Check for photo attachment
        photo = message.get('photo')
        has_image = False
        image_file_id = None
        
        # Check for photo in caption or as separate entity
        if photo:
            # Get the largest photo
            photo_sizes = sorted(photo, key=lambda x: x.get('file_size', 0))
            image_file_id = photo_sizes[-1]['file_id'] if photo_sizes else None
            has_image = True
            
            # If there's a caption, it might contain the command
            caption = message.get('caption', '')
            if caption:
                text = caption  # Use caption as the command text
        
        # Only allow admin
        if str(chat_id) != ADMIN_CHAT_ID:
            send_telegram_message(chat_id, "⛔ Access denied. You are not authorized to use this bot.")
            return
        
        # Handle commands without text (just image)
        if not text and has_image:
            send_telegram_message(chat_id, 
                "📸 Image received!\n\n"
                "To add a product with this image, send:\n"
                "/add Name | PKR Price | USD Price | Description | Instructions | WhatsApp Message\n\n"
                "Or edit a product with:\n"
                "/edit ID | Name | PKR Price | USD Price | Description | Instructions | WhatsApp Message"
            )
            return
        
        # Parse command
        if text.startswith('/start'):
            send_telegram_message(chat_id, 
                "👋 Welcome Admin!\n\n"
                "🛍️ Premium Store Admin Dashboard\n\n"
                "Available Commands:\n"
                "📦 /products - List all products\n"
                "➕ /add Name | PKR Price | USD Price | Description | Instructions | WhatsApp Message\n"
                "   *Attach image with this command*\n"
                "✏️ /edit ID | Name | PKR Price | USD Price | Description | Instructions | WhatsApp Message\n"
                "   *Attach new image to update*\n"
                "🗑️ /delete ID\n"
                "📊 /stats - Store statistics\n"
                "🖼️ /image ID - Get product image\n"
                "ℹ️ /help - Show this message\n\n"
                "🔒 Admin Only\n\n"
                "📸 *To add image:* Attach a photo with the /add or /edit command\n"
                "💰 *Price Format:* PKR first, then USD"
            )
        
        elif text.startswith('/help'):
            send_telegram_message(chat_id,
                "📚 Admin Commands Guide\n\n"
                "*Add Product with Image:*\n"
                "1. Send: `/add iPhone 15 | 350000 | 1299.99 | Latest phone | Available in colors | I want to order`\n"
                "2. *Attach a photo* with the message\n\n"
                "*Edit Product:*\n"
                "/edit 1 | New Name | 270000 | 999.99 | New description | New instructions | New message\n"
                "*Attach new image to update photo*\n\n"
                "*Delete Product:*\n"
                "/delete 1\n\n"
                "*View Image:*\n"
                "/image 1\n\n"
                "💰 *Prices:* PKR first, then USD"
            )
        
        elif text.startswith('/products'):
            if not products:
                send_telegram_message(chat_id, "📭 No products available.")
                return
            
            response = "📦 *Available Products:*\n\n"
            for p in products:
                response += f"*ID:* {p['id']}\n"
                response += f"*Name:* {p['name']}\n"
                response += f"*PKR:* Rs.{p['price_pkr']:,.0f} | *USD:* ${p['price_usd']}\n"
                response += f"*Description:* {p['description'][:50]}...\n"
                if p.get('has_image', False):
                    response += f"📸 Has Image\n"
                response += "-" * 30 + "\n"
            send_telegram_message(chat_id, response)
        
        elif text.startswith('/add'):
            process_add_product(chat_id, text, image_file_id, has_image)
        
        elif text.startswith('/edit'):
            process_edit_product(chat_id, text, image_file_id, has_image)
        
        elif text.startswith('/delete'):
            process_delete_product(chat_id, text)
        
        elif text.startswith('/image'):
            process_get_image(chat_id, text)
        
        elif text.startswith('/stats'):
            total_products = len(products)
            total_value_usd = sum([p['price_usd'] for p in products])
            total_value_pkr = sum([p['price_pkr'] for p in products])
            avg_usd = total_value_usd / total_products if total_products > 0 else 0
            avg_pkr = total_value_pkr / total_products if total_products > 0 else 0
            
            stats_text = f"📊 *Store Statistics*\n\n"
            stats_text += f"📦 Total Products: {total_products}\n"
            stats_text += f"💰 Total Value: Rs.{total_value_pkr:,.0f} | ${total_value_usd:.2f}\n"
            stats_text += f"📈 Average Price: Rs.{avg_pkr:,.0f} | ${avg_usd:.2f}\n"
            
            if total_products > 0:
                cheapest = min(products, key=lambda x: x['price_pkr'])
                expensive = max(products, key=lambda x: x['price_pkr'])
                stats_text += f"🏷️ Cheapest: {cheapest['name']} (Rs.{cheapest['price_pkr']:,.0f})\n"
                stats_text += f"💎 Most Expensive: {expensive['name']} (Rs.{expensive['price_pkr']:,.0f})"
            
            send_telegram_message(chat_id, stats_text)
        
        else:
            # Check if it's a plain image with no command
            if has_image and not text:
                send_telegram_message(chat_id, 
                    "📸 Image received!\n\n"
                    "To add a product with this image, send:\n"
                    "`/add Name | PKR Price | USD Price | Description | Instructions | WhatsApp Message`\n\n"
                    "With the image attached."
                )
            else:
                send_telegram_message(chat_id, "❌ Unknown command. Send /help for available commands.")
            
    except Exception as e:
        print(f"Error processing command: {e}")
        send_telegram_message(chat_id, f"❌ Error: {str(e)}")

def save_product_image(image_file_id, product_id):
    """Download and save product image"""
    try:
        image_data = download_telegram_file(image_file_id)
        if image_data:
            # Compress and save image
            img = Image.open(BytesIO(image_data))
            
            # Resize if too large
            max_size = (800, 800)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.LANCZOS)
            
            # Save to file
            filename = f"product_{product_id}.jpg"
            filepath = os.path.join(IMAGES_FOLDER, filename)
            img.save(filepath, 'JPEG', quality=85, optimize=True)
            
            # Convert to base64 for web display
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85, optimize=True)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return filename, img_base64
        return None, None
    except Exception as e:
        print(f"Error saving image: {e}")
        return None, None

def process_add_product(chat_id, text, image_file_id, has_image):
    """Process add product command"""
    global next_product_id
    
    try:
        # Remove /add and split by |
        command_parts = text.replace('/add', '').strip()
        parts = [p.strip() for p in command_parts.split('|')]
        
        if len(parts) < 6:
            send_telegram_message(chat_id, 
                "❌ Please provide all 6 fields separated by '|'\n\n"
                "Format: `/add Name | PKR Price | USD Price | Description | Instructions | WhatsApp Message`\n"
                "📸 Attach a photo with the command\n\n"
                "Example:\n"
                "`/add iPhone 15 | 350000 | 1299.99 | Latest phone | Available in colors | I want to order`"
            )
            return
        
        name, pkr_price_str, usd_price_str, description, instructions, whatsapp_message = parts[:6]
        price_pkr = float(pkr_price_str.replace(',', ''))
        price_usd = float(usd_price_str.replace(',', ''))
        
        # Create new product
        new_product = {
            "id": next_product_id,
            "name": name,
            "price_pkr": price_pkr,
            "price_usd": price_usd,
            "description": description,
            "instructions": instructions,
            "whatsapp_message": whatsapp_message,
            "has_image": False
        }
        
        # Save image if attached
        if has_image and image_file_id:
            filename, img_base64 = save_product_image(image_file_id, next_product_id)
            if filename and img_base64:
                new_product['image_filename'] = filename
                new_product['image_base64'] = img_base64
                new_product['has_image'] = True
                send_telegram_message(chat_id, "📸 Image saved successfully!")
        
        products.append(new_product)
        save_products(products)
        next_product_id += 1
        
        response = f"✅ *Product Added Successfully!*\n\n"
        response += f"📦 Name: {name}\n"
        response += f"💰 PKR: Rs.{price_pkr:,.0f} | USD: ${price_usd}\n"
        response += f"🆔 ID: {new_product['id']}\n"
        if new_product.get('has_image', False):
            response += f"📸 Image: Yes\n"
        response += f"\n🔗 Website updated automatically!"
        
        send_telegram_message(chat_id, response)
        
    except ValueError as e:
        send_telegram_message(chat_id, f"❌ Invalid price format. Please enter valid numbers. Error: {e}")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error adding product: {str(e)}")

def process_edit_product(chat_id, text, image_file_id, has_image):
    """Process edit product command"""
    try:
        # Remove /edit and split by |
        command_parts = text.replace('/edit', '').strip()
        parts = [p.strip() for p in command_parts.split('|')]
        
        if len(parts) < 7:
            send_telegram_message(chat_id, 
                "❌ Please provide ID and all 6 fields separated by '|'\n\n"
                "Format: `/edit ID | Name | PKR Price | USD Price | Description | Instructions | WhatsApp Message`\n"
                "📸 Attach new image to update photo\n\n"
                "Example:\n"
                "`/edit 1 | iPhone 15 Pro | 350000 | 1299.99 | Latest phone | Available in colors | I want to order`"
            )
            return
        
        product_id = int(parts[0])
        name, pkr_price_str, usd_price_str, description, instructions, whatsapp_message = parts[1:7]
        price_pkr = float(pkr_price_str.replace(',', ''))
        price_usd = float(usd_price_str.replace(',', ''))
        
        # Find and update product
        for p in products:
            if p['id'] == product_id:
                p['name'] = name
                p['price_pkr'] = price_pkr
                p['price_usd'] = price_usd
                p['description'] = description
                p['instructions'] = instructions
                p['whatsapp_message'] = whatsapp_message
                
                # Update image if new one is attached
                if has_image and image_file_id:
                    filename, img_base64 = save_product_image(image_file_id, product_id)
                    if filename and img_base64:
                        # Delete old image if exists
                        if p.get('image_filename'):
                            try:
                                os.remove(os.path.join(IMAGES_FOLDER, p['image_filename']))
                            except:
                                pass
                        
                        p['image_filename'] = filename
                        p['image_base64'] = img_base64
                        p['has_image'] = True
                        send_telegram_message(chat_id, "📸 Image updated successfully!")
                
                save_products(products)
                
                response = f"✅ *Product Updated Successfully!*\n\n"
                response += f"🆔 ID: {product_id}\n"
                response += f"📦 Name: {name}\n"
                response += f"💰 PKR: Rs.{price_pkr:,.0f} | USD: ${price_usd}\n"
                if p.get('has_image', False):
                    response += f"📸 Has Image\n"
                
                send_telegram_message(chat_id, response)
                return
        
        send_telegram_message(chat_id, f"❌ Product with ID {product_id} not found.")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Invalid price format or ID. Please check your input.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error updating product: {str(e)}")

def process_delete_product(chat_id, text):
    """Process delete product command"""
    try:
        product_id = int(text.replace('/delete', '').strip())
        
        for i, p in enumerate(products):
            if p['id'] == product_id:
                removed_product = products.pop(i)
                
                # Remove image file if exists
                if p.get('image_filename'):
                    try:
                        os.remove(os.path.join(IMAGES_FOLDER, p['image_filename']))
                    except:
                        pass
                
                save_products(products)
                send_telegram_message(chat_id,
                    f"✅ *Product Deleted Successfully!*\n\n"
                    f"📦 Name: {removed_product['name']}\n"
                    f"🆔 ID: {removed_product['id']}"
                )
                return
        
        send_telegram_message(chat_id, f"❌ Product with ID {product_id} not found.")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Please provide a valid product ID (number).")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error deleting product: {str(e)}")

def process_get_image(chat_id, text):
    """Process get image command"""
    try:
        product_id = int(text.replace('/image', '').strip())
        
        for p in products:
            if p['id'] == product_id:
                if p.get('has_image', False) and p.get('image_filename'):
                    # Send the image file
                    filepath = os.path.join(IMAGES_FOLDER, p['image_filename'])
                    if os.path.exists(filepath):
                        with open(filepath, 'rb') as f:
                            # Upload to Telegram
                            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                            files = {'photo': f}
                            data = {'chat_id': chat_id}
                            response = requests.post(url, files=files, data=data)
                            return
                
                send_telegram_message(chat_id, f"❌ No image found for product {product_id}")
                return
        
        send_telegram_message(chat_id, f"❌ Product with ID {product_id} not found.")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Please provide a valid product ID (number).")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {str(e)}")

# ============================================
# START BOT IN BACKGROUND (FIX FOR RENDER)
# ============================================

def run_telegram_bot():
    """Run the Telegram bot using polling"""
    print("🤖 Starting Telegram bot...")
    last_update_id = 0
    
    while True:
        try:
            updates = get_telegram_updates(last_update_id + 1 if last_update_id else None)
            
            for update in updates:
                if 'message' in update:
                    print(f"📩 Received message: {update['message'].get('text', 'No text')}")
                    process_telegram_command(update)
                    last_update_id = update['update_id']
            
            time.sleep(2)  # Short delay to prevent excessive CPU usage
            
        except Exception as e:
            print(f"❌ Bot error: {e}")
            time.sleep(10)

# Start the bot in a background thread when the app starts
bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
bot_thread.start()
print("✅ Bot thread started")

# ============================================
# START FLASK APP
# ============================================

if __name__ == "__main__":
    print("🚀 Starting Flask app...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
