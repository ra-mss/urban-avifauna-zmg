"""
02_estadistica.py
Análisis descriptivo por zona y Distribución de Poisson para validar estadísticamente cada nodo
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson
from sqlalchemy import create_engine
import os

DB_PASS = os.environ.get("DB_PASSWORD", "tu_password")
engine  = create_engine(f"mysql+pymysql://root:{DB_PASS}@localhost/avifauna_zmg")

# 1. Estadística DESCRIPTIVA por zona
print("=" * 55)
print("ESTADÍSTICA DESCRIPTIVA POR ZONA")
print("=" * 55)

query = """
        SELECT
            z.cluster_id,
            z.lat_centroide,
            z.lon_centroide,
            r.cantidad
        FROM RegistrosDeAvistamiento r
                 JOIN Zonas z ON r.id_zona = z.id_zona \
        """
df = pd.read_sql(query, engine)

descriptivo = df.groupby("cluster_id")["cantidad"].agg(
    n_avistamientos = "count",
    media           = "mean",
    mediana         = "median",
    desv_std        = "std",
    varianza        = "var",
    minimo          = "min",
    maximo          = "max",
    total_indiv     = "sum"
).round(3)

print(descriptivo.to_string())

# 2. Distribución de POISSON por zona
print("\n" + "=" * 55)
print("DISTRIBUCIÓN DE POISSON POR ZONA (lambda = media)")
print("=" * 55)

lambdas = df.groupby("cluster_id")["cantidad"].mean()
lambda_global = df["cantidad"].mean()

print(f"\nLambda global (ciudad completa): {lambda_global:.3f}")
print(f"\n{'Zona':>5}  {'λ':>7}  {'P(X≥3)':>9}  {'P(X≥5)':>9}  {'vs Global':>10}")
print(f"{'─'*5}  {'─'*7}  {'─'*9}  {'─'*9}  {'─'*10}")

for zona_id, lam in lambdas.items():
    p_3_o_mas = 1 - poisson.cdf(2, lam)  # P(X >= 3)
    p_5_o_mas = 1 - poisson.cdf(4, lam)  # P(X >= 5)
    diferencia = lam - lambda_global
    signo = "▲" if diferencia > 0 else "▼"
    print(f"{zona_id:>5}  {lam:>7.3f}  {p_3_o_mas:>9.4f}  {p_5_o_mas:>9.4f}  "
          f"{signo}{abs(diferencia):.3f}")

# 3. Graficar Poisson de la zona con mayor lambda
zona_max = lambdas.idxmax()
lam_max  = lambdas[zona_max]

print(f"\nZona con mayor actividad: Zona {zona_max} (λ={lam_max:.3f})")
print(f"Interpretación: en promedio, {lam_max:.1f} individuos por avistamiento")

x   = np.arange(0, int(lam_max * 3) + 1)
pmf = poisson.pmf(x, lam_max)
pmf_global = poisson.pmf(x, lambda_global)

fig, ax = plt.subplots(figsize=(11, 6))
ax.bar(x - 0.2, pmf, width=0.35, color="#185FA5", alpha=0.8,
       label=f"Zona {zona_max} (λ={lam_max:.2f}) — Nodo candidato")
ax.bar(x + 0.2, pmf_global, width=0.35, color="#888780", alpha=0.6,
       label=f"Promedio ciudad (λ={lambda_global:.2f})")
ax.axvline(x=lam_max, color="#185FA5", linestyle="--", linewidth=1.5)
ax.axvline(x=lambda_global, color="#5F5E5A", linestyle="--", linewidth=1.5)
ax.set_xlabel("Individuos por avistamiento (k)", fontsize=12)
ax.set_ylabel("Probabilidad  P(X = k)", fontsize=12)
ax.set_title(f"Distribución de Poisson — Validación estadística del Nodo {zona_max}",
             fontsize=14, fontweight="bold")
ax.legend(fontsize=11)
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("poisson_zona.png", dpi=150)
print("\nGráfica guardada: poisson_zona.png")

# 4. Exportar tabla resumen a CSV (para el reporte)
descriptivo.to_csv("estadisticas_por_zona.csv")
print("Tabla guardada: estadisticas_por_zona.csv")
print("\nEstadística completa. Siguiente: python 03_mapa.py")