from flask import Flask, request, jsonify
from google.cloud import firestore, storage
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Explicitly set the project ID from the environment variable
project_id = os.getenv('GCLOUD_PROJECT_ID')

# Firestore connection
db = firestore.Client(project=project_id)

# Google Cloud Storage
storage_client = storage.Client()
bucket_name = os.getenv('GCLOUD_STORAGE_BUCKET')
bucket = storage_client.bucket(bucket_name)

@app.route('/products', methods=['GET'])
def get_products():
    products_ref = db.collection('products')
    docs = products_ref.stream()
    products = [doc.to_dict() for doc in docs]
    return jsonify(products)

@app.route('/products/<string:product_id>', methods=['GET'])
def get_product(product_id):
    products_ref = db.collection('products')
    query_ref = products_ref.where('productID', '==', product_id).stream()
    products = [doc.to_dict() for doc in query_ref]
    
    if products:
        return jsonify(products[0])
    else:
        return jsonify({'error': 'Product not found'}), 404

@app.route('/products', methods=['POST'])
def add_product():
    data = request.json
    product_ref = db.collection('products').add(data)
    return jsonify({'id': product_ref[1].id})

@app.route('/products/<string:id>', methods=['PUT'])
def update_product(id):
    data = request.json
    product_ref = db.collection('products').document(id)
    product_ref.set(data, merge=True)
    return 'Product updated', 200

@app.route('/products/<string:id>', methods=['DELETE'])
def delete_product(id):
    product_ref = db.collection('products').document(id)
    product_ref.delete()
    return 'Product deleted', 200

@app.route('/product-images', methods=['GET'])
def get_product_images():
    images_ref = db.collection('productImages')
    docs = images_ref.stream()
    images = [doc.to_dict() for doc in docs]
    return jsonify(images)

@app.route('/product-images/<string:id>', methods=['GET'])
def get_product_image(id):
    images_ref = db.collection('productImages').where('productID', '==', id)
    docs = images_ref.stream()
    images = [doc.to_dict() for doc in docs]
    return jsonify(images)

@app.route('/product-images', methods=['POST'])
def upload_product_image():
    productID = request.form['productID']
    file = request.files['image']
    blob = bucket.blob(secure_filename(file.filename))

    blob.upload_from_string(
        file.read(),
        content_type=file.content_type
    )
    public_url = blob.public_url

    image_data = {
        'productID': productID,
        'imageURL': public_url
    }

    image_ref = db.collection('productImages').add(image_data)
    return jsonify({'id': image_ref[1].id, 'imageURL': public_url})

@app.route('/product-images/<string:id>', methods=['PUT'])
def update_product_image(id):
    productID = request.form['productID']
    file = request.files['image']
    blob = bucket.blob(secure_filename(file.filename))

    blob.upload_from_string(
        file.read(),
        content_type=file.content_type
    )
    public_url = blob.public_url

    image_data = {
        'productID': productID,
        'imageURL': public_url
    }

    images_ref = db.collection('productImages').where('productID', '==', id).stream()
    for image in images_ref:
        image.reference.update(image_data)
    return 'Product image updated', 200

@app.route('/product-images/<string:id>', methods=['DELETE'])
def delete_product_image(id):
    images_ref = db.collection('productImages').where('productID', '==', id).stream()
    for image in images_ref:
        image_data = image.to_dict()
        image.reference.delete()
        file_name = os.path.basename(image_data['imageURL'])
        blob = bucket.blob(file_name)
        blob.delete()
    return 'Product image deleted', 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
