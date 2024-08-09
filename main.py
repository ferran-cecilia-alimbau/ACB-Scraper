import json
import pandas as pd
import scraper
from logger import setup_logger

logger = setup_logger()

def load_config(filename='config.json'):
    """
    Cargar la configuración desde un archivo JSON.
    """
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

def main():
    # Cargar la configuración
    config = load_config()

    start_id = config.get("start_id")
    end_id = config.get("end_id")

    # Validar los IDs
    if start_id is None or end_id is None or start_id > end_id:
        logger.error("Configuración inválida. Por favor, revise los IDs de inicio y fin.")
        return

    logger.info(f"Iniciando proceso de scraping para los partidos {start_id} a {end_id}")

    all_stats = pd.DataFrame()

    # Generar URLs y procesar cada partido
    base_url = "https://www.acb.com/partido/estadisticas/id/"
    for game_id in range(start_id, end_id + 1):
        url = f"{base_url}{game_id}"
        logger.info(f"Procesando partido {game_id}")
        try:
            df_team1, df_team2 = scraper.get_game_data(url, game_id)
            # Concatenar los resultados al DataFrame general
            all_stats = pd.concat([all_stats, df_team1, df_team2], ignore_index=True)
            logger.info(f"Partido {game_id} procesado exitosamente")
        except Exception as e:
            logger.error(f'Error al procesar el partido {game_id}: {str(e)}')

    # Guardar todas las estadísticas en un solo archivo CSV
    output_file = 'estadisticas_todos_partidos.csv'
    all_stats.to_csv(output_file, index=False)
    logger.info(f'Todos los datos de los partidos guardados en {output_file}')

if __name__ == "__main__":
    main()