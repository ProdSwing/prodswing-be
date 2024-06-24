from datetime import datetime, timedelta
import subprocess
from flask import Flask, request, jsonify
from google.cloud import firestore, storage
import numpy as np
import pandas as pd
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler
from model_loader import loaded_model, load_model_from_gcs
from query_model import analyze

load_dotenv()

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

@app.route('/signup', methods=['POST'])
def signup():
    try:
        id_token = request.json.get('id_token')
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token['email']
        name = request.json.get('name')
        user_name = request.json.get('user_name')

        user_data = {
            'firebaseUID': uid,
            'userName': user_name,
            'name': name,
            'email': email
        }

        user_ref = db.collection('users').document(uid)
        user_ref.set(user_data)

        return jsonify({'message': 'User signed up successfully', 'user': user_data}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/login', methods=['POST'])
def login():
    try:
        id_token = request.json.get('id_token')
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()

        if user_doc.exists:
            return jsonify({'message': 'Login successful', 'user': user_doc.to_dict()}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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

def fetch_tweets(product_name):
    print("fetch_tweeets: ", product_name)
    twitter_auth_token = os.getenv('TWITTER_AUTH_TOKEN')
    limit = 15
    current_date = datetime.now()
    day_end = current_date.day
    month_end = current_date.month
    year_end = current_date.year
    previous_date = current_date - timedelta(days=5)
    day_start = previous_date.day
    month_start = previous_date.month
    year_start = previous_date.year
    filename = f'updated_{product_name}_{previous_date.strftime("%Y-%m-%d")}.csv'

    search_keyword = f'{product_name} lang:en since:{year_start}-{month_start:02d}-{day_start:02d} until:{year_end}-{month_end:02d}-{day_end:02d}'
        
    subprocess.run(f'npx --yes tweet-harvest@2.6.1 -o "{filename}" -s "{search_keyword}" --tab "LATEST" -l {limit} --token {twitter_auth_token}', shell=True)
        
    df = pd.read_csv(f'tweets-data/{filename}', usecols=['full_text'])
    os.remove(f'tweets-data/{filename}')
    return analyze(df)

def scheduled_update_tweets():
    with app.app_context():
        try:
            results_ref = db.collection('results')
            docs = list(results_ref.stream())
            if not docs:
                print("No documents found in 'results' collection.")
                return

            random_doc = docs[np.random.randint(0, len(docs))]
            product_name = random_doc.to_dict().get('name')
            
            # Fetch new tweet analysis result for the product
            new_result = fetch_tweets(product_name)
            
            # Update the result attribute of the random document
            random_doc.reference.update({'result': new_result})
            print(f"Updated '{product_name}' result to: {new_result}")
        except Exception as e:
            print(f"Error: {e}")

@app.route('/results', methods=['GET'])
def get_results():
    results_ref = db.collection('results')
    docs = results_ref.stream()
    results = [doc.to_dict() for doc in docs]
    return jsonify(results)

@app.route('/results/<string:id>', methods=['GET'])
def get_results_category(id):
    results_ref = db.collection('results').where('category', '==', id)
    docs = results_ref.stream()
    filtered_results = [doc.to_dict() for doc in docs]
    return jsonify(filtered_results)

if __name__ == '__main__':
    loaded_model = loaded_model or load_model_from_gcs()
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_update_tweets, 'cron', hour=1, minute=10)
    scheduler.start()
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
