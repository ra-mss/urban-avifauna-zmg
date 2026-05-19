package com.biodiversidad.service;

import com.biodiversidad.model.Avistamiento;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.*;
import java.net.http.HttpResponse;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

public class EBirdAPIClient {
    private static final String BASE = "https://api.ebird.org/v2";
    private static final String KEY = System.getenv("EBIRD_API_KEY");
    private final HttpClient http = HttpClient.newHttpClient();
    private final ObjectMapper json = new ObjectMapper();

    // observaciones recientes en Jalisco (últimos X días)
    public List<Avistamiento> fetchRecientes(int diasAtras) throws Exception {
        String url = BASE + "/data/obs/MX-JAL/recent"
                + "?back=" + diasAtras
                + "&maxResults=10000"
                + "&includeProvisional=true";
        System.out.println("  → Fetching recientes (back=" + diasAtras + ")...");
        return parsearRespuesta(llamarAPI(url));
    }

    // histórico para una fecha específica
    public List<Avistamiento> fetchHistorico(LocalDate fecha) throws Exception {
        String url = String.format(
                "%s/data/obs/MX-JAL/historic/%d/%d/%d?maxResults=10000",
                BASE, fecha.getYear(), fecha.getMonthValue(), fecha.getDayOfMonth()
        );
        System.out.println("Fetching histórico: " + fecha + "...");
        return parsearRespuesta(llamarAPI(url));
    }

    // radio alrededor de GDL
    public List<Avistamiento> fetchPorRadio(double lat, double lon,
                              int radioKm) throws Exception {
        String url = String.format(
                "%s/data/obs/geo/recent?lat=%.4f&lng=%.4f&dist=%d&back=30&maxResults=10000",
                BASE, lat, lon, radioKm
        );
        System.out.println("Fetching por radio (" + radioKm + "km)...");
        return parsearRespuesta(llamarAPI(url));
    }

    // HTTP GET con header de autenticación
    private String llamarAPI(String url) throws Exception {
        if (KEY == null || KEY.isBlank()) {
            throw new IllegalStateException(
                    "EBIRD_API_KEY no configurada. Ejecuta: export EBIRD_API_KEY=la_clave"
            );
        }
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("x-ebirdapitoken", KEY)
                .header("Accept", "application/json")
                .GET().build();

        HttpResponse<String> resp =
                http.send(req, HttpResponse.BodyHandlers.ofString());

        if (resp.statusCode() != 200) {
            throw new RuntimeException(
                    "Error API eBird: HTTP " + resp.statusCode() + "\n" + resp.body()
            );
        }
        return resp.body();
    }

    // parsear array JSON a List
    private List<Avistamiento> parsearRespuesta(String cuerpo) throws Exception {
        List<Avistamiento> lista = new ArrayList<>();
        JsonNode array = json.readTree(cuerpo);

        for (JsonNode nodo : array) {
            try {
                String especie = nodo.get("sciName").asText("");
                String comun = nodo.get("comName").asText("");
                double lat = nodo.get("lat").asDouble();
                double lon = nodo.get("lng").asDouble();
                String fechaStr = nodo.get("obsDt").asText().substring(0, 10);
                int cantidad = (nodo.has("howMany") && !nodo.get("howMany").isNull())
                        ? nodo.get("howMany").asInt() : 1;
                String locNombre = nodo.has("locName")
                        ? nodo.get("locName").asText("") : "";

                Avistamiento a = new Avistamiento(
                        especie, comun, lat, lon,
                        LocalDate.parse(fechaStr), cantidad, locNombre
                );

                if (a.isValido()) lista.add(a);

            } catch (Exception ignored) {
                // registro mal se descarta
            }
        }
        System.out.println("Registros válidos de la ZMG: " + lista.size());
        return lista;
    }
}
