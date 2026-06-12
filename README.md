# UnioMercato

Plataforma de scouting de porteros para comparar mercados, filtrar candidatos y generar informes individuales en PDF.

## Funcionalidades

- Comparación de porteros mediante percentiles contextualizados por el grupo visible.
- Scores de juego de pies, paradas y equilibrio global.
- Filtros multicompetición, minutos, partidos y características del jugador.
- Ficha individual con radares, fortalezas, puntos a vigilar y vías de distribución.
- Generación de informes PDF.
- Lectura de datos y recursos desde Google Drive mediante una cuenta de servicio.

## Ejecución local

1. Crea un entorno virtual e instala `requirements.txt`.
2. Copia `.env.example` como `.env` y completa las credenciales.
3. Comparte la carpeta de Google Drive con el correo de la cuenta de servicio.
4. Ejecuta:

```bash
streamlit run app.py
```

Los secretos, los datos descargados y los informes generados están excluidos del repositorio.

## Documentación

- [Metodología y evolución del proyecto](docs/proyecto_scouting_unionistas.md)
- [Sincronización con Google Drive](docs/drive_sync.md)
