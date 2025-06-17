import os
import random
import pandas as pd
import base64
import gradio as gr 

from svd import *

def load(base_dir):
    # path
    user_review_dir = os.path.join(base_dir, '02_restaurants', 'user_review_excel')
    utility_path = os.path.join(user_review_dir, '05_7_utility_matrix.xlsx')
    res_info_path = os.path.join(base_dir, 'restaurant_info_preprocessed.json')
    menu_info_path = os.path.join(base_dir, 'menu_preprocessed.json')
    
    # Load data
    _, melted_df, _ = load_utility_matrix(utility_path)
    res_info, menu_info = load_restaurant_menu_info(res_info_path, menu_info_path)
    return res_info, menu_info, melted_df

def get_user_info(melted_df, res_info):
    user_info = dict()
    selected_users = sorted(random.sample(melted_df['user_id'].tolist(), 4)) # sample users
    for user_id in selected_users:
        visited_restaurants = melted_df[melted_df['user_id'] == user_id]['item_id'].unique().tolist()
        visited_restaurants = [res_info.get(res_id, "Unknown") for res_id in visited_restaurants]
        user_info[f"user{user_id}"] = visited_restaurants
    return user_info
    
def get_user_desc(user_id):
    visits = user_info.get(user_id, [])
    return "최근 방문한 식당: " + ", ".join(visits) if visits else "방문한 식당 정보 없음"

def get_image_base64(image_path):
    # to show local images
    with open(image_path, "rb") as img_f:
        img_bytes = img_f.read()
    base64_str = base64.b64encode(img_bytes).decode()
    ext = image_path.split('.')[-1]
    return f"data:image/{ext};base64,{base64_str}"

#MARK: SVD
def svd(user_id, visit_time, visit_weather):
    user_id = int(user_id[4:])
    with open(os.path.join("/proj-rs/results/svd", f"recommend_results_{visit_time}_{visit_weather}.pkl"), "rb") as f:
        svd_results = pickle.load(f) # use trained model

    menu_names = [r["best_menu"] for r in svd_results[user_id][:-1]]
    cards = ""
    for r in svd_results[user_id][:-1]:
        img_path = os.path.join("/proj-rs/static/images", r['menu_image'].split("/")[-1])
        img_src = get_image_base64(img_path)
        cards += f"""
        <div style="display:inline-block;width:180px;margin:5px;text-align:center">
            <img src="{img_src}" alt="{r['best_menu']}" style="width:100%;border-radius:10px">
            <div style="font-weight:bold;margin-top:5px">{r['best_menu']}</div>
            <div style="font-size:0.9em;color:gray">{r['restaurant_name']}</div>
        </div>
        """
    return gr.update(choices=menu_names, visible=True), cards

#MARK: MENU SIMILARITY
def menu_sim(menu_choice):
    df = pd.read_csv("/proj-rs/results/menu_sim_clip/menu_top.csv") # load precomputed similarity results
    with open("/proj-rs/data/menu_preprocessed.json", "r", encoding="utf-8") as f:
        menu_info = json.load(f)
    with open("/proj-rs/data/restaurant_info.json", "r", encoding="utf-8") as f:
        res_info = {r["restaurant_id"]: r["res_name"] for r in json.load(f)}
    name_to_info = {item['menu_name']: item for item in menu_info}
    id_to_info = {item['menu_id']: item for item in menu_info}
    if menu_choice not in name_to_info:
        return f"선택한 메뉴 '{menu_choice}' 정보를 찾을 수 없습니다."
    ref_id = name_to_info[menu_choice]['menu_id']
    row = df[df['Reference'] == ref_id]
    row = row.iloc[0]
    top_ids = [row['Top 1'], row['Top 2'], row['Top 3']]
    
    htmls = []
    for tid in top_ids:
        if tid not in id_to_info:
            continue
        info = id_to_info[tid]
        name = info.get('menu_name', 'Unknown Menu')
        desc = info.get('menu_description', '')
        rest_id = info.get('restaurant_id', '')
        rest = res_info.get(rest_id, '')
        img_path = info.get('menu_img_path', '')
        img_src = get_image_base64(img_path)
        html = f"""
        <div style="display: inline-block; width: 180px; margin: 5px; text-align: center;">
            <img src="{img_src}" alt="{name}" style="width: 100%; border-radius: 10px;">
            <div style="font-weight: bold; margin-top: 5px;">{name}</div>
            <div style="font-size: 0.9em;">{desc}</div>
            <div style="color: gray; font-size: 0.8em;">{rest}</div>
        </div>
        """
        htmls.append(html)
        
    footer = """
    <div style="text-align: center; margin-top: 30px; font-size: 1.2em;">
        🍽️ 맛있는 식사 되세요! 🍱🍰💕
    </div>
    """
    return "".join(htmls) + footer

#MARK: MAIN
def main():
    base_dir = '/proj-rs/data'
    res_info, menu_info, melted_df = load(base_dir)
    user_info = get_user_info(melted_df, res_info)
    with gr.Blocks() as demo:
        gr.HTML(
            """
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div></div>
                <div style="text-align:right; font-size:18px; font-weight:bold;">
                    2025-1 Recommendation System Term Project
                </div>
            </div>
            """
        )
        gr.Markdown("# 🍽️ 배레모 - 오늘 모 먹지?")
        gr.Markdown("## 1단계: 어떤 음식이 끌리시나요?")
        
        with gr.Row():
            user_radio = gr.Radio(choices=list(user_info.keys()), label="사용자 선택")
            time_radio = gr.Radio(choices=["아침", "점심", "저녁"], label="방문 시간")
            weather_radio = gr.Radio(choices=["맑음", "비", "눈", "흐림"], label="날씨")
            
        user_visit_text = gr.Markdown("")
        def get_user_desc(user_id):
            visits = user_info.get(user_id, [])
            return "최근 방문한 식당: " + ", ".join(visits) if visits else "방문한 식당 정보 없음"
        user_radio.change(fn=get_user_desc, inputs=user_radio, outputs=user_visit_text)
        step1_btn = gr.Button("Get Recommendations")
        selected_menu = gr.Dropdown(label="STEP 2: 선택한 메뉴", visible=False)
        result_html_step1 = gr.HTML()
        step1_btn.click(fn=svd,
                        inputs=[user_radio, time_radio, weather_radio],
                        outputs=[selected_menu, result_html_step1])

        gr.Markdown("## 2단계: 선택한 메뉴와 비슷한 음식들을 만나보세요!")
        step2_btn = gr.Button("Get Recommendations")
        result_html_step2 = gr.HTML()
        step2_btn.click(
            fn=menu_sim,
            inputs=[selected_menu],
            outputs=[result_html_step2]
        )

    demo.launch() # demo.launch(share=True)

if __name__ == '__main__':
    main()
