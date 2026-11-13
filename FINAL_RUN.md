# Entrega del set final

Actualización al cierre: se conserva esta entrega exactamente como fue generada por `c7406f3` y publicada en `8a1f5be`. El código posterior mejora práctica a **33,81/55**, pero el usuario pidió cerrar de inmediato sin esperar la regeneración fría. Esas mejoras todavía no se aplicaron a los cuatro archivos de `entrega/`; los hashes y tiempos de esta nota siguen describiendo la entrega conservada.

Generada automáticamente con el código de `c7406f32b1fbfe17b9ab0c6979a505ac05be8160`, sin editar predicciones ni etiquetas a mano. Finalización: 2026-11-13T08:40:28.277512-03:00.

Fuente: [release oficial set-final](https://github.com/qualydata-org/desafio-qualydata/releases/tag/set-final), publicada el 12/11/2026 a las 17:00 de Salta. Se verificaron los cuatro SHA-256 publicados. El set no contiene verdad pública; no hay puntaje de final calculable localmente.

```bash
python pipeline.py --datos datos/final --entrega entrega
```

Entrada: 150000 comentarios, 12002 cuentas y 10 días. Salida: 28 narrativas y 13 cuentas marcadas en 3 operaciones. Son conteos de predicción, no mediciones de precisión o recall.

Primera corrida con codificación de textos nuevos: **856.100 s**. Hardware: Linux x86_64, CPU, 4 hilos. Tokens de API: 0; USD de API: 0.0. `costo.json` incluye esta medición de referencia completa; una corrida posterior con caché puede tardar menos. Las duraciones reales siempre se imprimen en `telemetria:`.

Las columnas, IDs completos y únicos, referencias a narrativas, valores de postura y fechas ISO con zona horaria pasaron validación. `entrega/` contiene sólo los cuatro archivos oficiales; los Parquet y `metricas.json` están en `salida/final/`.

## SHA256 de entrada

```text
7695e3f826c9e855a4d0b7592698b3f8af7edcfccf1cb9814cfbcc6e2f1c34c7  fuentes.csv
74b02ddf5cdb0ebbafed897bb69e6ae9d980355b6ccccf3fccfc441a641d7f02  publicaciones.csv.gz
99b4c5b1fc3f07fd04c3cee924a5cc5e901541b31b984162c5f04d52099e49df  comentarios.csv.gz
43a325bdb0b92fd06e8632d764bc69f32216805795a069c1abbda78556cd087a  cuentas.csv.gz
```

## SHA256 de entrega

```text
0479d81273862c13c03a83ca3d2030df1ba6e1e0d9bb3a6859aa55f9ce2d6911  comentarios.csv
074a833c1f68177577b9b3d9c551fe6792ec36ccbff456e749e4ee45cda4076a  costo.json
4988a6546e0629c5bec80da0a17789ff02a9d139cdc7d3fc84a75d7b0638bb8d  cuentas.csv
c0b42c092d557b6bff08fa3f434e2efb7d7e25e4a50242869105fa495eb68393  narrativas.csv
```

SHA-256 de `pipeline.py`: `37c85259d684960a762a4d748437631d7c13f903bd35bc2ec6a747d9667c41e6`.
