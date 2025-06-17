import pandas as pd
import re

def date_change(date_str):
    m = re.match(r"(\d{4})년 (\d{1,2})월 (\d{1,2})일", str(date_str))
    if m:
        y, m_, d = m.groups()
        return pd.to_datetime(f"{y}-{int(m_):02d}-{int(d):02d}")
    return pd.NaT

review_df = pd.read_excel("/proj-rs/data/02_restaurants/user_review_excel/05_4_reviews_combine_user_id_nan_X.xlsx")
weather_df = pd.read_csv('/proj-rs/data/04_weather.csv', parse_dates=['날짜'])

# time
weight_time_matrix = pd.pivot_table(review_df, 
                                     index='visit_time', 
                                     columns='restaurant_id', 
                                     values='user_id',  # 아무 컬럼이나 count 기준으로 사용
                                     aggfunc='count', 
                                     fill_value=0)

time_mapping = {
    "After": "점심",
    "Eve": "저녁",
    "Mor": "아침",
    "N": "밤",
    "밤": "밤",
    "아침": "아침",
    "점심": "점심",
    "저녁": "저녁"
}

weight_time_matrix.rename(index=time_mapping, inplace=True)
weight_time_matrix = weight_time_matrix.groupby(weight_time_matrix.index).sum()
weight_time_matrix.to_excel("/proj-rs/data/02_restaurants/user_review_excel/weight_time_matrix.xlsx")

# weather
review_df['date'] = review_df['date'].apply(date_change)
review_df['restaurant_id'] = review_df['restaurant_id'].astype(str).str.replace(',', '').astype(int)
merged_df = pd.merge(review_df, weather_df, left_on='date', right_on='날짜', how='left')

weather_cols = weather_df.columns.drop('날짜')
weight_weather_matrix = merged_df.groupby('restaurant_id')[weather_cols].sum().astype(int).T
weight_weather_matrix.to_excel("/proj-rs/data/02_restaurants/user_review_excel/weight_weather_matrix.xlsx")