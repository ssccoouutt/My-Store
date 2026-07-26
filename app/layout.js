// app/layout.js
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <title>🛍️ My Store</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body>{children}</body>
    </html>
  );
}
