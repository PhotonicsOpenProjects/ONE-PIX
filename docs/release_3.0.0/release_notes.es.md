# ONE-PIX 3.0.0: una nueva base para la imagen hiperespectral

[English](../../RELEASE_NOTES_3.0.0.md) · [Français](release_notes.fr.md) · **Español** · [Deutsch](release_notes.de.md)

ONE-PIX 3.0.0 convierte un conjunto de aplicaciones de escritorio en una cámara hiperespectral que se controla desde un navegador, se amplía con plugins y cuyos datos pueden reutilizarse fuera del proyecto. La adquisición, la reconstrucción y el análisis siguen en el centro, con una interfaz web, un núcleo Python `onepix` reorganizado y plugins independientes para los métodos de imagen, el hardware y el análisis.

## Novedades principales

- **Interfaz web en 4 idiomas** (inglés, francés, español, alemán): adquisición, análisis, datos, plugins, registros y ajustes de hardware y software, con modo oscuro y gráficos de espectros interactivos. Control remoto de una Raspberry Pi sin pantalla.
- **Plugins instalados desde la interfaz.** Los métodos de imagen, espectrómetros, cámaras y páginas de análisis son paquetes pip; un gestor de plugins los instala, actualiza y elimina.
- **Pipelines de análisis.** Encadene procesamientos (selección espectral, suavizado, normalización, índices espectrales…), normalice a reflectancia a partir de una zona o de un hipercubo de referencia almacenado, y conserve el historial de pasos en los metadatos.
- **Mediciones más limpias.** Ajuste en vivo del tiempo de integración con consejos, tiempo de integración dinámico por patrón, linealización de la respuesta en niveles de gris, calibración del corregistro proyector-cámara y control del proyector por HDMI-CEC.
- **Datos FAIR reutilizables.** Cada adquisición registra un identificador, un autor, una licencia y las versiones del software; exportación a HDF5, NumPy, MATLAB, ENVI y pilas TIFF, como paquetes RO-Crate con sumas de verificación SHA-256, para Python, MATLAB, QGIS o Fiji.
- **Archivos más pequeños.** Las mediciones JSON guardadas son de 3 a 6 veces más pequeñas y se cargan mucho más rápido, sin pérdida.
- **Control remoto.** Un servidor Socket.IO con autenticación por token configura e inicia mediciones, para aplicaciones conectadas e IoT.

## Bajo el capó

Paquete `onepix` instalado con pip; arquitectura de plugins descubiertos mediante puntos de entrada; más de 190 pruebas y una CI en tres versiones de Python; registro de eventos; escritura atómica de la configuración; instalador unificado (`install.py`) y servicio systemd en Raspberry Pi.

## Correcciones que conviene conocer

Bloqueo entre los hilos de adquisición, proyección y espectrómetro; pérdida silenciosa de datos al guardar ciertas matrices como JSON; escritura en un archivo cerrado en dos módulos de hardware; modo debug de Flask desactivado por defecto; autenticación de Socket.IO; solicitudes entre sitios rechazadas.

## Migración desde la versión anterior

1. Instale los plugins que necesite: ya no se incluye ningún método de imagen en el repositorio.
2. Sustituya `core.*` por `onepix.*` en sus scripts.
3. Use la interfaz web: las aplicaciones Tkinter se han eliminado.
4. Un programa que lea los JSON guardados sin `onepix.utils` debe usar `ONEPIX_COMPACT_JSON=0`. No se ha probado la relectura de archivos de resultados V2.

La interfaz web no tiene autenticación y escucha en todas las interfaces de red: úsela en una red de confianza (véase [SECURITY.md](../../SECURITY.md)).

Detalles completos: [CHANGELOG.md](../../CHANGELOG.md) (en inglés).
