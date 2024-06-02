const express = require('express');
const mysql = require('mysql2');
const multer = require('multer');
const { Storage } = require('@google-cloud/storage');
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

const storage = new Storage();
const bucketName = process.env.GCLOUD_STORAGE_BUCKET;
const bucket = storage.bucket(bucketName);

const upload = multer({
  storage: multer.memoryStorage(),
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

app.get('/product-images', (req, res) => {
  db.query('SELECT * FROM productImage', (err, results) => {
    if (err) throw err;
    res.json(results);
  });
});

app.get('/product-images/:id', (req, res) => {
  const { id } = req.params;
  db.query('SELECT * FROM productImage WHERE productID = ?', [id], (err, result) => {
    if (err) throw err;
    res.json(result);
  });
});

app.post('/product-images', upload.single('image'), (req, res) => {
  const { productID } = req.body;
  const file = req.file;
  const blob = bucket.file(file.originalname);
  const blobStream = blob.createWriteStream();

  blobStream.on('error', err => {
    res.status(500).send(err);
  });

  blobStream.on('finish', () => {
    const publicUrl = `https://storage.googleapis.com/${bucketName}/${blob.name}`;
    db.query('INSERT INTO productImage (productID, imageURL) VALUES (?, ?)', [productID, publicUrl], (err, result) => {
      if (err) throw err;
      res.json({ id: result.insertId, imageURL: publicUrl });
    });
  });

  blobStream.end(file.buffer);
});

app.put('/product-images/:id', upload.single('image'), (req, res) => {
  const { id } = req.params;
  const { productID } = req.body;
  const file = req.file;
  const blob = bucket.file(file.originalname);
  const blobStream = blob.createWriteStream();

  blobStream.on('error', err => {
    res.status(500).send(err);
  });

  blobStream.on('finish', () => {
    const publicUrl = `https://storage.googleapis.com/${bucketName}/${blob.name}`;
    db.query('UPDATE productImage SET productID = ?, imageURL = ? WHERE productID = ?', [productID, publicUrl, id], (err, result) => {
      if (err) throw err;
      res.send('Product image updated');
    });
  });

  blobStream.end(file.buffer);
});

app.delete('/product-images/:id', (req, res) => {
  const { id } = req.params;
  db.query('SELECT imageURL FROM productImage WHERE productID = ?', [id], (err, result) => {
    if (err) throw err;
    const imageUrl = result[0].imageURL;
    const fileName = imageUrl.split('/').pop();
    const file = bucket.file(fileName);

    file.delete(err => {
      if (err) {
        res.status(500).send(err);
        return;
      }

      db.query('DELETE FROM productImage WHERE productID = ?', [id], (err, result) => {
        if (err) throw err;
        res.send('Product image deleted');
      });
    });
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
