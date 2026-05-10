package com.biodiversidad.service;

import com.biodiversidad.model.Avistamiento;
import java.time.LocalDate;
import java.util.*;
import java.util.List;
import java.util.Set;
import java.util.ArrayList;
import java.util.HashSet;

public class DataAccumulatorService {
    private final EBirdAPIClient api;
    private final ETLService     etl;

    // Fechas históricas de alta actividad migratoria en Jalisco
    private static final LocalDate[] FECHAS_HISTORICAS = {
            // Primavera 2025
            LocalDate.of(2025, 3, 21),
            LocalDate.of(2025, 4, 15),
            LocalDate.of(2025, 5, 10),
            // Verano 2025
            LocalDate.of(2025, 6, 21),
            LocalDate.of(2025, 7, 15),
            LocalDate.of(2025, 8, 10),
            // Otoño 2025
            LocalDate.of(2025, 9, 22),
            LocalDate.of(2025, 10, 15),
            LocalDate.of(2025, 11, 10),
            // Invierno 2025-2026
            LocalDate.of(2025, 12, 21),
            LocalDate.of(2026, 1, 15),
            LocalDate.of(2026, 2, 10),
            // Primavera 2026 (a la fecha)
            LocalDate.of(2026, 3, 21),
            LocalDate.of(2026, 4, 15),
    };

    public DataAccumulatorService(EBirdAPIClient api, ETLService etl) {
        this.api = api;
        this.etl = etl;
    }

    public void ejecutar() throws Exception {
        Set<String> clavesVistas = new HashSet<>();
        List<Avistamiento> acumulados = new ArrayList<>();

        // Llamada 1: últimos 30 días en MX-JAL
        System.out.println("\n[1/16] Observaciones recientes MX-JAL...");
        agregarNuevos(api.fetchRecientes(30), acumulados, clavesVistas);

        // Llamada 2: radio 50km alrededor del centro de GDL
        System.out.println("\n[2/16] Observaciones radio 50km (GDL centro)...");
        agregarNuevos(
                api.fetchPorRadio(20.6597, -103.3496, 50),
                acumulados, clavesVistas
        );

        // Llamadas 3-16: fechas históricas
        for (int i = 0; i < FECHAS_HISTORICAS.length; i++) {
            System.out.printf("%n[%d/16] Histórico: %s...%n",
                    i + 3, FECHAS_HISTORICAS[i]);
            agregarNuevos(
                    api.fetchHistorico(FECHAS_HISTORICAS[i]),
                    acumulados, clavesVistas
            );
            Thread.sleep(350); // Rate limiting: ~2.8 req/seg (límite eBird ~100/min)
        }

        System.out.printf("  Total registros únicos acumulados: %,d%n", acumulados.size());

        // Cargar en MySQL
        System.out.println("\n[MYSQL] Iniciando carga en base de datos...");
        etl.cargar(acumulados);
        etl.poblarEspecies();
    }

    // Agrega solo los registros que no hayamos visto antes (O(1) con HashSet)
    private void agregarNuevos(List<Avistamiento> nuevos,
                               List<Avistamiento> acumulados,
                               Set<String> clavesVistas) {
        int antes = acumulados.size();
        for (Avistamiento a : nuevos) {
            String clave = a.getNombreCientifico()
                    + "|" + a.getLatitud()
                    + "|" + a.getLongitud()
                    + "|" + a.getFecha();
            if (clavesVistas.add(clave)) {
                acumulados.add(a);
            }
        }
        System.out.println("Nuevos agregados: " + (acumulados.size() - antes));
    }
}
