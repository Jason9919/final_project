import streamlit as st

# 1인세대가 아닌 전체세대에 대한 대시보드임을 강조
st.header('전체세대에 대한 대시보드도 만들어봄')

# 필요한 라이브러리 다 불러오기
import folium
from folium import GeoJson, GeoJsonTooltip
import geopandas as gpd
import pandas as pd
import branca.colormap as cm
from streamlit_folium import st_folium
import plotly.express as px

# 필요한 데이터 불러오기
gdf_gu = gpd.read_file("N3A_G01.json")
df_1 = pd.read_csv("전국1인가구_전처리.csv")

# 필요한 열만 선택하여 불러오기
df_1 = df_1[['2014년_전체세대', '2015년_전체세대', '2016년_전체세대', '2017년_전체세대', '2018년_전체세대',
             '2019년_전체세대', '2020년_전체세대', '2021년_전체세대', '2022년_전체세대', '2023년_전체세대',
             '행정구역코드', '행정시', '1인가구비율']]

# 열 이름 변경 및 행정구역코드 str 타입으로 변경 - 합칠 때 행정구역코드를 기준으로 합칠 것이기 때문임
gdf_gu = gdf_gu.rename(columns={'NAME': '행정구', 'BJCD': '행정구역코드'})
df_1['행정구역코드'] = df_1['행정구역코드'].astype(str)
gdf_gu['행정구역코드'] = gdf_gu['행정구역코드'].astype(str)

# 데이터 행정구역코드를 기준으로 합치기
## 행정구로 합치면 중복되는 구가 많아서 안 됨
gdf_gu = pd.merge(gdf_gu, df_1, on='행정구역코드', how='inner')

# 2014년부터 2023년까지의 1인세대 전처리
## 쉼표 모두 제거해주고 숫자형으로 변환
for year in range(2014, 2024):
    col_name = f"{year}년_전체세대" 
    if col_name in gdf_gu.columns:  
        gdf_gu[col_name] = gdf_gu[col_name].replace({',': ''}, regex=True)  # 콤마 제거
        gdf_gu[col_name] = pd.to_numeric(gdf_gu[col_name], errors='coerce')  # 숫자로 변환

# wide mode 를 디폴트로 바꿔줌 (너무 좁아서 잘 안 보임)
st.set_page_config(
    page_title="Wide Mode Dashboard", 
    layout="wide"  
)

# streamlit 설정 시작 (제목 등)
st.title("전체 세대 수 데이터 대시보드")
st.sidebar.title("옵션 설정")

# 연도 선택 사이드 바 만들기
available_years = [col.split("_")[0] for col in gdf_gu.columns if "전체세대" in col]
selected_year = st.sidebar.selectbox("연도 선택", sorted(available_years))
data_column = f"{selected_year}_전체세대"

# 행정구 선택 사이드 바 만들기
all_gu = gdf_gu['행정구'].unique().tolist()
selected_gu = st.sidebar.multiselect("행정구 선택 (선택하지 않으면 전체가 표시됩니다)", all_gu)

# 행정구를 선택 안 하면 전체를 선택하게 만듦
if selected_gu:
    filtered_data = gdf_gu[gdf_gu['행정구'].isin(selected_gu)]
else:
    filtered_data = gdf_gu

# 지도 시각화 시작

# legend 표시와 색의 표현을 위해 최대최소값 구함
min_value = filtered_data[data_column].min()
max_value = filtered_data[data_column].max()

# 색 지정함
colormap = cm.LinearColormap(colors=["yellow", "red"], vmin=min_value, vmax=max_value)
colormap.caption = f"{selected_year} 전체 세대 수"

# 한국의 중심 좌표와 줌 설정 조정함
korea_map = folium.Map(location=[36.5, 127.5], zoom_start=7)

# geojson 파일을 사용해서 지도 시각화 설정 조정함
## 1인세대 수의 차이를 색의 차이로 표현함
### 툴팁도 설정함 - 마우스 올리면 행정구와 1인 세대 수가 나옴
geojson_layer = GeoJson(
    filtered_data,
    style_function=lambda feature: {
        'fillColor': colormap(feature['properties'][data_column]),
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.7
    },
    tooltip=GeoJsonTooltip(
        fields=['행정구', data_column],
        aliases=['행정구:', '전체 세대 수:'],
        localize=True
    )
)
geojson_layer.add_to(korea_map)
colormap.add_to(korea_map)

# 도넛 차트 생성함
## 행정구가 너무 많아서 행정시를 기준으로 도넛 차트 만듦
grouped_data = filtered_data.groupby('행정시')[data_column].sum().reset_index()
donut_fig = px.pie(
    grouped_data,
    values=data_column,
    names='행정시',
    title=f"{selected_year} 전체세대 분포 (행정시 기준)",
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Pastel
)

# 1인 세대 증감률 계산
## 1인세대 데이터 전처리 - '년' 붙은 걸 제거하고 정수형으로 변환함
selected_year_int = int(selected_year.replace("년", ""))  

# 2013년 데이터가 없기 때문에 2014년 데이터는 증감률을 구할 수가 없음
## 따라서 2014년 이후만 증감률을 계산하게끔 코드 수정
if selected_year_int > 2014: 
    prev_year = str(selected_year_int - 1) 
    prev_data_column = f"{prev_year}년_전체세대"

# 만약 두 개 이상의 행정구를 선택했을 경우?
## 가장 처음으로 선택된 행정구에 대한 1인세대 증감률을 보여줌
    if selected_gu:
        first_selected_gu = selected_gu[0] 
        current_data = filtered_data[filtered_data['행정구'] == first_selected_gu][data_column].sum()
        if prev_data_column in gdf_gu.columns:
            previous_data = filtered_data[filtered_data['행정구'] == first_selected_gu][prev_data_column].sum()
            if previous_data > 0: 
                growth_rate = ((current_data - previous_data) / previous_data) * 100
                change_amount = current_data - previous_data  
            else:
                growth_rate = None
                change_amount = None
        else:
            growth_rate = None
            change_amount = None
        target_label = f"{first_selected_gu}의 {selected_year} 전체세대 증가율"
    
# 선택된 행정구가 없으면 전체 데이터를 기준으로 증감률을 계산함
    else: 
        total_current = filtered_data[data_column].sum()
        if prev_data_column in gdf_gu.columns:
            total_previous = filtered_data[prev_data_column].sum()
            if total_previous > 0: 
                growth_rate = ((total_current - total_previous) / total_previous) * 100
                change_amount = total_current - total_previous 
            else:
                growth_rate = None
                change_amount = None
        else:
            growth_rate = None
            change_amount = None
        target_label = f"{selected_year} 전체 전체세대 증가율"
else:
    growth_rate = None
    change_amount = None
    target_label = "2013년도 데이터 없음"

# Column 레이아웃 조정함
## 컬럼 1은 도넛 차트랑 증감률을 배치할 거라 그렇게 많은 자리가 필요없는 반면
## 컬럼 2에는 지도 시각화를 할 것이기 때문에 공간이 많이 필요함 (4:6 비율로 맞춤)
col1, col2 = st.columns([4, 6])

# 컬럼 1에 도넛 차트 및 증감률 배치함
with col1:
    st.plotly_chart(donut_fig, use_container_width=True)
    if growth_rate is not None and change_amount is not None:
        st.markdown(
            f"""
            <div style="text-align: center;">
                <h3>{target_label}</h3>
                <h1 style="color: {'green' if growth_rate > 0 else 'red'};">{growth_rate:.2f}%</h1>
                <p style="font-size: 18px; color: {'green' if change_amount > 0 else 'red'};">
                    {'+' if change_amount > 0 else ''}{change_amount:,.0f} 세대
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style="text-align: center;">
                <h3>{target_label}</h3>
                <h1 style="color: grey;">2015년부터 표시 가능</h1>
            </div>
            """,
            unsafe_allow_html=True
        )

# 컬럼 2에 지도 시각화 배치함
with col2:
    st_folium(korea_map, width=800, height=600)
