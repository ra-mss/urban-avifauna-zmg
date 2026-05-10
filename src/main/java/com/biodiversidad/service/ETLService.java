package com.biodiversidad.service;

import com.biodiversidad.model.Avistamiento;
import java.sql.*;
import java.util.List;
import java.util.List;
import java.util.Set;
import java.util.ArrayList;
import java.util.HashSet;

public class ETLService {
    // Cuántos registros se envían juntos en cada lote de SQL
    private static final int BATCH_SIZE = 500;
    private final Connection conn;

    public ETLService(Connection conn) {
        this.conn = conn;
    }

    /**
     CARGAR: Inserta la lista en MySQL en lotes (O(n), no O(n²)). ON DUPLICATE KEY UPDATE evita errores de repetidos
     */
    public void cargar(List<Avistamiento> avistamientos) throws SQLException {
        String sql = """
            INSERT INTO RegistrosDeAvistamiento
              (nombre_cientifico, nombre_comun, latitud, longitud, fecha, cantidad, loc_nombre)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE
              cantidad   = VALUES(cantidad),
              loc_nombre = VALUES(loc_nombre)
            """;

        // Desactiva autocommit: una sola transacción para todo el lote
        conn.setAutoCommit(false);

        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            int contador = 0;

            for (Avistamiento a : avistamientos) {
                ps.setString(1, a.getNombreCientifico());
                ps.setString(2, a.getNombreComun());
                ps.setDouble(3, a.getLatitud());
                ps.setDouble(4, a.getLongitud());
                ps.setDate  (5, java.sql.Date.valueOf(a.getFecha()));
                ps.setInt   (6, a.getCantidad());
                ps.setString(7, a.getLocNombre());
                ps.addBatch();

                if (++contador % BATCH_SIZE == 0) {
                    ps.executeBatch();
                    System.out.printf("[CARGAR] %,d registros insertados...%n", contador);
                }
            }
            ps.executeBatch();  // Lote residual
            conn.commit();
            System.out.printf("Carga completa: %,d registros totales.%n", contador);

        } catch (SQLException e) {
            conn.rollback();
            System.err.println("Error en carga, rollback ejecutado.");
            throw e;
        } finally {
            conn.setAutoCommit(true);
        }
    }

    /**
     Ingresa datos en la tabla Especies con los nombres únicos
     que ya existen en RegistrosDeAvistamiento.
     Se ejecuta DESPUES de cargar los avistamientos
     */
    public void poblarEspecies() throws SQLException {
        String sql = """
            INSERT IGNORE INTO Especies (nombre_cientifico, nombre_comun)
            SELECT DISTINCT nombre_cientifico, nombre_comun
            FROM RegistrosDeAvistamiento
            WHERE nombre_cientifico IS NOT NULL
            """;
        try (Statement st = conn.createStatement()) {
            int filas = st.executeUpdate(sql);
            System.out.println("  Especies agregadas: " + filas);
        }
    }
}
