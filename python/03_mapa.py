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

#  3. Crear mapa base centrado en GDL
mapa = folium.Map(
    location=[20.6597, -103.3496],
    zoom_start=12,
    tiles="CartoDB positron"
)

# 4. Capa Heatmap (densidad)
calor_data = df[["latitud", "longitud", "cantidad"]].values.tolist()
heat_layer = folium.FeatureGroup(name="🌡 Mapa de calor (densidad)", show=False)
HeatMap(calor_data, radius=15, blur=20, min_opacity=0.4).add_to(heat_layer)
heat_layer.add_to(mapa)

# 5. Capa de puntos por clúster
for cluster_id in sorted(df["cluster_id"].unique()):
    color = COLORES[int(cluster_id) % len(COLORES)]
    subset = df[df["cluster_id"] == cluster_id]

    capa = folium.FeatureGroup(
        name=f"Clúster {cluster_id}  ({len(subset):,} registros)"
    )
    cluster_marker = MarkerCluster().add_to(capa)

    for _, fila in subset.iterrows():
        folium.CircleMarker(
            location=[fila["latitud"], fila["longitud"]],
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.65,
            popup=folium.Popup(
                f"{fila['nombre_comun']}. <br>"
                f"{fila['nombre_cientifico']}. <br>"
                f"Cantidad: {fila['cantidad']}. <br>"
                f"Fecha: {fila['fecha']}",
                max_width=220
            )
        ).add_to(cluster_marker)

    capa.add_to(mapa)

# 6. Marcadores de nodos (o centroides)
nodos_capa = folium.FeatureGroup(name="Nodos biológicos", show=True)

for _, zona in zonas.iterrows():
    cid   = int(zona["cluster_id"])
    color = COLORES[cid % len(COLORES)]

    # Ícono de hoja para el nodo
    icono = folium.Icon(color="green", icon="leaf", prefix="fa")

    popup_html = f"""
<div style="font-family:sans-serif; font-size:13px; min-width:180px;">
  <b>Nodo #{cid}</b><br><br>
  Lat: {zona['lat_centroide']:.5f}<br>
  Lon: {zona['lon_centroide']:.5f}<br><br>
  Registros: {int(zona['num_registros']):,}<br>
  Punto de máxima concentración de fauna
</div> """

    folium.Marker(
        location=[zona["lat_centroide"], zona["lon_centroide"]],
        icon=icono,
        popup=folium.Popup(popup_html, max_width=260),
        tooltip=f"Nodo {cid} — clic para detalles"
    ).add_to(nodos_capa)

    # Círculo de radio de influencia del nodo (~1.5km)
    folium.Circle(
        location=[zona["lat_centroide"], zona["lon_centroide"]],
        radius=1500,
        color=color,
        fill=True,
        fill_opacity=0.08,
        weight=2,
    ).add_to(nodos_capa)

nodos_capa.add_to(mapa)

# 7. Control de capas y guardar
folium.LayerControl(collapsed=False).add_to(mapa)

# Título superpuesto en el mapa
titulo_html = """

  Nodos biológicos — Zona Metropolitana de Guadalajara

"""
mapa.get_root().html.add_child(folium.Element(titulo_html))

output_file = "nodos_biologicos_zmg.html"
mapa.save(output_file)
print(f"\nMapa guardado: {output_file}")
print("Ábrelo en tu navegador para ver los resultados interactivos.")
print("\nPipeline completo.")