# batch_play_by_play_v2.py
# NUEVA VERSIÓN: Usa la nueva estructura HTML de ACB con MatchPlayByPlayCardWrapper

import argparse
import os
import json
import time
import csv
import queue
import tempfile
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

script_dir = Path(__file__).resolve().parent


def _find_chrome_binary():
    """Busca Chrome/Chromium local, incluido Chrome for Testing descargado en el workspace."""
    env_binary = os.environ.get("CHROME_BINARY") or os.environ.get("GOOGLE_CHROME_BIN")
    candidates = [
        env_binary,
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(script_dir.parent / ".chrome-for-testing" / "chrome-mac-arm64" / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing"),
        str(script_dir.parent / ".chrome-for-testing" / "chrome-mac-x64" / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _find_chromedriver_binary():
    """Busca un chromedriver instalado en el sistema antes de descargar nada."""
    env_driver = os.environ.get("CHROMEDRIVER") or os.environ.get("CHROME_DRIVER")
    candidates = [
        env_driver,
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/snap/bin/chromium.chromedriver",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


class BatchHumanLikeScraper:
    """Procesador en lote que extrae Play-by-Play de forma concurrente."""

    def __init__(self):
        self.output_dir = script_dir.parent / "data" / "play_by_play"
        os.makedirs(self.output_dir, exist_ok=True)
        self.driver_pool = queue.Queue()
        self.score_lookup = self._load_score_lookup()

    def _load_score_lookup(self):
        """Carga resultados esperados desde estadisticas_partido.csv."""
        game_info_path = script_dir.parent / "data" / "output" / "estadisticas_partido.csv"
        lookup = {}
        try:
            with open(game_info_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lookup[int(row['id_partido'])] = (
                        int(row['resultado_local']),
                        int(row['resultado_visitante']),
                    )
        except FileNotFoundError:
            print("[AVISO] No se encontró estadisticas_partido.csv — verificación de marcador desactivada")
        return lookup

    def setup_undetected_driver(self):
        """Configuración del driver de Chrome con webdriver-manager."""
        try:
            print("   [INFO] Configurando Chrome...")

            options = Options()
            # Opciones básicas
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')

            # Opciones adicionales para Ubuntu Server (sin GUI)
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-setuid-sandbox')
            # Puerto debug fijo ELIMINADO — Chrome asigna puerto libre automáticamente
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')

            # Opciones experimentales
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            chrome_binary = _find_chrome_binary()
            if chrome_binary:
                options.binary_location = chrome_binary
                print(f"   [INFO] Usando Chrome: {chrome_binary}")

            chromedriver_binary = _find_chromedriver_binary()
            if chromedriver_binary:
                print(f"   [INFO] Usando ChromeDriver: {chromedriver_binary}")
                service = Service(chromedriver_binary)
                driver = webdriver.Chrome(service=service, options=options)
            elif chrome_binary:
                # webdriver-manager: usa caché local, sin descargar si ya existe
                os.environ['WDM_LOCAL'] = '1'
                try:
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                except Exception as wdm_error:
                    print(f"   [AVISO] webdriver-manager falló: {wdm_error}")
                    print("   [INFO] Reintentando con Selenium Manager...")
                    driver = webdriver.Chrome(options=options)
            else:
                print("   [INFO] Chrome local no detectado; usando Selenium Manager...")
                driver = webdriver.Chrome(options=options)

            print("   [OK] Chrome iniciado correctamente")
            return driver

        except Exception as e:
            print(f"   [ERROR FATAL] No se pudo inicializar Chrome: {e}")
            raise

    def _verify_score(self, game_id, extracted_data):
        """Compara el marcador final del PBP con el resultado real.

        Returns:
            (ok, message) — ok=True si coincide o no hay datos de referencia.
        """
        if not self.score_lookup or game_id not in self.score_lookup:
            return True, "Sin datos de referencia para verificar marcador"

        expected_local, expected_visitor = self.score_lookup[game_id]

        # Buscar último marcador en las jugadas extraídas
        last_local, last_visitor = 0, 0
        for row in extracted_data:
            try:
                local = int(row['marcador_local'])
                visitor = int(row['marcador_visitante'])
                if local > last_local or visitor > last_visitor:
                    last_local = max(last_local, local)
                    last_visitor = max(last_visitor, visitor)
            except (ValueError, TypeError):
                continue

        if last_local == expected_local and last_visitor == expected_visitor:
            return True, f"Marcador OK: {last_local}-{last_visitor}"

        return False, (
            f"MARCADOR NO COINCIDE: PBP={last_local}-{last_visitor}, "
            f"esperado={expected_local}-{expected_visitor}"
        )

    def _scrape_and_process_game(self, game_id, force=False):
        """Procesa un único partido: navega, extrae y guarda."""
        output_filepath = os.path.join(self.output_dir, f"play_by_play_{game_id}.csv")
        if os.path.exists(output_filepath) and not force:
            return f"SALTADO: {game_id}"

        try:
            driver = self.driver_pool.get(timeout=1)
        except queue.Empty:
            driver = self.setup_undetected_driver()
        try:
            print(f"[INFO]  Procesando partido {game_id}...")

            # Limpiar estado SPA: navegar a about:blank para desmontar DOM React
            driver.get('about:blank')
            time.sleep(0.5)

            url = f"https://live.acb.com/es/partidos/{game_id}/jugadas"
            driver.get(url)

            # Esperar a que la página cargue los elementos de play-by-play
            print(f"   [INFO] Esperando carga de elementos play-by-play...")
            try:
                # Fase 1: Si quedan elementos del partido anterior, esperar a que desaparezcan
                existing = driver.find_elements(By.CSS_SELECTOR, "div[class*='MatchPlayByPlayCardWrapper']")
                if existing:
                    try:
                        WebDriverWait(driver, 10).until(EC.staleness_of(existing[0]))
                    except TimeoutException:
                        pass

                # Fase 2: Esperar elementos frescos del partido actual
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
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[.//*[normalize-space()='Todos'] or normalize-space()='Todos']",
                    ))
                )
                driver.execute_script("arguments[0].click();", todos_button)
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
                        if action in ("Quinteto Inicial", "Cinco Inicial"):
                            action = "Quinteto inicial"
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
            if not (cinco_inicial_count >= 5 or len(extracted_data) > 200):
                error_msg = f"CALIDAD INSUFICIENTE en {game_id}: Solo {len(extracted_data)} jugadas y {cinco_inicial_count} quintetos"
                print(f"   {error_msg}")
                return error_msg

            # Verificación de marcador: comparar con resultado real
            score_ok, score_msg = self._verify_score(game_id, extracted_data)
            print(f"   [INFO] {score_msg}")
            if not score_ok:
                error_msg = f"RECHAZADO {game_id}: {score_msg}"
                print(f"   [ERROR] {error_msg}")
                return error_msg

            fieldnames = ['id_partido', 'periodo', 'tiempo', 'marcador_local', 'marcador_visitante', 'equipo', 'jugador', 'accion', 'estadistica']
            fd, temp_path = tempfile.mkstemp(
                prefix=f".play_by_play_{game_id}.",
                suffix=".tmp",
                dir=self.output_dir,
            )
            os.close(fd)
            try:
                with open(temp_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(extracted_data)
                os.replace(temp_path, output_filepath)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            print(f"   [OK] CSV generado: {output_filepath}")
            return f"OK: {game_id} ({len(extracted_data)} jugadas, {cinco_inicial_count} quintetos)"

        except Exception as e:
            try:
                driver.get('about:blank')
            except Exception as cleanup_error:
                print(f"   [AVISO] Error en cleanup del driver: {cleanup_error}")
            return f"ERROR en {game_id}: {e}"
        finally:
            if driver:
                try:
                    driver.current_url
                    self.driver_pool.put(driver)
                except Exception:
                    print("   [INFO] Descartando navegador cerrado; creando uno nuevo...")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    try:
                        self.driver_pool.put(self.setup_undetected_driver())
                    except Exception as replacement_error:
                        print(f"   [ERROR] No se pudo recrear Chrome: {replacement_error}")

    def verify_existing_files(self, game_ids):
        """Verifica que los ficheros PBP existentes tienen marcadores correctos."""
        print(f"\n[VERIFY] Verificando {len(game_ids)} partidos...")
        ok_count, fail_count, missing_count = 0, 0, 0
        failed_ids = []

        for game_id in game_ids:
            filepath = os.path.join(self.output_dir, f"play_by_play_{game_id}.csv")
            if not os.path.exists(filepath):
                missing_count += 1
                continue

            # Leer jugadas del CSV
            extracted_data = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    extracted_data.append(row)

            score_ok, score_msg = self._verify_score(game_id, extracted_data)
            if score_ok:
                ok_count += 1
            else:
                fail_count += 1
                failed_ids.append(game_id)
                print(f"   [FAIL] {game_id}: {score_msg}")

        print(f"\n[VERIFY] Resultado: {ok_count} OK, {fail_count} FAIL, {missing_count} sin fichero")
        if failed_ids:
            print(f"[VERIFY] IDs con marcador incorrecto: {failed_ids}")
            print(f"[VERIFY] Para re-scrapear: --force --only {' '.join(str(x) for x in failed_ids)}")
        return failed_ids

    def run_batch(self, game_ids, max_workers=1, force=False):
        start_time = time.time()

        print(f"[INFO] Creando pool de {max_workers} navegadores...")
        for _ in range(max_workers):
            self.driver_pool.put(self.setup_undetected_driver())

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._scrape_and_process_game, gid, force) for gid in game_ids]
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


def main():
    parser = argparse.ArgumentParser(
        description="Scraper de Play-by-Play de la ACB (live.acb.com)"
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Re-scrapear aunque el fichero CSV ya exista',
    )
    parser.add_argument(
        '--only', nargs='+', type=int, metavar='ID',
        help='Procesar solo estos game IDs',
    )
    parser.add_argument(
        '--workers', type=int, default=1,
        help='Número de navegadores concurrentes (default: 1, recomendado)',
    )
    parser.add_argument(
        '--verify', action='store_true',
        help='Solo verificar marcadores de ficheros existentes (no scrapea)',
    )
    args = parser.parse_args()

    # Cargar game IDs
    match_ids_file = script_dir.parent / "data" / "input" / "match_ids.json"
    try:
        with open(match_ids_file, 'r') as f:
            all_game_ids = json.load(f)['match_ids']
    except FileNotFoundError:
        print("Error: No se encuentra el fichero 'data/input/match_ids.json'")
        return

    scraper = BatchHumanLikeScraper()

    # Modo verificación
    if args.verify:
        game_ids = args.only if args.only else all_game_ids
        scraper.verify_existing_files(game_ids)
        return

    # Modo scraping
    game_ids = args.only if args.only else all_game_ids
    print(f"[INFO] Partidos a procesar: {len(game_ids)}")

    if game_ids:
        workers = min(args.workers, len(game_ids))
        scraper.run_batch(game_ids, max_workers=workers, force=args.force)
    else:
        print("No hay partidos seleccionados para procesar.")


if __name__ == "__main__":
    main()
