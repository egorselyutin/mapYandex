import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="ГИС Мониторинг")

st.title("🗺️ Высокопроизводительный ГИС модуль мониторинга")
st.caption("Оптимизированный рендеринг через ymaps.ObjectManager")

# =============================================================================
# ЗАГРУЗКА ДАННЫХ
# =============================================================================
@st.cache_data
def load_terminal_data():
    # Приоритет файлов: Терминалы_2 -> Координаты -> Терминалы
    files = ["Терминалы_2.xlsx", "Координаты.xlsx", "Терминалы.xlsx"]
    file_name = next((f for f in files if os.path.exists(f)), None)
        
    if file_name:
        try:
            df = pd.read_excel(file_name)
            
            # Приводим названия колонок координат к единому стандарту
            rename_dict = {}
            if "Широта" in df.columns: rename_dict["Широта"] = "lat"
            if "Долгота" in df.columns: rename_dict["Долгота"] = "lon"
            df = df.rename(columns=rename_dict)
            
            # Проверка критических данных
            if "lat" not in df.columns or "lon" not in df.columns:
                st.error(f"Ошибка: В файле '{file_name}' не найдены обязательные колонки 'Широта' и 'Долгота'!")
                return pd.DataFrame(columns=["lat", "lon"])
                
            df["lat"] = pd.to_numeric(df["lat"], errors='coerce')
            df["lon"] = pd.to_numeric(df["lon"], errors='coerce')
            df = df.dropna(subset=["lat", "lon"])
            
            # Если есть адрес, сохраняем его, если нет — создаем пустую колонку
            address_col = next((c for c in df.columns if any(x in str(c).lower() for x in ["адрес", "address", "место"])), None)
            if address_col:
                df = df.rename(columns={address_col: "Адрес"})
            else:
                df["Адрес"] = None
                
            return df
        except Exception as e:
            st.error(f"Ошибка при чтении файла {file_name}: {e}")
            return pd.DataFrame(columns=["lat", "lon", "Адрес"])
    else:
        st.error("Файлы данных не найдены в директории проекта!")
        return pd.DataFrame(columns=["lat", "lon", "Адрес"])

# =============================================================================
# ГЕНЕРАЦИЯ ДАННЫХ ДЛЯ КАРТЫ
# =============================================================================
@st.cache_data
def build_geojson_collection(df):
    features = []
    for idx, row in enumerate(df.itertuples()):
        # Логика: если адрес есть — показываем, если нет — только координаты
        addr_text = getattr(row, "Адрес", None)
        has_address = pd.notna(addr_text) and str(addr_text).strip().lower() != "nan"
        
        balloon_body = f"<div style='font-size:12px; font-family:Arial;'>"
        if has_address:
            balloon_body += f"<b>Адрес:</b> {str(addr_text).strip()}<br>"
        balloon_body += f"<b>Координаты:</b> {row.lat:.5f}, {row.lon:.5f}</div>"
            
        features.append({
            "type": "Feature",
            "id": idx,
            "geometry": {
                "type": "Point",
                "coordinates": [float(row.lat), float(row.lon)]
            },
            "properties": {
                "balloonContentHeader": f"<b>Терминал №{idx+1}</b>",
                "balloonContentBody": balloon_body,
                "hintContent": f"Терминал №{idx+1}" + (f" ({addr_text})" if has_address else "")
            }
        })
    return {"type": "FeatureCollection", "features": features}

# --- Остальная часть скрипта (Загрузка данных, UI, JS) остается без изменений ---
df_terminals = load_terminal_data()

if not df_terminals.empty:
    median_lat = float(df_terminals["lat"].median())
    median_lon = float(df_terminals["lon"].median())
else:
    median_lat, median_lon = 56.0153, 92.8932

geojson_data = build_geojson_collection(df_terminals)
geojson_json = json.dumps(geojson_data, ensure_ascii=False)
points_heatmap_json = json.dumps(df_terminals[["lat", "lon"]].values.tolist())

# UI Sidebar
st.sidebar.header("🗺️ Управление слоями")
show_terminals = st.sidebar.checkbox("🟢 Реальные данные: Кластеры", value=True)
show_method_2  = st.sidebar.checkbox("🔵 Радиусы покрытия", value=False)
show_method_3  = st.sidebar.checkbox("🔥 Тепловая карта", value=False)

# HTML/JS Map (код внутри остается прежним, использующим переменную geojson_json)
yandex_highperf_html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><script src="https://api-maps.yandex.ru/2.1/?lang=ru_RU&modules=Heatmap"></script></head>
<body>
    <div id="map" style="width:100%; height:700px;"></div>
    <script type="text/javascript">
        ymaps.ready(init);
        function init() {{
            var myMap = new ymaps.Map("map", {{ center: [{median_lat}, {median_lon}], zoom: 8 }});
            var geojsonData = {geojson_json};
            var objectManager = new ymaps.ObjectManager({{ clusterize: true }});
            objectManager.add(geojsonData);
            myMap.geoObjects.add(objectManager);
        }}
    </script>
</body>
</html>
"""

with st.container():
    components.html(yandex_highperf_html, height=700)