import re
import copy
from datetime import datetime, timedelta
import json
import pandas as pd

def clean_address(addr, prefix):
    return addr.replace(prefix, "").replace("복사", "").strip()

def remove_provided_text(desc):
    if not isinstance(desc, str):
        return ''
    return re.sub(r'.*제공\n?', '', desc).strip()

# Preprocessing business hours
def get_last_order_time(time_info):
    if '라스트오더' in time_info:
        match = re.search(r'\n(\d{2}:\d{2}) 라스트오더', time_info)
        if match:
            return match.group(1)
    elif '정기휴무' in time_info:
        return None
    else:
        match = re.search(r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})', time_info)
        if match:
            end = match.group(2)
            if end == '24:00':
                return '23:30'
            else:
                end_time = datetime.strptime(end, '%H:%M')
                last_order = end_time - timedelta(minutes=30)
                return last_order.strftime('%H:%M')
    return None

def clean_business_hour_text(hour_str):
    return re.sub(r'\n\d{2}:\d{2} 라스트오더', '', hour_str).strip()


with open('/proj-rs/data/restaurant_info.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

review_df = pd.read_excel('/proj-rs/data/02_restaurants/user_review_excel/05_3_reviews_combine_restaurant_id_nan_X.xlsx')
valid_ids = set(review_df['restaurant_id'].dropna().astype(int).tolist()) # Filter based on restaurant_id

data = [res for res in data if res.get('restaurant_id') in valid_ids]
processed_data = copy.deepcopy(data)

for restaurant in processed_data:
    restaurant['road_name_addr'] = clean_address(restaurant['road_name_addr'], '도로명')
    restaurant['lot_num_addr'] = clean_address(restaurant['lot_num_addr'], '지번')
    restaurant['description'] = remove_provided_text(restaurant.get('description'))
    last_order_hours = {}
    new_business_hours = {}
    for day, hours in restaurant['business_hours'].items():
        last_order_hours[day] = get_last_order_time(hours)
        new_business_hours[day] = clean_business_hour_text(hours)
    restaurant['last_order_hours'] = last_order_hours
    restaurant['business_hours'] = new_business_hours

with open('/proj-rs/data/restaurant_info_preprocessed.json', 'w', encoding='utf-8') as f:
    json.dump(processed_data, f, ensure_ascii=False, indent=2)