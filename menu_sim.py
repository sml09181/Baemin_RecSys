import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import torch
import torchvision.transforms as transforms
from tqdm import tqdm
import matplotlib.font_manager as fm
import clip
import imagehash
import csv

import matplotlib.font_manager
print([f.fname for f in matplotlib.font_manager.fontManager.ttflist])

import matplotlib.font_manager
font_list = matplotlib.font_manager.findSystemFonts(fontpaths=None, fontext='ttf')
[matplotlib.font_manager.FontProperties(fname=font).get_name() for font in font_list if 'Nanum' in font]
\
import matplotlib.pyplot as plt
plt.rc('font', family='NanumGothic')
\
import matplotlib as mpl
mpl.rcParams['axes.unicode_minus'] = False

plt.rcParams["font.family"] = 'NanumGothic'
mpl.rcParams['axes.unicode_minus'] = False


# text model: jhgan/ko-sroberta-multitask
# image model: clip ViT-B/32

# ===============================
# CONFIG
# ===============================
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.chdir("/proj-rs/results/menu_sim_clip")
VEC_SAVE_PATH = 'multi_vectors.npy'
IDX_SAVE_PATH = 'menu_index_map.csv'
MENU_TOP_SAVE_PATH = 'menu_top.csv'


# ===============================
# MODELS
# ===============================
def load_text_model(model_name='jhgan/ko-sroberta-multitask'):
    print('text model jhgan/ko-sroberta-multitask loaded')
    return SentenceTransformer(model_name)

def load_image_model():
    device = set_device("0")
    model, preprocess = clip.load("ViT-B/32", device=device)
    model.eval()
    return model, preprocess, device

def set_device(gpu_id):
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id;
    if torch.cuda.is_available():
        device = torch.device(f"cuda:{gpu_id}")
    else:
        device = torch.device("cpu")
    print(device)
    return device


# ===============================
# EMBEDDING FUNCTIONS
# ===============================
def get_text_embedding(text, model):
    return model.encode(text)

def get_image_embedding(img_path, model, preprocess, device):
    try:
        image = Image.open(img_path).convert('RGB')
        image_input = preprocess(image).unsqueeze(0).to(device)
        with torch.no_grad():
            vec = model.encode_image(image_input).squeeze().cpu().numpy()
        return vec
    except Exception as e:
        print(f"Image Error: {img_path} | {e}")
        return np.zeros(512)

def normalize_price(price, mean, std):
    return [(price - mean) / std]

def combine_vectors(text_vec, img_vec, price_vec, a = 1.7, b = 1.2, c = 1):
    text_vec = np.array(text_vec) * a
    img_vec = np.array(img_vec) * b
    price_vec = np.array(price_vec) * c
    return np.concatenate([text_vec, img_vec, price_vec])


# ===============================
# MODE: BUILD VECTOR
# ===============================
def build_vector_mode(df, text_model_name='jhgan/ko-sroberta-multitask'):
    text_model = load_text_model(text_model_name)
    image_model, preprocess, device = load_image_model()

    price_mean = df['menu_price'].mean()
    price_std = df['menu_price'].std()

    multi_vecs = []
    for _, row in tqdm(df.iterrows()):
        text = row['menu_name'] + ' ' + row['menu_description']
        text_vec = get_text_embedding(text, text_model)
        img_vec = get_image_embedding(row['menu_img_path'], image_model, preprocess, device)
        price_vec = normalize_price(row['menu_price'], price_mean, price_std)
        multi_vec = combine_vectors(text_vec, img_vec, price_vec)
        multi_vecs.append(multi_vec)

    np.save(VEC_SAVE_PATH, np.stack(multi_vecs))
    df[['menu_id']].to_csv(IDX_SAVE_PATH, index=False)
    print(f"Vector saved to: {VEC_SAVE_PATH}")
    print(f"Menu ID index saved to: {IDX_SAVE_PATH}")


# ===============================
# MODE: RECOMMEND + PLOT
# ===============================
def recommend_and_plot(df, menu_id):
    vecs = np.load(VEC_SAVE_PATH)
    idx_map = pd.read_csv(IDX_SAVE_PATH)

    try:
        query_idx = idx_map[idx_map['menu_id'] == menu_id].index[0]
    except IndexError:
        print(f"menu_id {menu_id} not found.")
        return
    
    print("Has NaN:", np.isnan(vecs).any())
    nan_rows = np.where(np.isnan(vecs).any(axis=1))[0]
    print("NaN found at indices:", nan_rows)
    vecs = np.nan_to_num(vecs, nan=0.0)

    sims = cosine_similarity(vecs[query_idx].reshape(1, -1), vecs)[0]
    sorted_indices = np.argsort(sims)[::-1]
    
    top_indices = []
    seen_img_hashes = set()

    target = df[df['menu_id'] == menu_id].iloc[0]
    
    try:
        ref_img = Image.open(target['menu_img_path']).convert('RGB')
        ref_hash = str(imagehash.average_hash(ref_img))
        seen_img_hashes.add(ref_hash)
    except Exception as e:
        print(f"Reference img {target['menu_img_path']} X | {e}")
    
    for idx in sorted_indices:
        if idx == query_idx:
            continue

        img_path = df.iloc[idx]['menu_img_path']
        try:
            img = Image.open(img_path).convert('RGB')
            img_hash = str(imagehash.average_hash(img))

            if img_hash not in seen_img_hashes:
                seen_img_hashes.add(img_hash)
                top_indices.append(idx)

            if len(top_indices) >= 3:
                break
        except Exception as e:
            print(f"Failed to load images: {img_path} | {e}")
    
    recs = df.iloc[top_indices]

    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    fig.suptitle(f"Recommended Menus (Reference: {target['menu_name']})", fontsize=16)

    def plot_img(ax, path, title, xlabel):
        try:
            img = Image.open(path).convert('RGB')
            ax.imshow(img)
        except:
            ax.set_title("Image load failed")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(xlabel, fontsize=10)
        ax.axis('off')

    plot_img(
        axes[0],
        target['menu_img_path'],
        "Reference",
        f"{target['menu_name']} (₩{target['menu_price']})"
    )

    for i, (_, row) in enumerate(recs.iterrows()):
        plot_img(
            axes[i + 1],
            row['menu_img_path'],
            f"Top {i+1}",
            f"{row['menu_name']} (₩{row['menu_price']})"
        )

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(f"sim_menu_{menu_id}.png")
    
    recommended_top3 = [df.iloc[i]['menu_id'] for i in top_indices]
    row = [menu_id] + recommended_top3
    

    with open(MENU_TOP_SAVE_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)

if __name__ == "__main__":
    df = pd.read_json('/proj-rs/data/menu_preprocessed.json') 
    build_vector_mode(df)
    
    with open(MENU_TOP_SAVE_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Reference", "Top 1", "Top 2", "Top 3"])
    
    for idx in range(2422):
        recommend_and_plot(df, menu_id=idx)
