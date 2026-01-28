# batch_play_by_play_v2.py
# NUEVA VERSIÓN: Usa la nueva estructura HTML de ACB con MatchPlayByPlayCardWrapper

import os
import json
import time
import csv
import queue
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class BatchHumanLikeScraper:
    """Procesador en lote que extrae Play-by-Play de forma concurrente."""

    def __init__(self):
        script_dir = Path(__file__).resolve().parent
        self.output_dir = script_dir.parent / "data" / "play_by_play"
        os.makedirs(self.output_dir, exist_ok=True)
        self.driver_pool = queue.Queue()

    def setup_undetected_driver(self):
        """Configuración del driver de Chrome con webdriver-manager."""
        try:
            print("   [INFO] Configurando Chrome...")
            
            options = Options()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--headless=new')  # Modo headless: Chrome sin interfaz gráfica
            options.add_argument('--disable-gpu')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # webdriver-manager descarga automáticamente el driver correcto
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            print("   [OK] Chrome iniciado correctamente")
            return driver
            
        except Exception as e:
            print(f"   [ERROR FATAL] No se pudo inicializar Chrome: {e}")
            raise

    def _scrape_and_process_game(self, game_id):
        """Procesa un único partido: navega, extrae y guarda."""
        output_filepath = os.path.join(self.output_dir, f"play_by_play_{game_id}.csv")
        if os.path.exists(output_filepath):
            return f"SALTADO: {game_id}"

        driver = self.driver_pool.get()
        try:
            print(f"[INFO]  Procesando partido {game_id}...")
            
            url = f"https://live.acb.com/es/partidos/{game_id}/jugadas"
            driver.get(url)
            
            # Esperar a que la página cargue los elementos de play-by-play
            print(f"   [INFO] Esperando carga de elementos play-by-play...")
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='MatchPlayByPlayCardWrapper']"))
                )
                time.sleep(3)
            except TimeoutException:
                return f"ERROR en {game_id}: No se encontraron elementos de play-by-play"
            
            # Click en botón "Todos" para mostrar todas las jugadas
            print(f"   [INFO] Buscando botón 'Todos'...")
            try:
                todos_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@class='_toggleGroupItem_13z1p_1']//p[contains(text(), 'Todos')]"))
                )
                parent_button = todos_button.find_element(By.XPATH, "..")
                driver.execute_script("arguments[0].click();", parent_button)
                time.sleep(2)
                print(f"   [OK] Botón 'Todos' clicado")
            except Exception as e:
                print(f"   [AVISO] No se pudo clicar botón 'Todos': {e}")
            
            # Scroll para cargar todo el contenido
            print(f"   [INFO] Cargando contenido completo...")
            scroll_attempts = 0
            max_scrolls = 300
            previous_count = 0
            no_change_rounds = 0
            quinteto_found = False
            
            while scroll_attempts < max_scrolls:
                # Scroll en el contenedor específico
                driver.execute_script("""
                    const container = document.getElementById('match-detail-scrollarea');
                    if (container) {
                        container.scrollTop += 800;
                    }
                """)
                
                time.sleep(0.4)
                scroll_attempts += 1
                
                # Cada 5 scrolls, verificar progreso
                if scroll_attempts % 5 == 0:
                    current_count = len(driver.find_elements(By.CSS_SELECTOR, "div[class*='MatchPlayByPlayCardWrapper']"))
                    
                    # Verificar si encontramos "Quinteto Inicial"
                    if not quinteto_found and "Quinteto Inicial" in driver.page_source:
                        quinteto_count = driver.page_source.count("Quinteto Inicial")
                        print(f"   [INFO] ¡Encontrados {quinteto_count} eventos 'Quinteto Inicial'!")
                        quinteto_found = True
                        # Continuar scrolleando un poco más
                        for _ in range(10):
                            driver.execute_script("""
                                const container = document.getElementById('match-detail-scrollarea');
                                if (container) container.scrollTop += 500;
                            """)
                            time.sleep(0.3)
                        break
                    
                    if scroll_attempts % 10 == 0:
                        print(f"   [DEBUG] Scroll #{scroll_attempts}: {current_count} elementos")
                    
                    if current_count == previous_count:
                        no_change_rounds += 1
                        if no_change_rounds >= 4:
                            print(f"   [OK] No se cargan más elementos: {current_count} total")
                            break
                    else:
                        no_change_rounds = 0
                        previous_count = current_count

            # Procesar contenido
            page_html = driver.page_source
            soup = BeautifulSoup(page_html, 'html.parser')

            # Extraer nombres de equipos
            local_team_name, visitor_team_name = "LOCAL", "VISITANTE"
            # TODO: Extraer nombres reales de equipos si es posible

            # Extraer jugadas con la nueva estructura
            card_wrappers = soup.select("div[class*='MatchPlayByPlayCardWrapper']")
            if not card_wrappers:
                return f"SIN JUGADAS: {game_id}"

            extracted_data = []
            current_period = "1C"
            current_time = "10:00"
            current_home_score = "0"
            current_away_score = "0"
            
            for wrapper in card_wrappers:
                # Extraer periodo y tiempo usando el selector correcto
                score_info = wrapper.select_one("div[class*='info__']")
                if score_info:
                    p_tags = score_info.find_all('p')
                    if len(p_tags) >= 2:
                        period_text = p_tags[0].text.strip()
                        time_text = p_tags[1].text.strip()
                        
                        if period_text:
                            current_period = period_text
                        if time_text:
                            current_time = time_text
                
                # Extraer marcadores
                home_score_el = wrapper.select_one("div[class*='homeScore']")
                away_score_el = wrapper.select_one("div[class*='awayScore']")
                if home_score_el and home_score_el.text.strip():
                    current_home_score = home_score_el.text.strip()
                if away_score_el and away_score_el.text.strip():
                    current_away_score = away_score_el.text.strip()

                # Extraer información del equipo y jugador
                team_card = wrapper.select_one("div[class*='MatchPlayByPlayTeamCard_matchPlayByPlayTeamCard']")
                if team_card:
                    team_name = "DESCONOCIDO"
                    classes = team_card.get('class', [])
                    if any('home' in c.lower() for c in classes):
                        team_name = local_team_name
                    elif any('away' in c.lower() for c in classes):
                        team_name = visitor_team_name
                    
                    player_el = team_card.select_one("p[class*='playerName']")
                    player = player_el.text.strip() if player_el else None
                    
                    desc_container = team_card.select_one("div[class*='MatchPlayByPlayTeamCardDescription']")
                    action = None
                    stats = None
                    if desc_container:
                        action_el = desc_container.select_one("p[class*='title']")
                        stats_el = desc_container.select_one("p[class*='stats']")
                        action = action_el.text.strip() if action_el else None
                        stats = stats_el.text.strip() if stats_el else None
                    
                    if action:
                        extracted_data.append({
                            'id_partido': game_id,
                            'periodo': current_period,
                            'tiempo': current_time,
                            'marcador_local': current_home_score,
                            'marcador_visitante': current_away_score,
                            'equipo': team_name,
                            'jugador': player,
                            'accion': action,
                            'estadistica': stats,
                        })
            
            
            # Verificación de calidad
            print(f"   [INFO] Extraídas {len(extracted_data)} jugadas")
            cinco_inicial_count = sum(1 for row in extracted_data if row['accion'] and "quinteto" in row['accion'].lower())
            
            print(f"   [DEBUG] Quinteto Inicial: {cinco_inicial_count}, Total jugadas: {len(extracted_data)}")

            # Verificación relajada: aceptar si tiene al menos 5 quintetos O más de 200 jugadas
            if cinco_inicial_count >= 5 or len(extracted_data) > 200:
                fieldnames = ['id_partido', 'periodo', 'tiempo', 'marcador_local', 'marcador_visitante', 'equipo', 'jugador', 'accion', 'estadistica']
                with open(output_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(extracted_data)
                print(f"   [OK] CSV generado: {output_filepath}")
                return f"OK: {game_id} ({len(extracted_data)} jugadas, {cinco_inicial_count} quintetos)"
            else:
                error_msg = f"CALIDAD INSUFICIENTE en {game_id}: Solo {len(extracted_data)} jugadas y {cinco_inicial_count} quintetos"
                print(f"   {error_msg}")
                return error_msg

        except Exception as e:
            try:
                driver.get('about:blank')
            except Exception as cleanup_error:
                print(f"   [AVISO] Error en cleanup del driver: {cleanup_error}")
            return f"ERROR en {game_id}: {e}"
        finally:
            if driver:
                self.driver_pool.put(driver)

    def run_batch(self, game_ids, max_workers=4):
        start_time = time.time()

        print(f"[INFO] Creando pool de {max_workers} navegadores...")
        for _ in range(max_workers):
            self.driver_pool.put(self.setup_undetected_driver())

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._scrape_and_process_game, gid) for gid in game_ids]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if "SALTADO" not in result:
                        print(result)
                except Exception as e:
                    print(f"Error en un hilo de ejecución: {e}")
        
        print("[INFO] Limpiando y cerrando navegadores...")
        while not self.driver_pool.empty():
            driver = self.driver_pool.get()
            driver.quit()

        end_time = time.time()
        print(f"\n--- Lote completado en {end_time - start_time:.2f} segundos ---")


if __name__ == "__main__":
    try:
        script_dir = Path(__file__).resolve().parent
        match_ids_file = script_dir.parent / "data" / "input" / "match_ids.json"
        with open(match_ids_file, 'r') as f:
            all_game_ids = json.load(f)['match_ids']
    except FileNotFoundError:
        print("Error: No se encuentra el fichero 'data/input/match_ids.json'")
        exit()
    
    print(f"[INFO] Total partidos en el fichero: {len(all_game_ids)}")
    scraper = BatchHumanLikeScraper()
    print("\n1. Procesar TODOS los partidos\n2. Procesar los primeros 10 partidos\n3. Procesar un rango de índices (ej: 0 a 5)")
    choice = input("\nElige una opción: ")
    
    game_ids_to_process, num_workers = [], 2
    if choice == '1':
        game_ids_to_process, num_workers = all_game_ids, 2
    elif choice == '2':
        game_ids_to_process, num_workers = all_game_ids[:10], 2
    elif choice == '3':
        try:
            start, end = int(input("Desde el índice: ")), int(input("Hasta el índice: "))
            game_ids_to_process = all_game_ids[start:end]
        except (ValueError, IndexError):
            print("Entrada inválida. Saliendo."); exit()
    else:
        print("Opción no válida. Saliendo."); exit()

    if game_ids_to_process:
        num_workers = min(num_workers, len(game_ids_to_process))
        scraper.run_batch(game_ids_to_process, max_workers=num_workers)
    else:
        print("No hay partidos seleccionados para procesar.")
