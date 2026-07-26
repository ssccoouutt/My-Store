// app/page.js
import { sql } from '@vercel/postgres';
import { revalidatePath } from 'next/cache';

// ============ CONFIGURATION (HARDCODED) ============
const BOT_TOKEN = '8898921110:AAFGHyoOkhpo8lC1UbbA7SyaMWSd1qmFNcE';
const ADMIN_CHAT_ID = '990321391';
const WHATSAPP_NUMBER = '923400315734';

// ============ DATABASE FUNCTIONS ============
async function initDb() {
  await sql`
    CREATE TABLE IF NOT EXISTS products (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      price DECIMAL(10,2) NOT NULL,
      description TEXT,
      instructions TEXT,
      whatsapp_text TEXT,
      image_url TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `;
}

async function getProducts() {
  await initDb();
  const { rows } = await sql`SELECT * FROM products ORDER BY id DESC`;
  return rows;
}

async function addProduct(name, price, description, instructions, whatsappText, imageUrl) {
  const { rows } = await sql`
    INSERT INTO products (name, price, description, instructions, whatsapp_text, image_url)
    VALUES (${name}, ${price}, ${description}, ${instructions}, ${whatsappText}, ${imageUrl})
    RETURNING *
  `;
  return rows[0];
}

async function deleteProduct(id) {
  await sql`DELETE FROM products WHERE id = ${id}`;
}

// ============ TELEGRAM HANDLER ============
async function handleTelegramMessage(message) {
  const chatId = message.chat.id;
  const text = message.text;
  
  if (chatId.toString() !== ADMIN_CHAT_ID) return;

  const sendMessage = async (msg) => {
    await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text: msg,
        parse_mode: 'Markdown'
      })
    });
  };

  if (text === '/start' || text === '/help') {
    await sendMessage(`
🤖 *Store Admin Bot*
/add - Add product
/list - List products
/del [id] - Delete product
    `);
  }

  if (text === '/list') {
    const products = await getProducts();
    if (products.length === 0) {
      await sendMessage('📭 No products found.');
      return;
    }
    let list = '📋 *Products:*\n\n';
    products.forEach(p => {
      list += `*${p.id}.* ${p.name} - $${p.price}\n`;
    });
    await sendMessage(list);
  }

  if (text.startsWith('/add ')) {
    try {
      const parts = text.replace('/add ', '').split('|').map(s => s.trim());
      if (parts.length !== 6) throw new Error('Need 6 fields: Name|Price|Description|Instructions|WhatsApp Text|Image URL');
      
      const [name, price, description, instructions, whatsappText, imageUrl] = parts;
      const product = await addProduct(name, parseFloat(price), description, instructions, whatsappText, imageUrl);
      await sendMessage(`✅ Added! ID: ${product.id}\n${name} - $${price}`);
    } catch (error) {
      await sendMessage(`❌ Error: ${error.message}`);
    }
  }

  if (text.startsWith('/del ')) {
    const id = parseInt(text.replace('/del ', ''));
    if (isNaN(id)) {
      await sendMessage('❌ Use: /del [id]');
      return;
    }
    try {
      await deleteProduct(id);
      await sendMessage(`✅ Product #${id} deleted.`);
    } catch (error) {
      await sendMessage(`❌ Error: ${error.message}`);
    }
  }
}

// ============ MAIN PAGE COMPONENT ============
export default async function Home() {
  const products = await getProducts();

  return (
    <html>
      <head>
        <title>🛍️ My Store</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body className="bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          <h1 className="text-4xl font-bold text-center mb-8">🛍️ Our Store</h1>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {products.map((product) => (
              <div key={product.id} className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition">
                <div className="h-48 bg-gradient-to-r from-blue-100 to-purple-100 flex items-center justify-center">
                  {product.image_url ? (
                    <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-gray-400 text-lg">📦 No Image</span>
                  )}
                </div>
                <div className="p-6">
                  <h2 className="text-xl font-semibold mb-2">{product.name}</h2>
                  <p className="text-2xl font-bold text-green-600 mb-2">${product.price}</p>
                  <p className="text-gray-600 mb-2">{product.description}</p>
                  <p className="text-sm text-gray-500 mb-4">📋 {product.instructions}</p>
                  
                  <a
                    href={`https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(
                      product.whatsapp_text || `I want to buy ${product.name} for $${product.price}`
                    )}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-4 rounded-lg text-center transition"
                  >
                    💬 Buy on WhatsApp
                  </a>
                </div>
              </div>
            ))}
          </div>

          {products.length === 0 && (
            <div className="text-center text-gray-500 py-12">
              <p className="text-xl">No products yet.</p>
              <p className="mt-2">Add products via Telegram bot.</p>
            </div>
          )}
        </div>
      </body>
    </html>
  );
}

// ============ API ROUTE FOR TELEGRAM WEBHOOK ============
export async function POST(request) {
  try {
    const body = await request.json();
    if (body.message) {
      await handleTelegramMessage(body.message);
    }
    return new Response('OK', { status: 200 });
  } catch (error) {
    return new Response('Error', { status: 500 });
  }
}
