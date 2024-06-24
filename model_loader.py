import tensorflow as tf
import requests
import tempfile
import logging

loaded_model = None
logger = logging.getLogger(__name__)

def load_model_from_gcs():
    global loaded_model
    if loaded_model is None:
        url = "https://storage.googleapis.com/prodswing-ml/sentiment_analysis_model_500000.h5"
        try:
            # Download the file from the URL
            response = requests.get(url)
            response.raise_for_status()  # Check that the request was successful

            # Write the contents to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file.flush()
                temp_model_path = temp_file.name

            # Load the model from the temporary file
            loaded_model = tf.keras.models.load_model(temp_model_path)
            print(f"Model loaded successfully from {url}")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            print(f"Error loading model: {str(e)}")
    return loaded_model
