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
    signo = " (Más)" if diferencia > 0 else " (Menos)"
    print(f"{zona_id:>5}  {lam:>7.3f}  {p_3_o_mas:>9.4f}  {p_5_o_mas:>9.4f}  "
          f"{abs(diferencia):.3f}{signo}")

# 3. Grafica Poisson de la zona con mayor lambda

zona_max = lambdas.idxmax()
lam_max  = lambdas[zona_max]

print(f"\nZona con mayor actividad: Zona {zona_max} (λ={lam_max:.3f})")
print(f"Interpretación: en promedio, {lam_max:.1f} individuos por avistamiento")

x   = np.arange(0, int(lam_max * 3) + 1)
pmf = poisson.pmf(x, lam_max)
pmf_global = poisson.pmf(x, lambda_global)

fig, ax = plt.subplots(figsize=(13, 7))

ax.bar(x - 0.2, pmf, width=0.38,
       color="#185FA5", alpha=0.85, edgecolor="white", linewidth=0.5,
       label=f"Nodo {zona_max}  (λ = {lam_max:.2f})")
ax.bar(x + 0.2, pmf_global, width=0.38,
       color="#888780", alpha=0.65, edgecolor="white", linewidth=0.5,
       label=f"Promedio ciudad  (λ = {lambda_global:.2f})")

# Líneas de lambda
ax.axvline(x=lam_max, color="#185FA5", linestyle="--",
           linewidth=2, alpha=0.8)
ax.axvline(x=lambda_global, color="#5F5E5A", linestyle="--",
           linewidth=2, alpha=0.8)

ax.set_xlabel("Individuos por avistamiento (k)", fontsize=16, labelpad=10)
ax.set_ylabel("Probabilidad  P(X = k)", fontsize=16, labelpad=10)
ax.set_title(f"Distribución de Poisson - Nodo {zona_max}",
             fontsize=18, fontweight="bold", pad=15)
ax.tick_params(axis="both", labelsize=13)
ax.legend(fontsize=18, framealpha=0.9)
ax.grid(True, axis="y", alpha=0.3, linestyle="--")
ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
plt.savefig("poisson_zona.png", dpi=200, bbox_inches="tight")
print("Gráfica guardada: poisson_zona.png")

# 4. Exportar tabla resumen a CSV (para el reporte)

descriptivo.to_csv("estadisticas_por_zona.csv")
print("Tabla guardada: estadisticas_por_zona.csv")

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

# 6. Regresión lineal multiple
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler

print("\n" + "-" * 55)
print("Regresión multiple")
# print("Predictores: mes, zona, día de la semana, coordenadas")

df_mult = pd.read_sql("""
                      SELECT
                          MONTH(fecha) AS mes,
                          DAYOFWEEK(fecha) AS dia_semana,
                          id_zona,
                          latitud,
                          longitud,
                          cantidad
                      FROM RegistrosDeAvistamiento
                      WHERE id_zona IS NOT NULL
                        AND cantidad IS NOT NULL
                        AND cantidad < 100
                      """, engine)

X_mult = df_mult[["mes", "dia_semana", "id_zona",
                  "latitud", "longitud"]].values
y_mult = df_mult["cantidad"].values

X_mult_scaled = StandardScaler().fit_transform(X_mult)

X_tr, X_te, y_tr, y_te = train_test_split(
    X_mult_scaled, y_mult,
    test_size=0.2, random_state=42
)

modelo_mult = LinearRegression()
modelo_mult.fit(X_tr, y_tr)
y_pred_mult = modelo_mult.predict(X_te)

r2 = r2_score(y_te, y_pred_mult)
rmse = mean_squared_error(y_te, y_pred_mult) ** 0.5

print(f"R^2: {r2:.4f}")
print(f"RMSE: {rmse:.4f}")

# Importancia de cada variable (ninguna es buena tho)
features = ["Mes", "Día semana", "Zona", "Latitud", "Longitud"]
print("\nAnálisis para cada variable:")
for f, c in zip(features, modelo_mult.coef_):
    asterisco = "*" * int(abs(c) * 10)
    signo = "+" if c > 0 else "-"
    print(f" {f:12s}: {signo}{abs(c):.4f}  {asterisco}")

# Gráfica: valores reales vs predichos
plt.figure(figsize=(8, 5))
plt.scatter(y_te, y_pred_mult,
            alpha=0.4, color="#185FA5", s=15)
plt.plot([y_te.min(), y_te.max()],
         [y_te.min(), y_te.max()],
         color="#D85A30", linewidth=2, linestyle="--",
         label="Predicción ideal")
plt.xlabel("Valores reales", fontsize=12)
plt.ylabel("Valores predichos", fontsize=12)
plt.title(f"Regresión Múltiple - Real vs Predicho  (R^2={r2:.3f})",
          fontsize=13, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("regresion_multiple.png", dpi=150)
print("\nGráfica guardada: regresion_multiple.png")

print("\nEstadística completa. Siguiente: python 03_mapa.py")