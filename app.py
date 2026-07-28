# ============================================
# COMPLETE STORE SCRIPT - FIXED GLOBAL SCOPE
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

# ============================================
# SETUP LOGGING
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# FILE STORAGE - USING /tmp (Works on Render Free)
# ============================================

# Use /tmp directory (works on Render free tier)
BASE_DIR = "/tmp/premium_store"
os.makedirs(BASE_DIR, exist_ok=True)

PRODUCTS_FILE = os.path.join(BASE_DIR, "products.json")
IMAGES_FOLDER = os.path.join(BASE_DIR, "product_images")
os.makedirs(IMAGES_FOLDER, exist_ok=True)

logger.info(f"📁 Storage directory: {BASE_DIR}")
logger.info(f"📁 Products file: {PRODUCTS_FILE}")
logger.info(f"📁 Images folder: {IMAGES_FOLDER}")

# ============================================
# GLOBAL PRODUCTS VARIABLE
# ============================================

# This is the CRITICAL fix - products must be global
products = []
next_product_id = 1

def load_products():
    """Load products from JSON file with detailed logging"""
    global products, next_product_id
    
    try:
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, 'r') as f:
                products = json.load(f)
                if products:
                    next_product_id = max([p["id"] for p in products]) + 1
                else:
                    next_product_id = 1
                logger.info(f"✅ Loaded {len(products)} products from {PRODUCTS_FILE}")
                logger.info(f"🆔 Next product ID: {next_product_id}")
                return products
        else:
            logger.info(f"📭 No products file found at {PRODUCTS_FILE}, starting empty")
            products = []
            next_product_id = 1
            return []
    except Exception as e:
        logger.error(f"❌ Error loading products: {e}")
        products = []
        next_product_id = 1
        return []

def save_products():
    """Save products to JSON file with detailed logging"""
    global products
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(PRODUCTS_FILE), exist_ok=True)
        
        with open(PRODUCTS_FILE, 'w') as f:
            json.dump(products, f, indent=2)
        
        logger.info(f"✅ Saved {len(products)} products to {PRODUCTS_FILE}")
        
        # Verify save worked
        if os.path.exists(PRODUCTS_FILE):
            file_size = os.path.getsize(PRODUCTS_FILE)
            logger.info(f"📄 File size: {file_size} bytes")
            
            # Log first product for debugging
            if products:
                logger.info(f"📦 First product: {products[0].get('name', 'Unknown')}")
            
            return True
        else:
            logger.error("❌ File not found after save!")
            return False
    except Exception as e:
        logger.error(f"❌ Error saving products: {e}")
        return False

# Load products on startup
load_products()

# ============================================
# FLASK WEB APP
# ============================================

app = Flask(__name__)

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>🛒 Premium Store</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; min-height: 100vh; padding: 0; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 100; }
        .header-content { max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .header h1 { color: white; font-size: 1.8em; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
        .header h1 span { font-weight: 300; font-size: 0.6em; opacity: 0.8; display: block; }
        .header-stats { color: white; background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 30px; backdrop-filter: blur(10px); font-size: 0.85em; white-space: nowrap; }
        .header-stats strong { font-size: 1.2em; }
        .container { max-width: 1400px; margin: 0 auto; padding: 15px 10px; }
        .controls { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; background: white; padding: 12px 18px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .controls .count { color: #555; font-size: 0.9em; }
        .controls .count strong { color: #667eea; font-size: 1.1em; }
        .controls input { padding: 8px 16px; border: 2px solid #e0e0e0; border-radius: 25px; font-size: 0.9em; width: 200px; transition: all 0.3s ease; outline: none; }
        .controls input:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .products-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; animation: fadeIn 0.5s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .product-card { background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 2px 15px rgba(0,0,0,0.06); transition: all 0.3s ease; display: flex; flex-direction: column; position: relative; }
        .product-card:hover { transform: translateY(-5px); box-shadow: 0 8px 30px rgba(0,0,0,0.12); }
        .product-image-container { position: relative; height: 200px; overflow: hidden; background: #f8f9fa; }
        .product-image { width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s ease; }
        .product-card:hover .product-image { transform: scale(1.05); }
        .product-image-placeholder { width: 100%; height: 100%; background: linear-gradient(135deg, #e0e0e0 0%, #f0f0f0 100%); display: flex; align-items: center; justify-content: center; font-size: 3em; color: #999; }
        .product-badge { position: absolute; top: 10px; right: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.7em; font-weight: 600; box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3); letter-spacing: 0.5px; text-transform: uppercase; }
        .product-content { padding: 14px 16px 18px; flex: 1; display: flex; flex-direction: column; }
        .product-name { font-size: 1.05em; font-weight: 700; color: #1a1a2e; margin-bottom: 6px; line-height: 1.3; min-height: 2.6em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .product-prices { display: flex; align-items: baseline; gap: 8px; margin: 6px 0 10px; flex-wrap: wrap; }
        .product-price-pkr { font-size: 1.5em; font-weight: 800; color: #667eea; }
        .product-price-pkr::before { content: 'Rs. '; font-weight: 600; }
        .product-price-usd { font-size: 0.85em; color: #888; font-weight: 500; }
        .product-price-usd::before { content: '$'; }
        .product-description { color: #555; font-size: 0.82em; line-height: 1.5; margin: 6px 0 10px; flex: 1; min-height: 2.8em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .product-instructions { background: #f8f9fa; padding: 8px 12px; border-radius: 8px; font-size: 0.78em; color: #666; margin: 6px 0 12px; border-left: 3px solid #667eea; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .product-instructions::before { content: '📋 '; }
        .buy-btn { background: #25D366; color: white; border: none; padding: 12px 16px; border-radius: 50px; font-size: 0.9em; font-weight: 700; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: auto; box-shadow: 0 4px 15px rgba(37, 211, 102, 0.25); }
        .buy-btn:hover { transform: scale(1.02); box-shadow: 0 6px 25px rgba(37, 211, 102, 0.35); background: #20b85f; }
        .buy-btn::before { content: '💬'; font-size: 1em; }
        .empty-message { grid-column: 1 / -1; text-align: center; padding: 60px 20px; background: white; border-radius: 20px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }
        .empty-message .icon { font-size: 3em; margin-bottom: 15px; display: block; }
        .empty-message h2 { color: #333; font-size: 1.3em; margin-bottom: 8px; }
        .empty-message p { color: #888; font-size: 0.95em; }
        .footer { text-align: center; padding: 20px 15px; color: #888; font-size: 0.8em; margin-top: 15px; border-top: 1px solid #e0e0e0; }
        
        @media (max-width: 768px) {
            .header h1 { font-size: 1.3em; }
            .header h1 span { font-size: 0.55em; }
            .header-stats { font-size: 0.7em; padding: 6px 12px; }
            .controls { flex-direction: row; flex-wrap: wrap; padding: 10px 14px; }
            .controls .count { font-size: 0.8em; }
            .controls input { width: 140px; font-size: 0.8em; padding: 6px 14px; }
            .products-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
            .product-image-container { height: 150px; }
            .product-content { padding: 10px 12px 14px; }
            .product-name { font-size: 0.9em; min-height: 2.2em; }
            .product-price-pkr { font-size: 1.2em; }
            .product-price-usd { font-size: 0.75em; }
            .product-description { font-size: 0.75em; min-height: 2.4em; }
            .product-instructions { font-size: 0.7em; padding: 6px 10px; }
            .buy-btn { font-size: 0.8em; padding: 10px 12px; }
            .product-badge { font-size: 0.6em; padding: 3px 10px; top: 8px; right: 8px; }
            .product-image-placeholder { font-size: 2em; }
        }
        @media (max-width: 400px) {
            .products-grid { gap: 8px; }
            .product-image-container { height: 120px; }
            .product-name { font-size: 0.8em; }
            .product-price-pkr { font-size: 1em; }
            .product-description { font-size: 0.7em; }
            .product-instructions { font-size: 0.65em; padding: 4px 8px; }
            .buy-btn { font-size: 0.7em; padding: 8px 10px; }
            .controls input { width: 100px; font-size: 0.7em; }
        }
        @media (min-width: 769px) and (max-width: 1024px) {
            .products-grid { grid-template-columns: repeat(2, 1fr); gap: 20px; }
            .product-image-container { height: 220px; }
        }
        @media (min-width: 1025px) {
            .products-grid { grid-template-columns: repeat(3, 1fr); gap: 25px; }
            .product-image-container { height: 250px; }
            .header h1 { font-size: 2.2em; }
            .container { padding: 25px 20px; }
        }
        @media (min-width: 1400px) {
            .products-grid { gap: 30px; }
            .product-image-container { height: 280px; }
        }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #f0f2f5; }
        ::-webkit-scrollbar-thumb { background: #667eea; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #764ba2; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>🛒 Premium Store <span>Quality Products at Best Prices</span></h1>
            <div class="header-stats">📦 <strong>{{ products|length }}</strong> Products</div>
        </div>
    </div>
    <div class="container">
        <div class="controls">
            <div class="count">Showing <strong>{{ products|length }}</strong> products</div>
            <input type="text" id="searchInput" placeholder="🔍 Search..." onkeyup="filterProducts()">
        </div>
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
                        <a href="https://wa.me/{{ whatsapp_number }}?text={{ product.whatsapp_message | urlencode }}" target="_blank" class="buy-btn">Buy Now</a>
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
        <div class="footer"><p>🏪 Powered by Telegram Bot | Admin Dashboard Available</p></div>
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
    global products
    logger.info(f"🏠 Home page requested - {len(products)} products available")
    return render_template_string(
        HTML_TEMPLATE,
        products=products,
        whatsapp_number=WHATSAPP_NUMBER
    )

@app.route('/api/products')
def api_products():
    global products
    logger.info(f"📡 API products requested - {len(products)} products")
    return jsonify(products)

@app.route('/images/<filename>')
def get_image(filename):
    try:
        return send_file(os.path.join(IMAGES_FOLDER, filename))
    except:
        return "Image not found", 404

@app.route('/debug')
def debug():
    """Debug endpoint to check storage"""
    global products
    info = {
        "base_dir": BASE_DIR,
        "products_file": PRODUCTS_FILE,
        "file_exists": os.path.exists(PRODUCTS_FILE),
        "products_count": len(products),
        "products": products,
        "images_folder": IMAGES_FOLDER,
        "images_exist": os.path.exists(IMAGES_FOLDER)
    }
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'r') as f:
            info["file_content"] = json.load(f)
    return jsonify(info)

# ============================================
# TELEGRAM BOT FUNCTIONS
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
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"📤 Sent message to {chat_id}: {text[:50]}...")
        return response.json()
    except Exception as e:
        logger.error(f"❌ Error sending Telegram message: {e}")
        return None

def download_telegram_file(file_id):
    """Download a file from Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
        response = requests.get(url, params={'file_id': file_id}, timeout=10)
        file_info = response.json()
        
        if not file_info.get('ok'):
            logger.error(f"❌ Failed to get file info: {file_info}")
            return None
        
        file_path = file_info['result']['file_path']
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        
        response = requests.get(file_url, timeout=30)
        logger.info(f"📥 Downloaded file from Telegram: {file_path}")
        return response.content
    except Exception as e:
        logger.error(f"❌ Error downloading file: {e}")
        return None

def get_telegram_updates(offset=None):
    """Get updates from Telegram Bot API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    try:
        response = requests.get(url, params=params, timeout=35)
        result = response.json().get('result', [])
        if result:
            logger.info(f"📩 Received {len(result)} update(s)")
        return result
    except Exception as e:
        logger.error(f"❌ Error getting updates: {e}")
        return []

def process_telegram_command(update):
    """Process incoming Telegram commands"""
    try:
        message = update.get('message', {})
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        logger.info(f"📩 Processing message from {chat_id}: {text[:50]}")
        
        # Check for photo attachment
        photo = message.get('photo')
        has_image = False
        image_file_id = None
        
        if photo:
            photo_sizes = sorted(photo, key=lambda x: x.get('file_size', 0))
            image_file_id = photo_sizes[-1]['file_id'] if photo_sizes else None
            has_image = True
            caption = message.get('caption', '')
            if caption:
                text = caption
                logger.info(f"📸 Message has image with caption: {text[:50]}")
        
        # Only allow admin
        if str(chat_id) != ADMIN_CHAT_ID:
            logger.warning(f"⛔ Unauthorized access attempt from {chat_id}")
            send_telegram_message(chat_id, "⛔ Access denied. You are not authorized to use this bot.")
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
            logger.info(f"✅ Sent /start response to {chat_id}")
        
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
        
        else:
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
        logger.error(f"❌ Error processing command: {e}")
        send_telegram_message(chat_id, f"❌ Error: {str(e)}")

def save_product_image(image_file_id, product_id):
    """Download and save product image"""
    try:
        image_data = download_telegram_file(image_file_id)
        if image_data:
            img = Image.open(BytesIO(image_data))
            
            max_size = (800, 800)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.LANCZOS)
            
            filename = f"product_{product_id}.jpg"
            filepath = os.path.join(IMAGES_FOLDER, filename)
            img.save(filepath, 'JPEG', quality=85, optimize=True)
            
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85, optimize=True)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            logger.info(f"📸 Saved image for product {product_id}: {filepath}")
            return filename, img_base64
        return None, None
    except Exception as e:
        logger.error(f"❌ Error saving image: {e}")
        return None, None

def process_add_product(chat_id, text, image_file_id, has_image):
    """Process add product command - FIXED with global"""
    global products, next_product_id
    
    try:
        logger.info(f"➕ Adding product from: {text[:100]}")
        logger.info(f"📊 Current products count before add: {len(products)}")
        
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
                logger.info(f"📸 Image attached to product {next_product_id}")
        
        # Add to global products list
        products.append(new_product)
        next_product_id += 1
        
        # Save to file
        save_success = save_products()
        
        if save_success:
            logger.info(f"✅ Product added successfully: {name} (ID: {new_product['id']})")
            logger.info(f"📊 Products count after add: {len(products)}")
            
            response = f"✅ *Product Added Successfully!*\n\n"
            response += f"📦 Name: {name}\n"
            response += f"💰 PKR: Rs.{price_pkr:,.0f} | USD: ${price_usd}\n"
            response += f"🆔 ID: {new_product['id']}\n"
            if new_product.get('has_image', False):
                response += f"📸 Image: Yes\n"
            response += f"\n🔗 Website updated automatically!"
            
            send_telegram_message(chat_id, response)
            
            # Log the current products for debugging
            logger.info(f"📋 Current products: {[p['name'] for p in products]}")
        else:
            logger.error("❌ Failed to save product to file")
            send_telegram_message(chat_id, "❌ Failed to save product. Please try again.")
        
    except ValueError as e:
        logger.error(f"❌ Invalid price format: {e}")
        send_telegram_message(chat_id, f"❌ Invalid price format. Please enter valid numbers. Error: {e}")
    except Exception as e:
        logger.error(f"❌ Error adding product: {e}")
        send_telegram_message(chat_id, f"❌ Error adding product: {str(e)}")

def process_edit_product(chat_id, text, image_file_id, has_image):
    """Process edit product command"""
    global products
    
    try:
        logger.info(f"✏️ Editing product from: {text[:100]}")
        
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
                
                if has_image and image_file_id:
                    filename, img_base64 = save_product_image(image_file_id, product_id)
                    if filename and img_base64:
                        if p.get('image_filename'):
                            try:
                                os.remove(os.path.join(IMAGES_FOLDER, p['image_filename']))
                            except:
                                pass
                        p['image_filename'] = filename
                        p['image_base64'] = img_base64
                        p['has_image'] = True
                        logger.info(f"📸 Image updated for product {product_id}")
                
                save_success = save_products()
                
                if save_success:
                    logger.info(f"✅ Product updated successfully: {name} (ID: {product_id})")
                    response = f"✅ *Product Updated Successfully!*\n\n"
                    response += f"🆔 ID: {product_id}\n"
                    response += f"📦 Name: {name}\n"
                    response += f"💰 PKR: Rs.{price_pkr:,.0f} | USD: ${price_usd}\n"
                    if p.get('has_image', False):
                        response += f"📸 Has Image\n"
                    send_telegram_message(chat_id, response)
                else:
                    send_telegram_message(chat_id, "❌ Failed to save product. Please try again.")
                return
        
        send_telegram_message(chat_id, f"❌ Product with ID {product_id} not found.")
        
    except ValueError as e:
        logger.error(f"❌ Invalid input: {e}")
        send_telegram_message(chat_id, "❌ Invalid price format or ID. Please check your input.")
    except Exception as e:
        logger.error(f"❌ Error updating product: {e}")
        send_telegram_message(chat_id, f"❌ Error updating product: {str(e)}")

def process_delete_product(chat_id, text):
    """Process delete product command"""
    global products
    
    try:
        product_id = int(text.replace('/delete', '').strip())
        logger.info(f"🗑️ Deleting product ID: {product_id}")
        
        for i, p in enumerate(products):
            if p['id'] == product_id:
                removed_product = products.pop(i)
                
                if p.get('image_filename'):
                    try:
                        os.remove(os.path.join(IMAGES_FOLDER, p['image_filename']))
                        logger.info(f"🗑️ Deleted image for product {product_id}")
                    except:
                        pass
                
                save_success = save_products()
                
                if save_success:
                    logger.info(f"✅ Product deleted successfully: {removed_product['name']} (ID: {product_id})")
                    send_telegram_message(chat_id,
                        f"✅ *Product Deleted Successfully!*\n\n"
                        f"📦 Name: {removed_product['name']}\n"
                        f"🆔 ID: {removed_product['id']}"
                    )
                else:
                    send_telegram_message(chat_id, "❌ Failed to save product. Please try again.")
                return
        
        send_telegram_message(chat_id, f"❌ Product with ID {product_id} not found.")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Please provide a valid product ID (number).")
    except Exception as e:
        logger.error(f"❌ Error deleting product: {e}")
        send_telegram_message(chat_id, f"❌ Error deleting product: {str(e)}")

def process_get_image(chat_id, text):
    """Process get image command"""
    try:
        product_id = int(text.replace('/image', '').strip())
        logger.info(f"🖼️ Getting image for product ID: {product_id}")
        
        for p in products:
            if p['id'] == product_id:
                if p.get('has_image', False) and p.get('image_filename'):
                    filepath = os.path.join(IMAGES_FOLDER, p['image_filename'])
                    if os.path.exists(filepath):
                        with open(filepath, 'rb') as f:
                            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                            files = {'photo': f}
                            data = {'chat_id': chat_id}
                            response = requests.post(url, files=files, data=data)
                            logger.info(f"📸 Sent image for product {product_id}")
                            return
                
                send_telegram_message(chat_id, f"❌ No image found for product {product_id}")
                return
        
        send_telegram_message(chat_id, f"❌ Product with ID {product_id} not found.")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Please provide a valid product ID (number).")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        send_telegram_message(chat_id, f"❌ Error: {str(e)}")

# ============================================
# START BOT IN BACKGROUND
# ============================================

def run_telegram_bot():
    """Run the Telegram bot using polling"""
    logger.info("🤖 Starting Telegram bot...")
    last_update_id = 0
    retry_count = 0
    
    while True:
        try:
            # Test connection every 60 seconds
            if retry_count % 30 == 0:
                test_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
                test_response = requests.get(test_url, timeout=10)
                if test_response.ok:
                    bot_info = test_response.json()['result']
                    logger.info(f"✅ Bot connected: @{bot_info['username']}")
                else:
                    logger.warning(f"⚠️ Bot connection test failed: {test_response.text}")
            
            updates = get_telegram_updates(last_update_id + 1 if last_update_id else None)
            
            if updates:
                for update in updates:
                    if 'message' in update:
                        process_telegram_command(update)
                        last_update_id = update['update_id']
                retry_count = 0
            else:
                if retry_count % 60 == 0:  # Log every 60 attempts
                    logger.info("⏳ Waiting for messages...")
            
            time.sleep(2)
            retry_count += 1
            
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
            time.sleep(10)

# ============================================
# ADD TEST PRODUCTS
# ============================================

def add_test_products():
    """Add test products if none exist"""
    global products, next_product_id
    
    if not products:
        logger.info("📦 No products found, adding test products...")
        test_products = [
            {
                "id": 1,
                "name": "Cordless Drill Kit",
                "price_pkr": 8500,
                "price_usd": 75.99,
                "description": "Professional grade drill with 2 batteries",
                "instructions": "Free delivery within 3 days",
                "whatsapp_message": "I want to order the Cordless Drill Kit",
                "has_image": False
            },
            {
                "id": 2,
                "name": "Digital Multimeter",
                "price_pkr": 3500,
                "price_usd": 29.99,
                "description": "Accurate measurements for professionals",
                "instructions": "Includes testing leads and manual",
                "whatsapp_message": "I want to order the Digital Multimeter",
                "has_image": False
            }
        ]
        products = test_products
        if save_products():
            next_product_id = max([p["id"] for p in products]) + 1
            logger.info(f"✅ Added {len(products)} test products")
        else:
            logger.error("❌ Failed to save test products")

# ============================================
# START APPLICATION
# ============================================

# Add test products
add_test_products()

# Start bot thread
try:
    logger.info("🚀 Starting bot thread...")
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot thread started successfully")
except Exception as e:
    logger.error(f"❌ Failed to start bot thread: {e}")

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    logger.info("🚀 Starting Flask app...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
