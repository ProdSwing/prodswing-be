const express = require('express');
const mysql = require('mysql2');
require('dotenv').config();

const app = express();
app.use(express.json());

const db = mysql.createConnection({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
});

db.connect(err => {
  if (err) throw err;
  console.log('Connected to database');
});

app.get('/products', (req, res) => {
  db.query('SELECT * FROM products', (err, results) => {
    if (err) throw err;
    res.json(results);
  });
});

app.get('/products/:id', (req, res) => {
  const { id } = req.params;
  db.query('SELECT * FROM products WHERE productID = ?', [id], (err, result) => {
    if (err) throw err;
    res.json(result[0]);
  });
});

app.post('/products', (req, res) => {
  const { productName, category, description, price, review } = req.body;
  db.query('INSERT INTO products (productName, category, description, price, review) VALUES (?, ?, ?, ?, ?)',
    [productName, category, description, price, review],
    (err, result) => {
      if (err) throw err;
      res.json({ id: result.insertId });
    });
});

app.put('/products/:id', (req, res) => {
  const { id } = req.params;
  const { productName, category, description, price, review } = req.body;
  db.query('UPDATE products SET productName = ?, category = ?, description = ?, price = ?, review = ? WHERE productID = ?',
    [productName, category, description, price, review, id],
    (err, result) => {
      if (err) throw err;
      res.send('Product updated');
    });
});

app.delete('/products/:id', (req, res) => {
  const { id } = req.params;
  db.query('DELETE FROM products WHERE productID = ?', [id], (err, result) => {
    if (err) throw err;
    res.send('Product deleted');
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
