# Drive Sync

## Estructura esperada en Google Drive

- `datos/` con los CSV de Wyscout.
- `escudo/` con los escudos del club.
- `logos_competiciones/` con los logos de las competiciones.
- `mcode/` con el logo de MCode Analytics.

## Variables de entorno

- `UNIOMERCATO_DATA_SOURCE=drive`
- `UNIOMERCATO_DRIVE_FOLDER_ID=<id de la carpeta raíz compartida>`
- `UNIOMERCATO_SERVICE_ACCOUNT_FILE=<ruta al JSON del service account>`
- `UNIOMERCATO_DRIVE_CACHE_DIR=<opcional, caché local de sincronización>`

Alternativa:

- Puedes usar las variables `GOOGLE_*` del service account directamente en `.env` sin guardar un JSON en disco.
- Si existe `GOOGLE_DRIVE_FOLDER_ID`, la app activa automáticamente el modo Drive.

## Qué hace la app

Cuando el modo `drive` está activo, la app:

1. Lee la carpeta raíz compartida de Drive.
2. Sincroniza sus subcarpetas a una caché local.
3. Sigue trabajando con rutas locales normales:
   - `data/`
   - `assets/escudo/`
   - `assets/competiciones/`
   - `assets/mcode/`

## Recordatorio

- El JSON del service account no debe subirse al repositorio.
- `.env` tampoco debe subirse al repositorio.
- Si cambias archivos en Drive, reinicia la app para refrescar la caché.

## Despliegue en Streamlit Community Cloud

En la configuración de la app desplegada, añade el contenido equivalente a `.env`
en la sección `Secrets`. Las claves `GOOGLE_*` y `GOOGLE_DRIVE_FOLDER_ID` deben
estar en el nivel raíz para que la app pueda leerlas como variables de entorno.

No subas a GitHub:

- `.env`
- el JSON del service account
- los CSV locales
- PDFs generados
