package com.biodiversidad.model;

import java.time.LocalDate;

public class Avistamiento {
    private int idAvistamiento;
    private String nombreCientifico;
    private String nombreComun;
    private double latitud;
    private double longitud;
    private LocalDate fecha;
    private int cantidad;
    private String locNombre;

    public Avistamiento(String nombreCientifico, String nombreComun,
                        double latitud, double longitud,
                        LocalDate fecha, int cantidad, String locNombre) {
        this.nombreCientifico = nombreCientifico;
        this.nombreComun = nombreComun;
        this.latitud = latitud;
        this.longitud = longitud;
        this.fecha = fecha;
        this.cantidad = cantidad;
        this.locNombre = locNombre;
    }

    public boolean isValido() {
        return latitud  >= 20.30 && latitud  <= 21.00 &&
                longitud >= -103.60 && longitud <= -102.90 &&
                cantidad > 0 &&
                nombreCientifico != null && !nombreCientifico.isBlank();
    }

    // Getters
    public String    getNombreCientifico() { return nombreCientifico; }
    public String    getNombreComun()      { return nombreComun; }
    public double    getLatitud()          { return latitud; }
    public double    getLongitud()         { return longitud; }
    public LocalDate getFecha()            { return fecha; }
    public int       getCantidad()         { return cantidad; }
    public String    getLocNombre()        { return locNombre; }

    @Override
    public String toString() {
        return String.format("[%s | lat=%.4f lon=%.4f | %s | x%d]",
                nombreCientifico, latitud, longitud, fecha, cantidad);
    }
}

