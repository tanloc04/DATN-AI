# SnapBuyWeb/model_ml/content_recommender.py
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from market.models import Item

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_PATH = os.path.join(BASE_DIR, 'model_ml', 'data', 'items_content.csv')

def get_content_recommendations(user, top_n=5):
    # Load data sản phẩm từ CSV
    df = pd.read_csv(DATA_PATH)

    # Kết hợp các thông tin thành một trường tổng hợp
    df['combined'] = (
        df['name'].fillna('') + ' ' +
        df['description'].fillna('') + ' ' +
        df['category'].fillna('')
    )

    # Tính TF-IDF
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['combined'])

    # Tính cosine similarity
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Map item_id → index trong dataframe
    indices = pd.Series(df.index, index=df['id'])

    # Lấy ID sản phẩm đã mua
    purchased_item_ids = {order.item_id for order in user.orders}
    if not purchased_item_ids:
        return []

    # Duyệt từng sản phẩm đã mua → gợi ý tương tự
    all_scores = {}
    for item_id in purchased_item_ids:
        if item_id not in indices:
            continue
        idx = indices[item_id]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        for sim_idx, score in sim_scores[1:]:
            sim_item_id = int(df.iloc[sim_idx]['id'])
            if sim_item_id not in purchased_item_ids:
                all_scores[sim_item_id] = max(all_scores.get(sim_item_id, 0), score)

    if not all_scores:
        return []

    # Lấy top_n sản phẩm gợi ý
    top_items = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [Item.query.get(item_id) for item_id, _ in top_items]
