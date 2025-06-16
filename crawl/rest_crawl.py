import os
import re
from time import sleep
import random
import pandas as pd
import json
import requests
from selenium import webdriver
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Chrome WebDriver 설정
options = Options()
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
options.add_argument('window-size=1380,1200')
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(3)

file_path = '01_restaurant_info_filtered.xlsx'
df = pd.read_excel(file_path)
menu_dict = dict()
menu_id = 0

if not os.path.exists('/RecSys/raw'):
    os.makedirs('/RecSys/raw')

def search_iframe():
    driver.switch_to.default_content()
    driver.switch_to.frame("searchIframe")

def entry_iframe():
    driver.switch_to.default_content()
    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, '//*[@id="entryIframe"]')))
    for i in range(5):
        sleep(1)
        try:
            driver.switch_to.frame(driver.find_element(By.XPATH, '//*[@id="entryIframe"]'))
            break
        except: pass

for index, row in df.iterrows():
    if index % 10 == 0:
        driver.refresh()
        sleep(5)
    restaurant_id = row['RestaurantID']

    if index <= 56: continue
    keyword = row['RevisedRestaurant']
    url = f'https://map.naver.com/p/search/{keyword}'
    driver.get(url)
    sleep(2)
    try: search_iframe()
    except: continue
    sleep(4)

    ALL_INFO = []
    RES_REVIEWS = []
    RES_MENUS = []
    res_name = None
    phone_num = None
    road_name_addr = None
    lot_num_addr = None
    description = None
    business_hours = None
    num_menu = 0

    print(f"--------------------------- {index}: {keyword} ---------------------------")

    ##  검색 결과에서 서울 서대문구 소재인 식당 선택 ##############################################################################################
    def get_lot_number_address():
        try:
            entry_iframe()
            driver.find_element(By.XPATH, '//span[@class="_UCia"]').click()
            sleep(1)
            return driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div/div[5]/div/div[2]/div[1]/div/div[1]/div/div[1]/div[2]").text
        except:
            return None
    
    lot_num_addr = get_lot_number_address()
    if not lot_num_addr or ('서울 서대문구 대현동' not in lot_num_addr and '서울 서대문구 창천동' not in lot_num_addr):
        try:
            search_iframe()
            addr_elements = driver.find_elements(By.XPATH, '//span[@class="Pb4bU"]')
            simple_addrs = [el.text for el in addr_elements if '서울 서대문구' in el.text]

            if not simple_addrs:
                print(f"[ERROR] No search results matching the restaurant name - {keyword}.")
                continue

            for i, addr in enumerate(simple_addrs[:4]):
                if '대현동' in addr or '창천동' in addr:
                    try:
                        driver.find_elements(By.XPATH, '//span[@class="YwYLL"]')[i].click()
                        sleep(3)
                        break
                    except:
                        continue
            else:
                continue
        except:
            continue
    
    ## 음식점 기본 정보 가져오기 ###############################################################################################################
    road_name_addr = driver.find_element(By.XPATH, '/html/body/div[3]/div/div/div/div[5]/div/div[2]/div[1]/div/div[1]/div/div[1]/div[1]').text  # 도로명 주소
    driver.find_element(By.CLASS_NAME, 'nmfMK').click() 
    res_name = driver.find_element(By.XPATH, '//span[@class="GHAhO"]').text
    try:
        phone_num = driver.find_element(By.XPATH,'//span[@class="xlx7Q"]').text # 전화번호
    except: print(f"[ERROR] No search results matching the restaurant name - {keyword}.")
    try: description = driver.find_element(By.XPATH,'/html/body/div[3]/div/div/div/div[2]/div[1]/div[2]/div').text # 음식점 한 줄 소개
    except: print(f"[ERROR] No search results matching the restaurant name - {keyword}.")
    print(res_name, road_name_addr, phone_num, description)

    ## 영업 시간 및 브레이크 타임 가져오기 ######################################################################################################
    business_hours = dict()
    try:
        business_hours_button = driver.find_element(By.CLASS_NAME, 'gKP9i')
        business_hours_button.click()
        sleep(2)
        parent_elements = driver.find_elements(By.XPATH,'//span[@class="i8cJw"]') # 요일
        child_elements = driver.find_elements(By.CLASS_NAME, 'H3ua4')
        for p, c in zip(parent_elements, child_elements):
            business_hours[p.text] = c.text
    except:
        print(f"Error get business hours")
    ALL_INFO = {"restaurant_id": restaurant_id, "res_name": res_name, "phone_num": phone_num, "road_name_addr": road_name_addr, \
                "lot_num_addr": lot_num_addr, "description": description, "business_hours": business_hours}

    ## 메뉴명 및 사진 경로 가져오기 #############################################################################################################
    try:
        menu_element = driver.find_element(By.XPATH, "//span[@class='veBoZ' and text()='메뉴']")
        menu_element.click()
        sleep(2)
        menu_names =  driver.find_elements(By.XPATH, '//span[@class="lPzHi"]')
        try:
            menu_descriptions = driver.find_elements(By.XPATH, '//div[@class="kPogF"]')
        except: menu_descriptions = [None] * len(menu_names)
        menu_prices = driver.find_elements(By.XPATH, '//div[@class="GXS1X"]')
        try:
            menu_imgs = driver.find_elements(By.XPATH, '//div[@class="YBmM2"]')
        except: menu_imgs = [None] * len(menu_names)
        best_menu = []
        span_elements = driver.find_elements(By.CLASS_NAME, 'QM_zp')
        for index, span in enumerate(span_elements):

            svg_element = span.find_elements(By.TAG_NAME, 'svg')
            if len(svg_element): best_menu.append(True)
            else: best_menu.append(False)

        try:
            for menu_name, menu_description, menu_price, menu_img, is_best_menu in zip(menu_names, menu_descriptions, menu_prices, menu_imgs, best_menu):
                image_save_path = None
                if menu_img is not None:
                    try:
                        img_element = menu_img.find_element(By.TAG_NAME, 'img')
                        image_url = img_element.get_attribute('src')
                        image_save_path = f'/RecSys/images/{restaurant_id}_{menu_id}.jpg'
                        os.makedirs(os.path.dirname(image_save_path), exist_ok=True)
                        image_response = requests.get(image_url)
                        with open(image_save_path, 'wb') as file:
                            file.write(image_response.content)
                    except:
                        image_save_path = None
                try:
                    price_text = menu_price.text
                except:
                    price_text = None
                menu = {
                    "restaurant_id": restaurant_id,
                    "menu_id": menu_id,
                    "menu_name": menu_name.text,
                    "is_best_menu": is_best_menu,
                    "menu_description": menu_description.text,
                    "menu_price": price_text,
                    "menu_img_path": image_save_path
                }
                menu_id += 1
                RES_MENUS.append(menu)
            num_menu = len(menu_names)
        except: print(f"Error get menu")
    except: print(f"[ERROR] No menu section")
    ALL_INFO["num_menu"] = num_menu
    print(RES_MENUS)
    if len(RES_MENUS)==0: continue

    ## 사용자 리뷰 가져오기 #############################################################################################################
    try:
        review_element = driver.find_element(By.XPATH, "//span[@class='veBoZ' and text()='리뷰']")
        review_element.click() # 리뷰 탭 클릭
        button = driver.find_element(By.XPATH, "//a[text()='최신순']")
        button.click() # 최신순 버튼 클릭
        for _ in range(10):
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
        if not len(driver.find_elements(By.CLASS_NAME, "fvwqf")): # 더보기 버튼 없음
            pass
        else: # 더보기 버튼 있음
            stop_flag = False
            for i in tqdm(range(50)):
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                sleep(4)
                try:
                    more_button = driver.find_element(By.CLASS_NAME, "fvwqf")
                    more_button.click()
                    sleep(2)
                except: pass

        reviews = driver.find_elements(By.XPATH, "//li[@class='place_apply_pui EjjAW']")
        for r in reviews:
            nickname = r.find_element(By.CSS_SELECTOR, 'span.pui__uslU0d').text.strip()
            content = r.find_element(By.CSS_SELECTOR, 'div.pui__vn15t2').text.strip()
            date = r.find_element(By.CSS_SELECTOR, 'span.pui__gfuUIT').text.strip()
            pattern = r'(\d{4}년 \d{1,2}월 \d{1,2}일 \S+)'
            match = re.search(pattern, date)
            date = match.group(0)
            try:
                visit_time = driver.find_element(By.XPATH, "//span[@class='pui__V8F9nN pui__2ZezJb pui__lI1wSR']").text.strip()
            except: visit_time = None
            visit_elements = r.find_elements(By.CSS_SELECTOR, 'span.pui__gfuUIT')
            num_visit = visit_elements[1].text.strip()
            i_tags = [tag.text.strip() for tag in r.find_elements(By.CSS_SELECTOR, 'div.pui__HLNvmI')]
            i_tags = str(i_tags)
            if "+" not in i_tags: # 태그 0개, 1개일 때
                i_tag = [tag.text.strip() for tag in r.find_elements(By.CSS_SELECTOR, 'div.pui__HLNvmI')]
            else: # 태그 2개 이상일 때
                tag_button = r.find_element(By.CSS_SELECTOR, 'a.pui__jhpEyP.pui__ggzZJ8') # 태그 더보기 버튼 누르기
                driver.execute_script("arguments[0].click();", tag_button)
                sleep(1)
                i_tag = [tag.text.strip() for tag in r.find_elements(By.CSS_SELECTOR, 'div.pui__HLNvmI span.pui__jhpEyP')]
            review = {"nickname": nickname, "content": content, "date": date, \
                      "num_visit": num_visit, "visit_time": visit_time, "url": url, "i_tags": i_tag}
            RES_REVIEWS.append(review)
    except: print("[ERROR] review")
    print(RES_REVIEWS)

    # 메뉴 데이터 저장
    try:
        with open('./raw/menu.json', 'r', encoding='utf-8') as json_file:
            data = json.load(json_file) 
    except FileNotFoundError: data = []
    data.append(RES_MENUS)
    with open(f'./raw/menu.json', 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    # 음식정 데이터 저장
    try:
        with open('./raw/restaurant_info.json', 'r', encoding='utf-8') as json_file:
            data = json.load(json_file) 
    except FileNotFoundError: data = []
    data.append(ALL_INFO)
    with open('./raw/restaurant_info.json', 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    # 리뷰 데이터 저장
    try:
        with open(f'./raw/{restaurant_id}_review.json', 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
    except FileNotFoundError: data = []
    data = RES_REVIEWS
    try:
        with open(f'./raw/{restaurant_id}_review.json', 'w', encoding='utf-8') as json_file:
            json.dump(RES_REVIEWS, json_file, ensure_ascii=False, indent=4)
    except: pass
    
driver.quit()



