import os
import pandas as pd
from surprise import Dataset, Reader, SVD
import json
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from collections import Counter
from math import log2
import math
import pickle

def load_utility_matrix(excel_path):
    utility_df = pd.read_excel(excel_path, index_col=0)
    melted_df = utility_df.reset_index().melt(id_vars=utility_df.index.name or "user_id",
                                             var_name="item_id", value_name="visits")
    melted_df = melted_df[melted_df["visits"] > 0]  # Surprise는 0 무시
    reader = Reader(rating_scale=(1, melted_df['visits'].max()))
    data = Dataset.load_from_df(melted_df[[utility_df.index.name or "user_id", "item_id", "visits"]], reader)
    return utility_df, melted_df, data

def train_svd(data, model_path=None):
    trainset = data.build_full_trainset()
    model = SVD()
    model.fit(trainset)
    if model_path:
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
    return model

def load_svd_model(model_path):
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    return model

def load_weight_matrices(time_path, weather_path):
    time_matrix = pd.read_excel(time_path, index_col=0)
    weather_matrix = pd.read_excel(weather_path, index_col=0)
    return time_matrix, weather_matrix

def load_restaurant_menu_info(res_path, menu_path):
    with open(res_path, "r", encoding="utf-8") as f:
        res_info = {r["restaurant_id"]: r["res_name"] for r in json.load(f)}
    with open(menu_path, "r", encoding="utf-8") as f:
        menu_data = json.load(f)

    menu_info = {}
    for m in menu_data:
        if m.get("is_best_menu", False):
            menu_info[m["restaurant_id"]] = {
                "menu_name": m.get("menu_name", "N/A"),
                "menu_img_path": m.get("menu_img_path", "N/A")
            }
    return res_info, menu_info

def compute_bias_penalty(melted_df):
    """
    Precompute Bias and Popularity Penalties
    """
    item_user_counts = melted_df.groupby("item_id")["user_id"].nunique()
    adar_bias_dict = {item: 1 / np.log1p(count) for item, count in item_user_counts.items()}
    counts = item_user_counts.to_dict()
    review_counts = np.array(list(counts.values()))
    q1 = np.percentile(review_counts, 25)
    q3 = np.percentile(review_counts, 75)
    iqr = q3 - q1
    median = np.median(review_counts)
    sigma = iqr if iqr > 0 else 1
    return adar_bias_dict, counts, median, sigma

def gaussian_penalty(x, mu, sigma):
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2)

#MARK: Recommendation Function
def recommend_for_user(uid, model, all_restaurants, time_matrix, weather_matrix,
                       adar_bias_dict, counts, current_time, current_weather, 
                       top_n=5, q3=0, sigma=1):
    predictions = []
    raw_scores = []
    time_weights = []
    weather_weights = []
    
    for rid in all_restaurants:
        raw_score = model.predict(uid, rid).est
        raw_scores.append(raw_score)
        time_w = time_matrix.at[current_time, str(rid)] if str(rid) in time_matrix.columns else 0
        weather_w = weather_matrix.at[current_weather, str(rid)] if str(rid) in weather_matrix.columns else 0
        time_weights.append(time_w)
        weather_weights.append(weather_w)

    # MinMax Scaling
    time_weights = MinMaxScaler().fit_transform(np.array(time_weights).reshape(-1, 1)).flatten()
    weather_weights = MinMaxScaler().fit_transform(np.array(weather_weights).reshape(-1, 1)).flatten()

    predictions = []
    for i, rid in enumerate(all_restaurants):
        raw_score = raw_scores[i]
        time_w = time_weights[i]
        weather_w = weather_weights[i]
        adar_bias = adar_bias_dict.get(rid, 1.0)
        bias_adj = 0.2 * adar_bias + 0.8
        popularity_penalty = gaussian_penalty(q3, counts.get(rid, 0), sigma)
        
        final_score = (
            0.7 * raw_score +
            0.15 * time_w +
            0.15 * weather_w
        ) * bias_adj * popularity_penalty 
        
        predictions.append((rid, raw_score, time_w, weather_w, adar_bias, final_score))
        
    top_preds = sorted(predictions, key=lambda x: x[-1], reverse=True)[:top_n]
    return top_preds, raw_scores

def format_recommendations(top_preds, res_info, menu_info, melted_df, uid):
    results = []
    for rid, raw, time_w, weather_w, bias, score in top_preds:
        res_name = res_info.get(rid, "Unknown")
        menu = menu_info.get(rid, {})
        results.append({
            "restaurant_id": rid,
            "restaurant_name": res_name,
            "score": round(score, 2),
            "best_menu": menu.get("menu_name", "N/A"),
            "menu_image": menu.get("menu_img_path", "N/A"),
            "time weight": round(time_w, 4),
            "weather weight": round(weather_w, 4),
            "raw score": round(raw, 4),
            "adar_bias": round(bias, 4)
        })
    visited_restaurants = melted_df[melted_df['user_id'] == uid]['item_id'].unique()
    results.append(visited_restaurants)
    return results

def inference(target_uid, recommendation, res_info):
    print(f"[User {target_uid}]")
    print("Already visited: ")
    for res_id in recommendation[-1]:
        res_name = res_info.get(res_id, "Unknown")
        print(f"   {res_name}")
    print("Recommend: ")
    for rec in recommendation[:-1]:
        print("    ", rec)
    print("------------------------------------------------")

def plot_raw_score_boxplot(all_raw_scores, time_matrix, weather_matrix, save_path_prefix):
    time_vals = time_matrix.values.flatten().tolist()
    weather_vals = weather_matrix.values.flatten().tolist()
    df = pd.DataFrame({
        'score': list(all_raw_scores) + time_vals + weather_vals,
        'group': ['SVD']*len(all_raw_scores) + ['Time']*len(time_vals) + ['Weather']*len(weather_vals)
    })
    palette = {'SVD': '#1f77b4', 'Time': '#ff7f0e', 'Weather': '#2ca02c'}

    plt.figure(figsize=(8, 6))
    sns.boxplot(x='group', y='score', data=df, hue='group', palette=palette, legend=False)
    plt.title("Raw Score Boxplot", fontsize=14)
    plt.xlabel("Group", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(f"{save_path_prefix}_boxplot.png")
    plt.close()

    plt.figure(figsize=(8, 6))
    sns.boxplot(x='group', y='score', data=df, hue='group', palette=palette, legend=False)
    plt.ylim(0, 60)
    plt.title("Raw Score Boxplot (Zoomed Y-axis 0~60)", fontsize=14)
    plt.xlabel("Group", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(f"{save_path_prefix}_boxplot_zoom.png")
    plt.close()

def plot_recommendation_histogram(counts, save_path):
    plt.figure(figsize=(10, 6))
    plt.hist(counts.values(), bins=20, color='skyblue', edgecolor='black')
    plt.title("Histogram of Recommendation Frequency per Item")
    plt.xlabel("Number of Recommendations")
    plt.ylabel("Number of Items")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def compute_coverage_entropy(recommended_items, all_restaurants):
    unique_recommended_items = set(recommended_items)
    total_items = set(all_restaurants)
    item_coverage = len(unique_recommended_items) / len(total_items) * 100 if total_items else 0

    counts = Counter(recommended_items)
    total_recs = sum(counts.values())
    entropy = -sum((count / total_recs) * log2(count / total_recs) for count in counts.values()) if total_recs > 0 else 0

    max_entropy = math.log2(len(counts)) if counts else 0
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
    return len(unique_recommended_items), item_coverage, entropy, normalized_entropy, counts

def main():
    # Paths
    base_dir = '/proj-rs/data'
    user_review_dir = os.path.join(base_dir, '02_restaurants', 'user_review_excel')
    restaurant_info_dir = os.path.join(base_dir)
    utility_path = os.path.join(user_review_dir, '05_7_utility_matrix.xlsx')
    time_weight_path = os.path.join(user_review_dir, 'weight_time_matrix.xlsx')
    weather_weight_path = os.path.join(user_review_dir, 'weight_weather_matrix.xlsx')
    res_info_path = os.path.join(restaurant_info_dir, 'restaurant_info_preprocessed.json')
    menu_info_path = os.path.join(restaurant_info_dir, 'menu_preprocessed.json')
    save_dir = "/proj-rs/results/svd"
    model_save_path = os.path.join(save_dir, 'svd.pkl')
    os.makedirs(save_dir, exist_ok=True)
    
    #MARK: Change Here
    top_n = 5
    global current_time, current_weather
    current_time = "저녁"    # 아침, 점심, 저녁
    current_weather = "눈"  # 맑음, 흐림, 비, 눈

    # Load data
    utility_df, melted_df, data = load_utility_matrix(utility_path)
    time_matrix, weather_matrix = load_weight_matrices(time_weight_path, weather_weight_path)
    res_info, menu_info = load_restaurant_menu_info(res_info_path, menu_info_path)
    adar_bias_dict, counts, q3, sigma = compute_bias_penalty(melted_df)
    all_restaurants = utility_df.columns.tolist()

    # Train or load model
    if os.path.exists(model_save_path):
        print("Loading saved model...")
        model = load_svd_model(model_save_path)
    else:
        print("Training new model...")
        model = train_svd(data, model_save_path)

    final_output = {}
    all_raw_scores = []

    # Generate recommendations for all users
    for uid in utility_df.index:
        top_preds, raw_scores = recommend_for_user(
            uid, model, all_restaurants, time_matrix, weather_matrix,
            adar_bias_dict, counts, current_time, current_weather, top_n, q3, sigma
        )
        all_raw_scores.extend(raw_scores)
        formatted = format_recommendations(top_preds, res_info, menu_info, melted_df, uid)
        final_output[uid] = formatted

    # Print stats
    all_raw_scores = np.array(all_raw_scores)
    print("\n전체 사용자 Raw Score 통계:")
    print(f" - 평균 (mean): {all_raw_scores.mean():.4f}")
    print(f" - 표준편차 (std): {all_raw_scores.std():.4f}")
    print(f" - 최댓값 (max): {all_raw_scores.max():.4f}")
    print(f" - 최솟값 (min): {all_raw_scores.min():.4f}")
    print(f" - 중앙값 (median): {np.median(all_raw_scores):.4f}")
    
    with open(os.path.join(save_dir, f"recommend_results_{current_time}_{current_weather}.pkl"), "wb") as f:
        pickle.dump(final_output, f)

    # Inference for all users
    for uid, recommendation in final_output.items():
        inference(uid, recommendation, res_info)

    # Item coverage & entropy
    recommended_items = [rec['restaurant_id'] for recs in final_output.values() for rec in recs[:-1]]
    num_recommend_items, coverage, entropy, normalized_entropy, counts = compute_coverage_entropy(recommended_items, all_restaurants)
    print(f"- Item Coverage: {coverage:.2f}%")
    print(f"- # Recommend Unique Items: {num_recommend_items}")
    print(f"- Entropy: {entropy:.4f}")
    print(f"- Normalized Entropy (0~1): {normalized_entropy:.4f}")
    
    # Plots
    plot_raw_score_boxplot(all_raw_scores, time_matrix, weather_matrix, os.path.join(save_dir, 'raw_scores'))
    plot_recommendation_histogram(counts, os.path.join(save_dir, 'freq_hist.png'))

if __name__ == "__main__":
    main()
