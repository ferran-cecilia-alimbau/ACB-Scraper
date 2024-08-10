
# Basketball Stats Scraper

Este repositorio contiene un web scraper diseñado para extraer datos de partidos de baloncesto desde el sitio web de la ACB. El scraper recopila estadísticas detalladas de cada partido y las guarda en un archivo CSV para su posterior análisis.

## Estructura del Proyecto

- **`config.json`**: Archivo de configuración que define los parámetros clave para la ejecución del scraper, como el rango de IDs de partidos a extraer, el URL base, y las opciones de manejo de errores y límite de velocidad.
  
- **`main.py`**: El punto de entrada principal para ejecutar el scraper. Este script se encarga de coordinar la ejecución del scraper y manejar los errores que puedan surgir durante la extracción de datos.

- **`scraper.py`**: Contiene la lógica principal del scraper, incluyendo la extracción de datos de la página web y la manipulación de las estadísticas de los partidos.

- **`logger.py`**: Módulo que configura y maneja el sistema de logging para capturar información sobre la ejecución del scraper, facilitando la detección y resolución de problemas.

- **`estadisticas_todos_partidos.csv`**: Archivo de salida generado por el scraper que contiene todas las estadísticas de los partidos extraídos.

## Configuración

El archivo `config.json` contiene las siguientes configuraciones clave:

- **`start_id`**: ID del primer partido a extraer.
- **`end_id`**: ID del último partido a extraer.
- **`base_url`**: URL base del sitio web de la ACB desde donde se extraerán los datos.
- **`output_file`**: Nombre del archivo CSV donde se guardarán las estadísticas extraídas.
- **`max_retries`**: Número máximo de reintentos en caso de que una solicitud falle.
- **`retry_delay`**: Tiempo de espera (en segundos) antes de reintentar una solicitud fallida.
- **`user_agent`**: User-Agent que se utilizará para las solicitudes HTTP.
- **`rate_limit`**: Tiempo mínimo (en segundos) entre solicitudes para respetar las políticas de uso del sitio web.

## Uso

1. **Configurar el scraper**: Asegúrese de que las configuraciones en `config.json` están ajustadas a sus necesidades.

2. **Ejecutar el scraper**: Desde la terminal, puede ejecutar el scraper utilizando el siguiente comando:

   ```bash
   python main.py
   ```

3. **Revisar el archivo de salida**: Una vez que el scraper haya terminado, todas las estadísticas de los partidos estarán disponibles en el archivo `estadisticas_todos_partidos.csv`.

## Dependencias

Este proyecto requiere Python 3.7 o superior. Las dependencias necesarias están especificadas en el archivo `requirements.txt` (si está disponible). Para instalarlas, ejecute:

```bash
pip install -r requirements.txt
```

## Registro de Logs

El scraper genera un archivo de logs que documenta la ejecución del programa. Esto es útil para depurar problemas o para verificar que los datos se han extraído correctamente. Los logs incluyen información sobre:

- Errores de red y reintentos
- Partidos procesados con éxito
- Problemas específicos con la extracción de datos

## Mejoras Futuras

- Implementar la extracción de más estadísticas y detalles adicionales de cada partido.
- Optimización del manejo de errores para casos específicos.
- Soporte para más formatos de salida (ej. JSON, bases de datos).

## Contribuciones

Las contribuciones son bienvenidas. Por favor, envíe un pull request con una descripción clara de los cambios propuestos.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT. Consulte el archivo LICENSE para más detalles.
