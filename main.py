import json
import pandas as pd
import scraper
from logger import setup_logger
import asyncio
import aiohttp
from tqdm import tqdm

logger = setup_logger()

def load_config(filename='config.json'):
    try:
        with open(filename, 'r') as file:
            config = json.load(file)
        logger.info(f"Configuración cargada exitosamente desde {filename}")
        return config
    except FileNotFoundError:
        logger.error(f"Archivo de configuración {filename} no encontrado")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error al decodificar JSON desde {filename}")
        raise

async def main():
    config = load_config()

    start_id = config.get("start_id")
    end_id = config.get("end_id")
    base_url = config.get("base_url")
    output_file = config.get("output_file")

    if start_id is None or end_id is None or start_id > end_id:
        logger.error("Configuración inválida. Por favor, revise los IDs de inicio y fin.")
        return

    logger.info(f"Iniciando proceso de scraping para los partidos {start_id} a {end_id}")

    all_stats = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for game_id in range(start_id, end_id + 1):
            url = f"{base_url}{game_id}"
            tasks.append(scraper.get_game_data(session, url, game_id, config))

        results = []
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Procesando partidos"):
            try:
                result = await f
                if result:
                    results.extend(result)
            except Exception as e:
                logger.error(f'Error al procesar un partido: {str(e)}')

    logger.info(f"Total de estadísticas de jugadores recopiladas: {len(results)}")

    if not results:
        logger.error("No se recopilaron datos. El archivo de salida estará vacío.")
        return

    # Convertir los resultados a un DataFrame
    all_stats = pd.DataFrame(results)

    # Definir el orden correcto de las columnas
    columns_order = [
        "id_partido", "equipo", "titular", "dorsal", "nombre", "minutos", "puntos",
        "T2", "T2 %", "T3", "T3 %", "T1", "T1 %", "rebotes_defensivos", "rebotes_ofensivos",
        "rebotes_totales", "asistencias", "robos", "perdidas", "C", "tapones_favor",
        "tapones_contra", "mates", "faltas_recibidas", "faltas_cometidas", "+/-", "V"
    ]

    # Asegurarse de que el DataFrame tenga todas las columnas en el orden correcto
    all_stats = all_stats.reindex(columns=columns_order)

    logger.info(f"Dimensiones del DataFrame final: {all_stats.shape}")

    # Guardar todas las estadísticas en un solo archivo CSV
    all_stats.to_csv(output_file, index=False)
    logger.info(f'Todos los datos de los partidos guardados en {output_file}')

if __name__ == "__main__":
    asyncio.run(main())