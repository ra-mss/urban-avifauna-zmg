"""
01_kmeans.py
Corre K-Means sobre los datos de MySQL y guarda los centroides
(Zonas) de vuelta en la base de datos.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

# ── Conexión a MySQL ────────────────────────────────────────────
import os
DB_PASS = os.environ.get("DB_PASSWORD", "tu_password")
engine  = create_engine(f"mysql+pymysql://root:{DB_PASS}@localhost/avifauna_zmg")

# ── 1. Cargar coordenadas desde la base de datos ────────────────
print("Cargando datos de MySQL...")
df = pd.read_sql(
    "SELECT id_registro, latitud, longitud FROM RegistrosDeAvistamiento",
    engine
)
print(f"  Registros cargados: {len(df):,}")

# ── 2. Normalizar coordenadas (CRUCIAL para K-Means) ───────────
#   Sin normalizar, la escala de lat y lon podría distorsionar clusters
scaler = StandardScaler()
X = scaler.fit_transform(df[["latitud", "longitud"]])

# ── 3. Método del Codo para encontrar K óptimo ─────────────────
print("\nCalculando Método del Codo (K de 2 a 14)...")
inercias = []
rango_k  = range(2, 15)

for k in rango_k:
    modelo = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
    modelo.fit(X)
    inercias.append(modelo.inertia_)

# Graficar
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(list(rango_k), inercias, "bo-", linewidth=2, markersize=8)
ax.set_xlabel("Número de Clústeres (K)", fontsize=13)
ax.set_ylabel("Inercia (suma de distancias²)", fontsize=13)
ax.set_title("Método del Codo — Nodos Biológicos ZMG", fontsize=15, fontweight="bold")
ax.grid(True, alpha=0.3)

# Marca visual en el codo (ajusta el valor después de ver la gráfica)
K_OPTIMO = 5   # <-- CAMBIA ESTE VALOR según el codo que veas en la gráfica
ax.axvline(x=K_OPTIMO, color="red", linestyle="--", linewidth=2,
           label=f"K óptimo = {K_OPTIMO}")
ax.legend(fontsize=12)
plt.tight_layout()
plt.savefig("elbow_method.png", dpi=150)
print(f"  Gráfica guardada: elbow_method.png")
print(f"  → Abre la imagen y confirma que K={K_OPTIMO} es el codo correcto.")

# ── 4. Entrenar modelo final con K óptimo ──────────────────────
print(f"\nEntrenando K-Means con K={K_OPTIMO}...")
modelo_final = KMeans(n_clusters=K_OPTIMO, random_state=42, n_init=10, max_iter=300)
df["cluster_id"] = modelo_final.fit_predict(X)

print(f"Modelo entrenado. Distribución de registros por clúster:")
print(df["cluster_id"].value_counts().sort_index().to_string())

# ── 5. Calcular centroides en coordenadas reales (desnormalizar) ─
centroides_norm = modelo_final.cluster_centers_
centroides_real = scaler.inverse_transform(centroides_norm)

conteos = df.groupby("cluster_id").size().reset_index(name="num_registros")

zonas_df = pd.DataFrame({
    "cluster_id":    range(K_OPTIMO),
    "lat_centroide": centroides_real[:, 0],
    "lon_centroide": centroides_real[:, 1],
}).merge(conteos, on="cluster_id")

print("\nCentroides identificados (Nodos Biológicos Invisibles):")
print(zonas_df.to_string(index=False))

# ── 6. Guardar centroides en MySQL (tabla Zonas) ────────────────
print("\nGuardando zonas en MySQL...")
with engine.connect() as con:
    con.execute(text("DELETE FROM Zonas"))  # Limpia antes de reinsertar
    con.commit()

zonas_df.to_sql("Zonas", engine, if_exists="append", index=False)
print("Zonas guardadas en MySQL.")

# ── 7. Actualizar id_zona en cada registro (asignación de cluster) ─
print("Asignando id_zona a cada registro...")
# Primero obtenemos el id_zona real (auto_increment) de MySQL
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
print("\nK-Means completo. Siguiente: python 02_estadistica.py")