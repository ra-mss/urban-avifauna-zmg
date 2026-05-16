"""
Esto corre K-Means en los datos de MySQL y guarda los centroides en la database
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

# Conexión a MySQL
import os
DB_PASS = os.environ.get("DB_PASSWORD", "tu_password")
engine  = create_engine(f"mysql+pymysql://root:{DB_PASS}@localhost/avifauna_zmg")

# 1. Cargar coordenadas desde la base de datos
print("Cargando datos de MySQL")
df = pd.read_sql(
    "SELECT id_registro, latitud, longitud FROM RegistrosDeAvistamiento",
    engine
)
print(f"Registros cargados: {len(df):,}")

# 2. Normalizar coordenadas
scaler = StandardScaler()
X = scaler.fit_transform(df[["latitud", "longitud"]])

# 3. Metodo del codo para encontrar el K óptimo
print("\nCalculando método del codo (K de 2 a 14)...")
inercias = []
rango_k = range(2, 15)

for k in rango_k:
    modelo = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
    modelo.fit(X)
    inercias.append(modelo.inertia_)

# Graficar
fig, ax = plt.subplots(figsize=(12, 7))
ax.plot(list(rango_k), inercias, "o-",
        color="#185FA5", linewidth=3, markersize=10,
        markerfacecolor="white", markeredgewidth=2.5)

ax.set_xlabel("Número de clústeres (K)", fontsize=16, labelpad=10)
ax.set_ylabel("Inercia (suma de distancias²)", fontsize=16, labelpad=10)
ax.set_title("Método del codo", fontsize=20, fontweight="bold", pad=15)
ax.tick_params(axis="both", labelsize=13)
ax.set_xticks(list(rango_k))
ax.legend(fontsize=13)
ax.grid(True, alpha=0.3, linestyle="--")
ax.spines[["top", "right"]].set_visible(False)

# Marcaje en el codo
K_OPTIMO = 5 # <- CAMBIAR ESTE VALOR SEGUN LO QUE VEAMOS EN LA GRAFICA
ax.plot(K_OPTIMO, inercias[K_OPTIMO - 2], "o",
        color="#D85A30", markersize=16, zorder=5,
        label=f"K óptimo = {K_OPTIMO}")
ax.axvline(x=K_OPTIMO, color="#D85A30", linestyle="--",
           linewidth=2, alpha=0.7)



plt.tight_layout()
plt.savefig("elbow_method.png", dpi=200, bbox_inches="tight")
print(f"Gráfica guardada: elbow_method.png")
print(f"Abre la imagen y confirma que K={K_OPTIMO} es el codo correcto.")

# 4. Entrenar modelo final con el K óptimo
print(f"\nEntrenando K-Means con K={K_OPTIMO}...")
modelo_final = KMeans(n_clusters=K_OPTIMO, random_state=42, n_init=10, max_iter=300)
df["cluster_id"] = modelo_final.fit_predict(X)

print(f"Iteraciones reales hasta convergencia: {modelo_final.n_iter_}")

print(f"Modelo entrenado. Distribución de registros por clúster:")
print(df["cluster_id"].value_counts().sort_index().to_string())

# 5. Calcular centroides en coordenadas reales (desnormalizar (?))
centroides_norm = modelo_final.cluster_centers_
centroides_real = scaler.inverse_transform(centroides_norm)

conteos = df.groupby("cluster_id").size().reset_index(name="num_registros")

zonas_df = pd.DataFrame({
    "cluster_id": range(K_OPTIMO),
    "lat_centroide": centroides_real[:, 0],
    "lon_centroide": centroides_real[:, 1],
}).merge(conteos, on="cluster_id")

print("\nCentroides identificados (Nodos biológicos):")
print(zonas_df.to_string(index=False))

# 6. Guardar centroides en MySQL (tabla Zonas)
print("\nGuardando zonas en MySQL...")
with engine.connect() as con:
    con.execute(text("DELETE FROM Zonas"))  # limpia antes de ingresar
    con.commit()

zonas_df.to_sql("Zonas", engine, if_exists="append", index=False)
print("Zonas guardadas en MySQL :D")

# 7. Actualizar id_zona en cada registro (asignación de cluster)
print("Asignando id_zona a cada registro...")
# Obtiene el id_zona real (auto_increment) desde mySQL
zonas_mysql = pd.read_sql("SELECT id_zona, cluster_id FROM Zonas", engine)
df = df.merge(zonas_mysql, on="cluster_id")

with engine.connect() as con:
    for _, fila in df.iterrows():
        con.execute(
            text("UPDATE RegistrosDeAvistamiento SET id_zona=:z WHERE id_registro=:r"),
            {"z": int(fila["id_zona"]), "r": int(fila["id_registro"])}
        )
    con.commit()

print("id_zona asignado a todos los registros.")
print("\nK-Means completo")

# DBSCAN

from sklearn.cluster import DBSCAN

EPS_GRADOS = 100 / 111_000 # 100 metros en grados decimales aprox 0.0045

dbscan = DBSCAN(eps=EPS_GRADOS, min_samples = 5, algorithm = 'ball_tree', metric = 'haversine') # Haversine requiere radianes (!)
coords_rad = np.radians(df[['latitud', 'longitud']].values)
df['cluster_dbscan'] = dbscan.fit_predict(coords_rad)

# Resumen
n_clusters = len(set(df['cluster_dbscan'])) - (1 if -1 in df['cluster_dbscan'].values else 0)
n_ruido = (df['cluster_dbscan'] == -1).sum()
print(f"Clústers encontrados: {n_clusters}")
print(f"Ruido encontrado (puntos -1): {n_ruido} ({n_ruido/len(df)*100:.1f}%)")

# Centroides DBSCAN
centroides_dbscan = (
    df[df['cluster_dbscan'] != -1].groupby('cluster_dbscan')[['latitud', 'longitud']]
    .mean().reset_index()
    .rename(columns={'cluster_dbscan': 'cluster_id',
                     'latitud': 'lat_centroide',
                     'longitud': 'lon_centroide'})
)
centroides_dbscan['num_registros'] = (
    df[df['cluster_dbscan'] != -1].groupby('cluster_dbscan').size().values
)

print("\nCentroides DBSCAN:")
print(centroides_dbscan.to_string(index=False))

# Guardar en MySQL (en otra tabla, no en la de K-means)
with engine.connect() as con:
    con.execute(text(
        "DROP TABLE IF EXISTS Zonas_DBSCAN"))
    con.commit()

centroides_dbscan.to_sql('Zonas_DBSCAN', engine, if_exists='append', index= False)

# Guarda etiquetas en CSV (para que pasen al mapa de folium kinda)

df[['latitud', 'longitud', 'cluster_id', 'cluster_dbscan']].to_csv(
    'avistamientos_clusterizados.csv', index=False)

print("\nDatos guardados en Zonas_DBSCAN (MySQL) y avistamientos_clusterizados.csv")

# Gráfica comparativa de K-means vs DBSCAN
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

COLORES = ["#185FA5","#1D9E75","#D85A30","#D4537E","#BA7517"]

for cid in sorted(df["cluster_id"].unique()):
    sub = df[df["cluster_id"] == cid]
    ax1.scatter(sub["longitud"], sub["latitud"],
                s=8, alpha=0.5, color=COLORES[cid % len(COLORES)],
                label=f"Clúster {cid}")
ax1.set_title(f"K-Means (K={K_OPTIMO})", fontsize=13, fontweight="bold")
ax1.set_xlabel("Longitud"); ax1.set_ylabel("Latitud")
ax1.legend(markerscale=2, fontsize=9)

colores_db = plt.cm.tab10.colors
for cid in sorted(df["cluster_dbscan"].unique()):
    sub = df[df["cluster_dbscan"] == cid]
    col = "gray" if cid == -1 else colores_db[cid % 10]
    lbl = "Ruido" if cid == -1 else f"D{cid}"
    ax2.scatter(sub["longitud"], sub["latitud"],
                s=8, alpha=0.5, color=col, label=lbl)
ax2.set_title(f"DBSCAN ({n_clusters} clústeres · {n_ruido} ruido)",
              fontsize=13, fontweight="bold")
ax2.set_xlabel("Longitud"); ax2.set_ylabel("Latitud")
ax2.legend(markerscale=2, fontsize=9, ncol=2)

plt.suptitle("Comparación K-Means vs DBSCAN - Nodos biológicos ZMG",
             fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("comparacion_modelos.png", dpi=150)
print("Gráfica guardada: comparacion_modelos.png")

print("\nSiguiente: python 02_estadistica.py")