import os
import pickle
import numpy as np
from sklearn.metrics.pairwise import linear_kernel
from market.models import Item

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_PATH = os.path.join(BASE_DIR, 'model_ml', 'model_content_mind.pkl')

def get_mind_recommendations(user, top_n=5):
    if not os.path.exists(MODEL_PATH):
        return []

    with open(MODEL_PATH, 'rb') as f:
        mind_model = pickle.load(f)

    user_id = user.id

    tfidf_matrix = mind_model['tfidf_matrix']
    user_profiles = mind_model['user_profiles']
    item_ids = mind_model['item_ids']

    if user_id not in user_profiles:
        return []

    user_vector = np.asarray(user_profiles[user_id])
    cosine_sim = linear_kernel(user_vector, tfidf_matrix).flatten()
    top_indices = cosine_sim.argsort()[-top_n:][::-1]
    recommended_item_ids = [item_ids[idx] for idx in top_indices]

    return [Item.query.get(item_id) for item_id in recommended_item_ids]
