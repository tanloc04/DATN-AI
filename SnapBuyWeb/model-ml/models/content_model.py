import pandas as pd
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_PATH = os.path.join('model-ml', 'model_content_based.pkl')

def train_content_model():
    df = pd.read_csv('model-ml/data/items_content.csv') # Đường dẫn tới dataset sản phẩm

    # Gộp các đặc trưng dạng văn bản lại thành 1 trường duy nhất
    df['combined'] = df['name'].fillna('') + ' ' + df['description'].fillna('') + ' ' + df['category'].fillna('')

    # Tính TF-IDF
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['combined'])

    # Tính cosine similarity
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Lưu lại mô hình
    item_ids = df['id'].tolist()
    model_data = {
        'cosine_sim': cosine_sim,
        'item_ids': item_ids
    }

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model_data, f)

    print(f"[✅] Content-based model đã được train và lưu tại {MODEL_PATH}")
