import pandas as pd
import os
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # chính là model-ml
DATA_DIR = os.path.join(BASE_DIR, 'MIND-small')

# 1. Convert news.tsv to items.csv
def convert_news_to_items():
    news_path = os.path.join(DATA_DIR, 'news.tsv')
    output_path = os.path.join(DATA_DIR, 'converted_items.csv')

    with open(news_path, 'r', encoding='utf-8') as f_in, open(output_path, 'w', encoding='utf-8', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['id', 'name', 'description', 'category', 'brand'])  # 'brand' = dummy

        for line in f_in:
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                news_id = parts[0]
                category = parts[1]
                title = parts[3]
                abstract = parts[4]
                writer.writerow([news_id, title, abstract, category, "MIND"])

    print("✅ Đã tạo converted_items.csv")

# 2. Convert behaviors.tsv to user_history.csv
def convert_behaviors_to_history():
    behaviors_path = os.path.join(DATA_DIR, 'behaviors.tsv')
    output_path = os.path.join(DATA_DIR, 'converted_user_history.csv')

    with open(behaviors_path, 'r', encoding='utf-8') as f_in, open(output_path, 'w', encoding='utf-8', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['user_id', 'item_id', 'interaction_type', 'timestamp'])

        for line in f_in:
            parts = line.strip().split('\t')
            if len(parts) != 5:
                continue
            user_id = parts[1]
            timestamp = parts[2]
            impressions = parts[4].split()

            for imp in impressions:
                if "-1" in imp:
                    item_id = imp.split('-')[0]
                    writer.writerow([user_id, item_id, 'click', timestamp])

    print("✅ Đã tạo converted_user_history.csv")

if __name__ == "__main__":
    convert_news_to_items()
    convert_behaviors_to_history()
