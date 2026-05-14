"""
Análisis descriptivo por zona, regresión lineal y distribución de poisson
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson
from sqlalchemy import create_engine
import os

DB_PASS = os.environ.get("DB_PASSWORD", "tu_password")
engine  = create_engine(f"mysql+pymysql://root:{DB_PASS}@localhost/avifauna_zmg")

# 1. Estadística descriptiva por zona
print("-" * 55)
print("Estadística descriptiva por zona")

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
    media = "mean",
    mediana = "median",
    desv_std = "std",
    varianza = "var",
    minimo = "min",
    maximo = "max",
    total_indiv = "sum"
).round(3)

print(descriptivo.to_string())

# 2. Distribución de poisson por zona
print("\n" + "-" * 55)
print("Distribución de Poisson por zona (lambda = media)")

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

# 3. Grafica Poisson de la zona con mayor lambda

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

# 5. Regresión lineal

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

print("\n" + "-" * 55)
print("Regresión lineal - Mes vs. Cantidad de individuos")

# Variable independiente X: mes del año (1 a 12)
# Variable dependiente y: cantidad de individuos
df_reg = pd.read_sql("""
                     SELECT MONTH(fecha) AS mes, cantidad
                     FROM RegistrosDeAvistamiento
                     WHERE cantidad IS NOT NULL
                     """, engine)

X_reg = df_reg[["mes"]].values
y_reg = df_reg["cantidad"].values

modelo_lr = LinearRegression()
modelo_lr.fit(X_reg, y_reg)

y_pred = modelo_lr.predict(X_reg)
r2 = r2_score(y_reg, y_pred)
rmse = mean_squared_error(y_reg, y_pred) ** 0.5

print(f"Coeficiente (pendiente): {modelo_lr.coef_[0]:.4f}")
print(f"Intercepto: {modelo_lr.intercept_:.4f}")
print(f"R^2 score: {r2:.4f}")
print(f"RMSE: {rmse:.4f}")
print(f"\nInterpretación: por cada mes que avanza el año,")
print(f"la cantidad de individuos cambia en {modelo_lr.coef_[0]:.3f} unidades.")

# Gráfica
meses_nombres = ["Ene","Feb","Mar","Abr","May","Jun",
                 "Jul","Ago","Sep","Oct","Nov","Dic"]
medias_mes = df_reg.groupby("mes")["cantidad"].mean()

plt.figure(figsize=(11, 5))
plt.scatter(df_reg["mes"], df_reg["cantidad"],
            alpha=0.15, color="#888780", s=10, label="Registros reales")
plt.plot(range(1, 13), modelo_lr.predict([[m] for m in range(1, 13)]),
         color="#185FA5", linewidth=2.5, label=f"Regresión lineal (R^2={r2:.3f})")
plt.plot(medias_mes.index, medias_mes.values,
         "o--", color="#D85A30", linewidth=1.5, label="Media mensual real")
plt.xticks(range(1, 13), meses_nombres)
plt.xlabel("Mes del año", fontsize=12)
plt.ylabel("Individuos por avistamiento", fontsize=12)
plt.title("Regresión Lineal - Estacionalidad de avistamientos en la ZMG",
          fontsize=14, fontweight="bold")
plt.legend(fontsize=11)
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("regresion_lineal.png", dpi=150)
print("Gráfica guardada: regresion_lineal.png")

# 6. Regresión logística

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (classification_report,
                             confusion_matrix,
                             ConfusionMatrixDisplay)

print("\n" + "-" * 55)
print("Regresión logística - ¿Podría ser un avistamiento de alta densidad?")

df_log = pd.read_sql("""
                     SELECT MONTH(fecha) AS mes,
                         id_zona,
                         cantidad
                     FROM RegistrosDeAvistamiento
                     WHERE id_zona IS NOT NULL AND cantidad IS NOT NULL
                     """, engine)

# Variable objetivo es binaria: 1 si cantidad > promedio, 0 si no (suponiendo que esto hace sentido)
umbral = df_log["cantidad"].mean()
df_log["alta_densidad"] = (df_log["cantidad"] > umbral).astype(int)

print(f"Umbral (media global): {umbral:.2f} individuos")
print(f"Alta densidad (1): {df_log['alta_densidad'].sum():,} registros")
print(f"Baja densidad (0): {(df_log['alta_densidad']==0).sum():,} registros")

X_log = df_log[["mes", "id_zona"]].values
y_log = df_log["alta_densidad"].values

X_train, X_test, y_train, y_test = train_test_split(
    X_log, y_log, test_size=0.2, random_state=42)

modelo_log = LogisticRegression(max_iter=200)
modelo_log.fit(X_train, y_train)
y_pred_log = modelo_log.predict(X_test)

print("\nReporte de clasificación:")
print(classification_report(y_test, y_pred_log,
                            target_names=["Baja densidad","Alta densidad"]))

# Matriz de confusión
cm  = confusion_matrix(y_test, y_pred_log)
fig, ax = plt.subplots(figsize=(6, 5))
ConfusionMatrixDisplay(cm, display_labels=["Baja","Alta"]).plot(
    ax=ax, colorbar=False, cmap="Blues"
)
ax.set_title("Regresión logística - Matriz de confusión\n",
             fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig("regresion_logistica.png", dpi=150)
print("Gráfica guardada: regresion_logistica.png")