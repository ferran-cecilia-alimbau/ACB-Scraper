# batch_play_by_play.py
# VERSIÓN MEJORADA: Manejo más robusto del botón "Todos" y mejor detección de carga completa

import os
import json
import time
import csv
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

class BatchHumanLikeScraper:
    """Procesador en lote que extrae Play-by-Play de forma concurrente."""
    
    def __init__(self):
        self.output_dir = "../data/play_by_play"
        os.makedirs(self.output_dir, exist_ok=True)
        self.driver_pool = queue.Queue()

    def setup_undetected_driver(self):
        """Configuración del driver de Chrome."""
        options = uc.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1366,768')
        options.add_argument('--headless=new')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        driver = uc.Chrome(options=options)
        return driver
    
    def _wait_for_page_stability(self, driver, timeout=10):
        """Espera a que la página esté estable antes de interactuar"""
        try:
            # Esperar a que no haya requests pendientes (JavaScript)
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            # Pequeña pausa adicional para asegurar que todo esté cargado
            time.sleep(2)
            return True
        except TimeoutException:
            return False

    def _click_todos_button_robust(self, driver):
        """Manejo robusto del click en el botón 'Todos'"""
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                print(f"   Intento {attempt + 1} de hacer click en 'Todos'...")
                
                # 1. Esperar a que el contenedor esté presente y visible
                filter_container = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.fi-per"))
                )
                
                # 2. Scroll hasta el elemento para asegurar visibilidad
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", filter_container)
                time.sleep(1)
                
                # 3. Buscar el botón 'Todos' con múltiples estrategias
                todos_selectors = [
                    "//div[@class='fi-per']/div[@role='button' and normalize-space(text())='Todos']",
                    "//div[contains(@class,'fi-per__item') and normalize-space(text())='Todos']",
                    "//div[@role='button' and contains(text(),'Todos')]"
                ]
                
                todos_button = None
                for selector in todos_selectors:
                    try:
                        todos_button = driver.find_element(By.XPATH, selector)
                        if todos_button.is_displayed():
                            break
                    except:
                        continue
                
                if not todos_button:
                    raise Exception("No se pudo localizar el botón 'Todos'")
                
                # 4. Verificar si ya está seleccionado
                current_classes = todos_button.get_attribute('class') or ''
                is_already_selected = 'fi-per__item--selected' in current_classes or 'selected' in current_classes
                
                if is_already_selected:
                    print("   [OK] El botón 'Todos' ya está seleccionado")
                    return True
                
                # 5. Intentar diferentes métodos de click
                click_methods = [
                    lambda: todos_button.click(),
                    lambda: driver.execute_script("arguments[0].click();", todos_button),
                    lambda: driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", todos_button)
                ]
                
                click_successful = False
                for i, click_method in enumerate(click_methods):
                    try:
                        click_method()
                        print(f"   Click ejecutado con método {i + 1}")
                        click_successful = True
                        break
                    except ElementClickInterceptedException:
                        print(f"   Método {i + 1} interceptado, probando siguiente...")
                        continue
                    except Exception as e:
                        print(f"   Método {i + 1} falló: {e}")
                        continue
                
                if not click_successful:
                    print(f"   [FALLO] Todos los métodos de click fallaron en intento {attempt + 1}")
                    continue
                
                # 6. Verificar que el click tuvo efecto
                verification_timeout = 10
                start_verification = time.time()
                
                while time.time() - start_verification < verification_timeout:
                    try:
                        # Re-localizar el elemento para evitar elementos obsoletos
                        current_button = driver.find_element(By.XPATH, todos_selectors[0])
                        current_classes = current_button.get_attribute('class') or ''
                        
                        if 'fi-per__item--selected' in current_classes or 'selected' in current_classes:
                            print("   [OK] Click verificado - botón 'Todos' seleccionado")
                            
                            # 7. Esperar a que las jugadas se carguen
                            try:
                                WebDriverWait(driver, 15).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, ".pp-item"))
                                )
                                print("   [OK] Jugadas detectadas después del filtro")
                                return True
                            except TimeoutException:
                                print("   [AVISO] Timeout esperando jugadas después del filtro")
                                # Continuar con el siguiente intento
                                break
                        
                        time.sleep(0.5)
                        
                    except StaleElementReferenceException:
                        # El elemento cambió, esto es normal después de un click exitoso
                        time.sleep(0.5)
                        continue
                    except Exception as e:
                        print(f"   Error durante verificación: {e}")
                        break
                
                print(f"   [FALLO] Verificación falló en intento {attempt + 1}")
                time.sleep(2)  # Pausa antes del siguiente intento
                
            except TimeoutException:
                print(f"   [FALLO] Timeout en intento {attempt + 1}")
                continue
            except Exception as e:
                print(f"   [FALLO] Error en intento {attempt + 1}: {e}")
                continue
        
        return False

    def _verify_complete_data_loading(self, driver):
        """Verifica que todos los datos del partido estén cargados"""
        try:
            # Verificar elementos clave que indican carga completa
            checks = [
                # Al menos debe haber jugadas
                (By.CSS_SELECTOR, ".pp-item", 1),
                # Debe haber eventos de "Cinco Inicial" (inicio del partido)
                (By.XPATH, "//*[contains(text(), 'Cinco Inicial')]", 2),
                # Debe haber "Inicio del Partido"
                (By.XPATH, "//*[contains(text(), 'Inicio del Partido')]", 1),
            ]
            
            for selector_type, selector, min_count in checks:
                elements = driver.find_elements(selector_type, selector)
                if len(elements) < min_count:
                    print(f"   [AVISO] Verificación falló: {selector} - encontrados {len(elements)}, esperados {min_count}")
                    return False
            
            print("   [OK] Verificación de datos completa exitosa")
            return True
            
        except Exception as e:
            print(f"   [FALLO] Error en verificación de datos: {e}")
            return False

    def _scrape_and_process_game(self, game_id):
        """Procesa un único partido: navega, extrae y guarda."""
        output_filepath = os.path.join(self.output_dir, f"play_by_play_{game_id}.csv")
        if os.path.exists(output_filepath):
            return f"SALTADO: {game_id}"

        driver = self.driver_pool.get()
        try:
            print(f"[INFO]  Procesando partido {game_id}...")
            
            url = f"https://jv.acb.com/es/{game_id}/jugadas"
            driver.get(url)
            
            # Esperar estabilidad inicial de la página
            if not self._wait_for_page_stability(driver):
                return f"ERROR en {game_id}: Página no se estabilizó"
            
            # Click en el elemento principal de play-by-play
            try:
                pp_element = WebDriverWait(driver, 25).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".pp"))
                )
                pp_element.click()
                time.sleep(2)
            except TimeoutException:
                return f"ERROR en {game_id}: No se pudo hacer click en elemento .pp"
            
            # Aplicar filtro "Todos" de forma robusta
            if not self._click_todos_button_robust(driver):
                return f"ERROR en {game_id}: No se pudo aplicar filtro 'Todos' después de múltiples intentos"
            
            # Scroll para cargar todo el contenido
            print(f"   [INFO] Cargando contenido completo...")
            start_time = time.time()
            scroll_timeout = 600  # 10 minutos máximo
            
            while True:
                if time.time() - start_time > scroll_timeout:
                    print(f"   [AVISO] Timeout de scroll en partido {game_id}")
                    break
                
                # Verificar si tenemos marcadores de inicio y fin
                inicio_count = len(driver.find_elements(By.XPATH, "//*[contains(text(), 'Cinco Inicial')]"))
                fin_count = len(driver.find_elements(By.XPATH, "//*[contains(text(), 'Final del Partido')]"))
                
                if inicio_count >= 9 and fin_count >= 1:
                    print(f"   [OK] Contenido completo detectado (Inicio: {inicio_count}, Fin: {fin_count})")
                    break
                
                # Scroll y pequeña pausa
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                time.sleep(0.5)
            
            # Verificación final de datos completos
            if not self._verify_complete_data_loading(driver):
                return f"ERROR en {game_id}: Datos incompletos después de la carga"

            # Procesar contenido
            page_html = driver.page_source
            soup = BeautifulSoup(page_html, 'html.parser')

            # Extraer nombres de equipos
            local_team_name, visitor_team_name = "LOCAL", "VISITANTE"
            header_container = soup.select_one("div.he-wrap")
            if header_container:
                team_name_elements = header_container.select(".ge-match-info__name span")
                if len(team_name_elements) >= 2:
                    local_team_name = team_name_elements[0].text.strip()
                    visitor_team_name = team_name_elements[1].text.strip()

            # Extraer jugadas
            play_elements = soup.select(".pp-item")
            if not play_elements:
                return f"SIN JUGADAS: {game_id}"

            extracted_data = []
            for play in play_elements:
                team_name = None
                play_classes = play.get('class', [])
                if play.select_one(".pp-item-mes__team"):
                    if 'pp-item--visitor' in play_classes:
                        team_name = visitor_team_name
                    else:
                        team_name = local_team_name
                
                periodo_tag = play.select_one(".ge-match-time-info")
                tiempo_tag = play.select_one(".ge-match-time-sec")
                jugador_tag = play.select_one(".pp-item-mes-portrait__name")
                accion_tag = play.select_one(".pp-item-mes-info-text__desc")
                stats_tag = play.select_one(".pp-item-mes-info-text__stats")
                marcador_local_tag = play.select_one(".pp-item-mes-score__local")
                marcador_visitante_tag = play.select_one(".pp-item-mes-score__visitor")

                extracted_data.append({
                    'id_partido': game_id,
                    'periodo': periodo_tag.text.strip() if periodo_tag else None,
                    'tiempo': tiempo_tag.text.strip() if tiempo_tag else None,
                    'marcador_local': marcador_local_tag.text.strip() if marcador_local_tag else None,
                    'marcador_visitante': marcador_visitante_tag.text.strip() if marcador_visitante_tag else None,
                    'equipo': team_name,
                    'jugador': jugador_tag.text.strip() if jugador_tag else None,
                    'accion': accion_tag.text.strip() if accion_tag else None,
                    'estadistica': stats_tag.text.strip() if stats_tag else None,
                })
            
            # Verificación de calidad mejorada
            cinco_inicial_count = sum(1 for row in extracted_data if row['accion'] and "Cinco Inicial" in row['accion'])
            inicio_partido_found = any(1 for row in extracted_data if row['accion'] and "Inicio del Partido" in row['accion'])
            final_partido_found = any(1 for row in extracted_data if row['accion'] and "Final del Partido" in row['accion'])

            if cinco_inicial_count >= 9 and inicio_partido_found and final_partido_found:
                fieldnames = ['id_partido', 'periodo', 'tiempo', 'marcador_local', 'marcador_visitante', 'equipo', 'jugador', 'accion', 'estadistica']
                with open(output_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(extracted_data)
                return f"OK: {game_id} ({len(extracted_data)} jugadas)"
            else:
                error_msg = f"ERROR DE CALIDAD en {game_id}: Datos incompletos (Cinco Inicial: {cinco_inicial_count}, Inicio: {inicio_partido_found}, Final: {final_partido_found})"
                return error_msg

        except Exception as e:
            try:
                driver.get('about:blank')
            except:
                pass
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
        with open('../data/input/match_ids.json', 'r') as f:
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