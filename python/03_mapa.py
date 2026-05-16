"""
03_mapa.py
Genera el mapa HTML:
  - Puntos de avistamiento coloreados por clúster
  - Marcadores de centroides (Nodos)
  - Popup informativo por zona
  - Control de capas para mostrar/ocultar clústeres
"""
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from sqlalchemy import create_engine
from scipy.spatial import ConvexHull
import numpy as np
import os

DB_PASS = os.environ.get("DB_PASSWORD", "tu_password")
engine  = create_engine(f"mysql+pymysql://root:{DB_PASS}@localhost/avifauna_zmg")

# 1. Cargar datos
print("Cargando datos para el mapa...")
df = pd.read_sql("""
                 SELECT r.latitud, r.longitud, r.nombre_comun,
                        r.nombre_cientifico, r.fecha, r.cantidad, z.cluster_id
                 FROM RegistrosDeAvistamiento r
                          JOIN Zonas z ON r.id_zona = z.id_zona
                 """, engine)

zonas = pd.read_sql("SELECT * FROM Zonas", engine)
print(f"  Avistamientos: {len(df):,} | Zonas: {len(zonas)}")

#  2. Paleta de colores por clúster
COLORES = [
    "#185FA5",  # azul
    "#1D9E75",  # teal
    "#D85A30",  # coral
    "#D4537E",  # rosa
    "#BA7517",  # ámbar
    "#534AB7",  # púrpura
    "#3B6D11",  # verde
    "#A32D2D",  # rojo
    "#5F5E5A",  # gris
]

#  3. Crear mapa base centrado en ZMG
mapa = folium.Map(
    location=[20.5597, -103.3496],
    zoom_start=10,
    tiles="CartoDB Voyager"
)

# 4. Capa Heatmap (densidad)
calor_data = df[["latitud", "longitud", "cantidad"]].values.tolist()
heat_layer = folium.FeatureGroup(name="Mapa de calor (densidad)", show=False)
HeatMap(calor_data, radius=15, blur=20, min_opacity=0.4).add_to(heat_layer)
heat_layer.add_to(mapa)

# 5. Polígonos convexos por clúster
poligonos_capa = folium.FeatureGroup(name="Polígonos de clústeres", show=True)

for cluster_id in sorted(df["cluster_id"].unique()):
    color  = COLORES[int(cluster_id) % len(COLORES)]
    subset = df[df["cluster_id"] == cluster_id][["latitud", "longitud"]].values

    # Necesitamos mínimo 3 puntos para formar un polígono
    if len(subset) < 3:
        continue

    try:
        hull  = ConvexHull(subset)
        # Los vértices del polígono convexo en orden
        puntos_hull = subset[hull.vertices].tolist()
        # Folium necesita [lat, lon]
        puntos_hull = [[p[0], p[1]] for p in puntos_hull]

        folium.Polygon(
            locations=puntos_hull,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.12,
            tooltip=f"Clúster {cluster_id} — {len(subset):,} registros"
        ).add_to(poligonos_capa)

    except Exception as e:
        print(f"No se pudo generar polígono para clúster {cluster_id}: {e}")

poligonos_capa.add_to(mapa)

# 6. Puntos individuales por clúster
for cluster_id in sorted(df["cluster_id"].unique()):
    color  = COLORES[int(cluster_id) % len(COLORES)]
    subset = df[df["cluster_id"] == cluster_id]

    capa            = folium.FeatureGroup(
        name=f"Clúster {cluster_id}  ({len(subset):,} registros)"
    )
    cluster_marker  = MarkerCluster().add_to(capa)

    for _, fila in subset.iterrows():
        folium.CircleMarker(
            location=[fila["latitud"], fila["longitud"]],
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.65,
            popup=folium.Popup(
                f"<b>{fila['nombre_comun']}</b><br>"
                f"<i>{fila['nombre_cientifico']}</i><br>"
                f"Cantidad: {fila['cantidad']}<br>"
                f"Fecha: {fila['fecha']}",
                max_width=220
            )
        ).add_to(cluster_marker)

    capa.add_to(mapa)

# 7. Marcadores de nodos biológicos

nodos_capa = folium.FeatureGroup(name="Nodos biológicos", show=True)

for _, zona in zonas.iterrows():
    cid   = int(zona["cluster_id"])
    color = COLORES[cid % len(COLORES)]

    popup_html = f"""
    <div style="font-family:sans-serif; font-size:13px; min-width:180px;">
      <b>Nodo #{cid}</b><br><br>
      Lat: {zona['lat_centroide']:.5f}<br>
      Lon: {zona['lon_centroide']:.5f}<br><br>
      Registros: {int(zona['num_registros']):,}<br>
      Punto de máxima concentración de fauna
    </div>
    """

    folium.Marker(
        location=[zona["lat_centroide"], zona["lon_centroide"]],
        icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
        popup=folium.Popup(popup_html, max_width=260),
        tooltip=f"Nodo {cid} — clic para detalles"
    ).add_to(nodos_capa)

nodos_capa.add_to(mapa)

# 8. Control de capas y guardar
folium.LayerControl(collapsed=False).add_to(mapa)

# Título superpuesto en el mapa
titulo_html = """

  Nodos biológicos en la Zona Metropolitana de Guadalajara

"""
mapa.get_root().html.add_child(folium.Element(titulo_html))

output_file = "nodos_biologicos_zmg.html"
mapa.save(output_file)
print(f"\nMapa guardado: {output_file}")
print("Ábrelo en tu navegador para ver los resultados interactivos.")
print("\nPipeline completo.")