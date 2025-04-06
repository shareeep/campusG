import Database from 'better-sqlite3';
import { join } from 'path';

// Initialize database
const db = new Database(join(process.cwd(), 'campus-g.db'));

// Create tables if they don't exist
db.exec(`
  -- Create order status enum table
  CREATE TABLE IF NOT EXISTS order_status (
    value TEXT PRIMARY KEY
  );

  -- Insert order status values if not exists
  INSERT OR IGNORE INTO order_status (value) VALUES
    ('pending'),
    ('accepted'),
    ('picked_up'),
    ('delivered');

  -- Create payment status enum table
  CREATE TABLE IF NOT EXISTS payment_status (
    value TEXT PRIMARY KEY
  );

  -- Insert payment status values if not exists
  INSERT OR IGNORE INTO payment_status (value) VALUES
    ('pending'),
    ('held'),
    ('released');

  -- Create orders table
  CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    order_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    runner_id TEXT,
    status TEXT NOT NULL REFERENCES order_status(value),
    payment_status TEXT NOT NULL REFERENCES payment_status(value),
    store_name TEXT NOT NULL,
    store_postal_code TEXT NOT NULL,
    delivery_building TEXT NOT NULL,
    delivery_level TEXT NOT NULL,
    delivery_room TEXT NOT NULL,
    delivery_school TEXT NOT NULL,
    delivery_meeting_point TEXT,
    delivery_fee REAL NOT NULL,
    total REAL NOT NULL,
    instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- Create order items table
  CREATE TABLE IF NOT EXISTS order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id),
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- Create users table
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT CHECK (role IN ('customer', 'runner')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

// Prepare statements
const statements = {
  // Orders
  createOrder: db.prepare(`
    INSERT INTO orders (
      id, order_id, user_id, status, payment_status,
      store_name, store_postal_code,
      delivery_building, delivery_level, delivery_room, delivery_school,
      delivery_meeting_point, delivery_fee, total, instructions
    ) VALUES (
      ?, ?, ?, 'pending', 'pending',
      ?, ?,
      ?, ?, ?, ?,
      ?, ?, ?, ?
    )
  `),
  
  getOrder: db.prepare('SELECT * FROM orders WHERE order_id = ?'),
  
  updateOrderStatus: db.prepare(`
    UPDATE orders 
    SET status = ?, updated_at = CURRENT_TIMESTAMP 
    WHERE order_id = ?
  `),
  
  updatePaymentStatus: db.prepare(`
    UPDATE orders 
    SET payment_status = ?, updated_at = CURRENT_TIMESTAMP 
    WHERE order_id = ?
  `),
  
  acceptOrder: db.prepare(`
    UPDATE orders 
    SET runner_id = ?, status = 'accepted', updated_at = CURRENT_TIMESTAMP 
    WHERE order_id = ? AND status = 'pending'
  `),

  // Order Items
  createOrderItem: db.prepare(`
    INSERT INTO order_items (id, order_id, name, quantity, price)
    VALUES (?, ?, ?, ?, ?)
  `),

  getOrderItems: db.prepare('SELECT * FROM order_items WHERE order_id = ?'),

  // Queries
  getAvailableOrders: db.prepare(`
    SELECT * FROM orders 
    WHERE status = 'pending' 
    ORDER BY created_at DESC
  `),

  getActiveOrders: db.prepare(`
    SELECT * FROM orders 
    WHERE runner_id = ? AND status IN ('accepted', 'picked_up')
    ORDER BY created_at DESC
  `),

  getUserOrders: db.prepare(`
    SELECT * FROM orders 
    WHERE user_id = ?
    ORDER BY created_at DESC
  `)
};

export { db, statements };