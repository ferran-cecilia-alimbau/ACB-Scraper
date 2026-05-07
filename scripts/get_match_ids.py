import requests
from bs4 import BeautifulSoup
import json
import re
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / 'data' / 'input' / 'match_ids.json'

def get_match_ids(url):
    # Hacer la petición GET a la página
    response = requests.get(url)
    
    # Verificar si la petición fue exitosa
    if response.status_code != 200:
        print(f"Error al acceder a la página: {response.status_code}")
        return []

    # Parsear el contenido HTML
    soup = BeautifulSoup(response.content, 'html.parser')

    # La web actual enlaza a ACB Live:
    # https://live.acb.com/partidos/<slug>-104459/estadisticas
    match_ids = set()
    for link in soup.select('a[href*="/estadisticas"]'):
        href = link.get('href', '')
        match_id = re.search(r'-(\d{5,})/estadisticas', href) or re.search(r'/id/(\d+)', href)
        if match_id:
            match_ids.add(int(match_id.group(1)))

    return sorted(match_ids)

def save_to_json(data, filename):
    filename = Path(filename)
    # Crear el directorio si no existe
    os.makedirs(filename.parent, exist_ok=True)
    
    # Guardar con el mismo formato que antes
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# URL de la página con el calendario de Liga Endesa 2025-26
url = "https://www.acb.com/es/liga/calendario"

# Obtener los IDs de los partidos
match_ids = get_match_ids(url)

# Guardar los IDs en un archivo JSON
save_to_json({"match_ids": match_ids}, OUTPUT_PATH)

print(f"Se han extraído {len(match_ids)} IDs de partidos y se han guardado en 'match_ids.json'")
