import re
import copy
from datetime import datetime, timedelta
import json
import pandas as pd

def clean_price(price_str):
    if price_str == '변동':
        return None
    if price_str == '무료':
        return 0
    # For ranges like '12000~18000', calculate the average value
    if '~' in price_str:
        price_range = price_str.replace('원', '').replace(',', '').split('~')
        low_price = int(price_range[0].strip())
        high_price = int(price_range[1].strip())
        return (low_price + high_price) // 2 
    return int(price_str.replace('원', '').replace(',', '').strip())

# Remove brackets like [[ ]], []
def clean_menu_name(menu_name):
    menu_name = re.sub(r'\[\[.*?\]\]', '', menu_name) 
    menu_name = re.sub(r'\[.*?\]', '', menu_name) 
    return menu_name.strip()

def clean_menu_description(description):
    description = re.sub(r'\+.*', '', description)
    return description.strip()


restaurant_info_df = pd.read_excel('/proj-rs/data/01_restaurant_info.xlsx')
restaurant_info = dict(zip(restaurant_info_df['RestaurantID'], restaurant_info_df['RestaurantType']))

with open('/proj-rs/data/menu.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for menu in data:
    menu['menu_price'] = clean_price(menu['menu_price'])
    menu['menu_name'] = clean_menu_name(menu['menu_name'])
    menu['menu_description'] = clean_menu_description(menu['menu_description'])
    menu['menu_img_path'] = update_img_path(menu['menu_img_path'])
    rest_id = menu.get('restaurant_id')
    if rest_id in restaurant_info:
        menu['restaurant_type'] = restaurant_info[rest_id]
        
with open('/proj-rs/data/menu_preprocessed.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)