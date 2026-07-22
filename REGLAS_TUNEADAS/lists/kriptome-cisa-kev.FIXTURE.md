# kriptome-cisa-kev — FIXTURE DE PRUEBA, NO ES EL FEED REAL

**Estado: EXPERIMENTAL** (mismo estado que la regla `100040` que la consume — ver `experimental/100040_cisa_kev.xml`).

El archivo `kriptome-cisa-kev` (sin extensión, en esta misma carpeta) contiene **3 CVE-IDs fijos de ejemplo**, reales pero estáticos:

- `CVE-2021-44228` (Log4Shell)
- `CVE-2023-23397` (Outlook)
- `CVE-2024-3400` (PAN-OS)

Esto **no es** el catálogo CISA KEV real, que cambia constantemente (cientos de entradas, actualizado por CISA). Es un fixture pensado para probar que la regla `100040` (hoy en `experimental/`) dispara correctamente cuando el CVE de una alerta coincide con una entrada de la lista — nada más.

## Por qué no lleva comentarios dentro del `.txt`/lista

El compilador CDB de Wazuh (`src/analysisd/lists_make.c`, verificado contra el tag v4.14.6) convierte en **clave** cualquier línea que contenga `:` — un comentario tipo `### esto es un comentario` se compilaría como una clave basura real dentro del `.cdb`. Por eso la documentación de esta lista vive en este archivo hermano, no dentro de la lista misma.

## Qué falta para que sea el feed real (no se construyó en este repo)

1. Cron diario que descargue `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` (comando de referencia en `GUIA_LISTAS.docx`).
2. Reemplazar el archivo `kriptome-cisa-kev` con la salida de ese feed (formato `CVE-ID:` por línea, sin comentarios).
3. Recompilar la lista (`systemctl restart wazuh-manager` o `wazuh-logtest`).
4. Resolver la decisión de arquitectura D-KEV (regla de Wazuh vs. enriquecimiento en la App) antes de mover `100040` fuera de `experimental/`.
