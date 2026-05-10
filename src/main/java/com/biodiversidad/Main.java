package com.biodiversidad;

import com.biodiversidad.service.*;
import java.sql.*;

public class Main {

    public static void main(String[] args) {

        // ── Validaciones de entorno ─────────────────────────────────
        String apiKey = System.getenv("EBIRD_API_KEY");
        String dbPass = System.getenv("DB_PASSWORD");

        if (apiKey == null || apiKey.isBlank()) {
            System.err.println(" Falta EBIRD_API_KEY.");
            System.err.println(" Ejecuta: export EBIRD_API_KEY=tu_clave");
            System.exit(1);
        }

        String dbUrl = "jdbc:mysql://localhost:3306/avifauna_zmg"
                + "?useSSL=false&serverTimezone=UTC";
        String dbUser = "root";

        System.out.println("Nodos biológicos - ZMG ETL");

        try (Connection conn = DriverManager.getConnection(dbUrl, dbUser, dbPass)) {
            System.out.println("Conexión MySQL establecida.\n");

            EBirdAPIClient apiClient = new EBirdAPIClient();
            ETLService etlService = new ETLService(conn);
            DataAccumulatorService acumulator =
                    new DataAccumulatorService(apiClient, etlService);

            acumulator.ejecutar();

            System.out.println("\n Pipeline ETL completado.");
            System.out.println("   Siguiente paso: ejecuta python/01_kmeans.py");

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
