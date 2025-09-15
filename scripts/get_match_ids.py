import requests
from bs4 import BeautifulSoup
import json
import re
import os


OUTPUT_PATH = '../data/input/match_ids.json'

def get_match_ids(url):
    # Hacer la petición GET a la página
    response = requests.get(url)
    
    # Verificar si la petición fue exitosa
    if response.status_code != 200:
        print(f"Error al acceder a la página: {response.status_code}")
        return []

    # Parsear el contenido HTML
    soup = BeautifulSoup(response.content, 'html.parser')

    # Encontrar todos los elementos 'article' con clase 'partido'
    partidos = soup.find_all('article', class_='partido')

    # Lista para almacenar los IDs de los partidos
    match_ids = []

    # Extraer los IDs de los partidos
    for partido in partidos:
        # Buscar los enlaces a las estadísticas
        links = partido.select('a[href*="/partido/estadisticas/id/"]')
        for link in links:
            # Extraer el ID del partido del atributo href
            match_id = re.search(r'/id/(\d+)', link['href'])
            if match_id:
                match_ids.append(int(match_id.group(1)))
                break  # Solo necesitamos un ID por partido

    return match_ids

def save_to_json(data, filename):
    # Crear el directorio si no existe
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Guardar con el mismo formato que antes
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# URL de la página con el calendario (2023 o 2024 según temporada deseada)
url = "https://www.acb.com/calendario/index/temporada_id/2024"

# Obtener los IDs de los partidos
match_ids = get_match_ids(url)

# Guardar los IDs en un archivo JSON
save_to_json({"match_ids": match_ids}, OUTPUT_PATH)

print(f"Se han extraído {len(match_ids)} IDs de partidos y se han guardado en 'match_ids.json'")