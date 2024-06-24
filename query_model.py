import re
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import Embedding, Bidirectional, LSTM, Dropout, Conv1D, GlobalMaxPooling1D, Dense
from tensorflow.keras.models import Sequential, load_model
from model_loader import loaded_model, load_model_from_gcs

def clean_text(text):
  # Remove date at the beginning of the tweet
  text = re.sub(r'^\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2} ', '', text)

  # Remove URLs
  text = re.sub(r'https?://\S+', '', text)

  # Remove mentions
  text = re.sub(r'@\w+', '', text)

  # Remove hashtags
  text = re.sub(r'#\w+', '', text)

  # Remove emojis
  text = text.encode('ascii', 'ignore').decode('ascii')

  # Remove <br> or <br /> tags
  text = re.sub(r'<br\s*/?>', '', text)

  # Remove special characters
  text = re.sub(r'[^A-Za-z0-9\s]+', '', text)

  # Convert to lowercase
  text = text.lower()

  # Remove extra whitespaces
  text = re.sub(r'\s+', ' ', text).strip()

  return text

def sentiment_analysis(df, vocab_size=1000, return_word_index=False, texts=[], model= None, predict=False):
  sentences = df['cleaned_text'].tolist()
  labels = df['sentiment'].tolist()

  training_portion = .8
  training_size = int(len(sentences) * training_portion)

  training_sentences = sentences[:training_size]
  training_labels = labels[:training_size]

  validation_sentences = sentences[training_size:]
  validation_labels = labels[training_size:]

  # vocab_size = 1000
  vocab_size = vocab_size
  embedding_dim = 100
  max_length = 100
  trunc_type = 'post'
  padding_type = 'post'
  oov_tok = "<OOV>"

  tokenizer = Tokenizer(num_words=vocab_size, oov_token=oov_tok)
  tokenizer.fit_on_texts(training_sentences)
  word_index = tokenizer.word_index

  if return_word_index:
    return word_index

  if predict:
    sequences = tokenizer.texts_to_sequences(texts)
    padded_sequences = pad_sequences(sequences, maxlen=max_length, padding=padding_type, truncating=trunc_type)
    predictions = model.predict(padded_sequences)
    predicted_classes = [np.argmax(pred) for pred in predictions]

    return predicted_classes

  else:
    training_sequences = tokenizer.texts_to_sequences(training_sentences)
    training_padded = pad_sequences(training_sequences, maxlen=max_length, padding=padding_type, truncating=trunc_type)

    validation_sequences = tokenizer.texts_to_sequences(validation_sentences)
    validation_padded = pad_sequences(validation_sequences, maxlen=max_length, padding=padding_type, truncating=trunc_type)

    training_labels = np.array(training_labels)
    validation_labels = np.array(validation_labels)

    model = Sequential([
      Embedding(vocab_size, embedding_dim, input_length=max_length),
      Bidirectional(LSTM(64, return_sequences=True)),
      Conv1D(128, 5, activation='relu'),
      GlobalMaxPooling1D(),
      Dense(64, activation='relu'),
      Dense(32, activation='relu'),
      Dropout(0.5),
      Dense(3, activation='softmax')
    ])

    model.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

    model.fit(
      training_padded,
      training_labels,
      # epochs=20,
      epochs=5,
      validation_data=(validation_padded, validation_labels),
      verbose=1
    )

    return model
  
model = loaded_model or load_model_from_gcs()
  
def analyze(df):
    if model is None:
        raise RuntimeError("Model not loaded. Ensure model_loader.load_model_from_file is successful.")
    # print("MASUK")
    df['full_text'] = df['full_text'].astype(str)
    shuffled_df = pd.read_csv('gs://prodswing-ml/shuffled_df.csv')
    shuffled_df['cleaned_text'] = shuffled_df['cleaned_text'].astype(str)
    df['cleaned_text'] = df['full_text'].apply(clean_text)
    predicted_classes = sentiment_analysis(shuffled_df, 500000, False, df['cleaned_text'].tolist(), model, True)

    sentiment_labels = ['Negative', 'Neutral', 'Positive']
    predicted_sentiments = [sentiment_labels[pred] for pred in predicted_classes]

    positive_count = predicted_sentiments.count('Positive')
    negative_count = predicted_sentiments.count('Negative')

    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    else:
        return "Neutral"
