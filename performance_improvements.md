# Mejoras de Rendimiento para ACB Scraper

Tras analizar el código, he identificado estos cuellos de botella de rendimiento y sus soluciones:

## 1. Búsquedas Ineficientes de Perfiles de Jugadores

**Problema**: En `main.py`, la línea 121 realiza una búsqueda ineficiente utilizando valores de DataFrames:
```python
if profile['player_id'] not in dataframes['output_file_player_profiles']['player_id'].values
```
Esta es una operación O(n) que se realiza repetidamente, lo que puede ser lento con conjuntos de datos grandes.

**Solución**: Convertir a un conjunto para búsquedas O(1):
```python
# Al principio de la función process_and_save_data:
existing_profile_ids_set = set(dataframes['output_file_player_profiles']['player_id'].values)

# Luego reemplazar la búsqueda con:
if profile['player_id'] not in existing_profile_ids_set
```

## 2. Limitación de Tasa Bloquea el Bucle de Eventos

**Problema**: En `scraper.py`, la implementación de limitación de tasa bloquea todo el bucle de eventos:
```python
async with session.get(url, headers=headers) as response:
    await asyncio.sleep(config.get('rate_limit', 1))
    response.raise_for_status()
    return await response.text()
```

**Solución**: Mover el sleep *después* de obtener el texto de respuesta para evitar el bloqueo:
```python
async with session.get(url, headers=headers) as response:
    response.raise_for_status()
    text = await response.text()
    await asyncio.sleep(config.get('rate_limit', 1))
    return text
```