import pickle
import os

MODEL_PATH = os.path.join('model-ml', 'model_content_based.pkl')

with open(MODEL_PATH, 'rb') as f:
    model_data = pickle.load(f)

cosine_sim = model_data['cosine_sim']
item_ids = model_data['item_ids']

id_to_index = {item_id: idx for idx, item_id in enumerate(item_ids)}
index_to_id = {idx: item_id for idx, item_id in enumerate(item_ids)}


def get_similar_items(item_id, top_n=5):
    if item_id not in id_to_index:
        return []

    idx = id_to_index[item_id]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Bỏ chính nó đi
    similar_indices = [i for i, _ in sim_scores[1:top_n + 1]]
    return [index_to_id[i] for i in similar_indices]
