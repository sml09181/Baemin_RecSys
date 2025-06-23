# BaRaemo: Baemin Recommender System

*What Should I Eat Today?🍽️*

## Project Overview
**BaRaemo** is a menu recommendation system designed to help Baemin (배달의 민족) app users easily choose what to eat.  
While current delivery apps like Baemin primarily focus on fast delivery promotions and previously ordered restaurants, **menu recommendations are missing**.  
Our system addresses this gap by providing **personalized restaurant recommendations using collaborative filtering (SVD)** and **similar menu recommendations using content-based filtering**.

This project involves real user review data collection, preprocessing, analysis, and building a recommendation system that tackles practical problems like popularity bias and item coverage.

<p align="center">
  <img src="https://github.com/user-attachments/assets/0856620a-e9ec-478e-b653-c0570e20e5e3" width="600" />
</p>


## Table of Contents
1. [Project Overview](#project-overview)
2. [Data Collection & Preprocessing](#data-collection--preprocessing)
3. [Model Architecture](#model-architecture)
4. [Problems & Solutions](#problems--solutions)
5. [Demo](#demo)
6. [Usage](#usage)
7. [Project Structure](#project-structure)
8. [Tech Stack](#tech-stack)


## Data Collection & Preprocessing
- **Data Source:** Naver Place User Reviews
- **Target Locations:** Daehyeon-dong, Yeonhui-dong, Changcheon-dong, Hongje-dong
- **Final Dataset:**
  - Users: 1,703
  - Restaurants: 327 
  - Menus w/ image: 2,422
  - Reviews: 12,405


## Model Architecture

### Step 1. Restaurant Recommendation (Collaborative Filtering)
- `SVD`-based utility matrix
- Time and weather weight integration
- Bias adjustments for popularity and obscurity

### Step 2. Menu Recommendation (Content-Based Filtering)
- Multi-modal vectors (Text + Image + Price)
- Cosine similarity for similarity computation
- `CLIP` and `ko-sroberta-multitask`-based embeddings
- Duplicate image filtering and weight tuning



## Demo

<p align="center">
  <img src="demo.gif" width="1000" />
</p>


The demo shows the full user flow:  
1️⃣ **Restaurant recommendations**  
2️⃣ **Display the best menu from the Top 5 recommended restaurants**  
3️⃣ **The user selects one menu**  
4️⃣ **Recommend the Top 3 menus similar to the selected menu**

A random user is selected in each session, and their previously visited restaurants are displayed.




## How To Run

### 1. Data Preprocessing
To preprocess the raw crawled data:

```bash
python preprocess/rest_preprocess.py    # restaurants' info 
python preprocess/menu_preprocess.py    # restaurants' menu 
python preprocess/data_preprocess.ipynb # users' history and utility matrix for SVD 
```

To build weather and visit time weight matrix for SVD:
```bash
python weight_matrix.py
```

### 2. Training & Inference
To run the step 1 - Get TOP5 restaurants and recommend their best menus:
```bash
python svd.py
```

To run Step 2 - Recommend Top 3 menus similar to the user's selected menu:
```bash
python menu_sim.py
```

### 3. Run Demo
To execute the `Gradio` demo with a user interface:

```bash
python demo.py
```

## Project Structure

```
ResSys/
│
├── crawl/                
├── data/                
├── preprocess/        
├── results/               
├── demo.py                
├── menu_sim.py         
├── svd.py               
├── weight_matrix.py     
└── README.md     
```