import time
import random
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

class HumanLikeScraper:
    """
    Una clase para realizar web scraping de jugadas de partidos de la ACB
    simulando un comportamiento humano para evitar bloqueos.
    """
    def __init__(self, game_id=104452):
        """
        Inicializa el scraper con un ID de partido.
        
        Args:
            game_id (int): El ID del partido a analizar.
        """
        self.game_id = game_id
        self.driver = self.setup_undetected_driver()
    
    def setup_undetected_driver(self):
        """
        Configura e inicializa una instancia del driver de Chrome
        con 'undetected-chromedriver' para evitar la detección de automatización.
        """
        options = uc.ChromeOptions()
        
        # --- Configuraciones para evitar la detección ---
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1366,768')
        # --- MODO INVISIBLE (HEADLESS) ---
        options.add_argument('--headless=new')
        
        # --- User Agent personalizado ---
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # --- Inicializa el driver ---
        print("🚀 Configurando el navegador en modo invisible...")
        driver = uc.Chrome(options=options)
        
        # --- Scripts de JavaScript para parecer más humano ---
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                delete Object.getPrototypeOf(navigator).webdriver;
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-ES', 'es', 'en']
                });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({ query: () => Promise.resolve({ state: 'granted' }) })
                });
            '''
        })
        
        return driver
    
    def scroll_to_bottom(self):
        """
        (ESTRATEGIA FINAL - BÚSQUEDA DEL "CINCO INICIAL" - OPTIMIZADA)
        Usa la pulsación de la tecla 'FIN' de forma rápida y detiene el scroll 
        solo cuando ha encontrado los 10 eventos de "Cinco Inicial".
        """
        print("📜 Iniciando estrategia de scroll definitiva buscando el 'Cinco Inicial'...")
        
        try:
            # 1. ESPERAR y ENFOCAR el contenedor correcto
            print("Esperando a que el contenedor de jugadas esté listo...")
            plays_container_selector = (By.CSS_SELECTOR, ".pp")
            plays_container = WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located(plays_container_selector)
            )
            print("✅ Contenedor listo. Haciendo clic para asegurar el foco...")
            ActionChains(self.driver).move_to_element(plays_container).click().perform()
            time.sleep(1)

            # 2. Bucle de SCROLL hasta encontrar los 10 "Cinco Inicial"
            print("Iniciando scroll rápido y continuo...")
            found_count = 0
            
            while True:
                # Busca cuántos eventos "Cinco Inicial" hay actualmente
                starting_five_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Cinco Inicial')]")
                current_count = len(starting_five_elements)

                # Imprime el progreso solo cuando encuentra nuevos eventos
                if current_count > found_count:
                    print(f"🔄 Progreso: {current_count}/10 eventos 'Cinco Inicial' encontrados.")
                    found_count = current_count

                # Si ya tenemos los 10, hemos llegado al final
                if current_count >= 10:
                    print("✅ ¡Objetivo encontrado! Se han cargado los 10 'Cinco Inicial'.")
                    break

                # Si no, pulsa 'FIN' para cargar más contenido
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                # Pausa mínima para no saturar la web y permitir que cargue
                time.sleep(0.3)

            print("✅ Se ha llegado al final de la página.")

        except Exception as e:
            print(f"❌ Error durante la fase de scroll: {e}")

    
    def extract_and_save_plays(self):
        """
        Método principal que orquesta la navegación, el scroll, la extracción
        y el guardado de las jugadas en un fichero CSV.
        """
        url = f"https://jv.acb.com/es/{self.game_id}/jugadas"
        
        print(f"🎯 Navegando como un humano a: {url}")
        self.driver.get(url)
        time.sleep(2)
        
        # --- NUEVO FLUJO: Esperar, enfocar y hacer scroll ---
        self.scroll_to_bottom()
        
        # --- Asegura que el filtro "Todos" está seleccionado (después del scroll) ---
        try:
            todos_button = self.driver.find_element(By.XPATH, "//div[@role='button' and text()='Todos']")
            if 'fi-per__item--selected' not in todos_button.get_attribute('class'):
                print("🖱️ El filtro 'Todos' no estaba seleccionado. Haciendo clic.")
                self.driver.execute_script("arguments[0].click();", todos_button)
                time.sleep(1)
        except Exception as e:
            print(f"⚠️ No se pudo encontrar o interactuar con el filtro 'Todos'. Error: {e}")
        
        time.sleep(1)
        
        # --- FASE DE EXTRACCIÓN OPTIMIZADA CON BEAUTIFULSOUP ---
        print("\n🔍 Extrayendo datos de todas las jugadas de forma optimizada...")
        
        # 1. Obtener todo el HTML de la página una sola vez
        page_html = self.driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')

        # 2. Encontrar todos los elementos de jugada con BeautifulSoup (mucho más rápido)
        play_elements = soup.select(".pp-item")
        
        extracted_data = []
        for play in play_elements:
            try:
                # Se utiliza select_one, que es más rápido y devuelve None si no encuentra nada
                periodo_tag = play.select_one(".ge-match-time-info")
                tiempo_tag = play.select_one(".ge-match-time-sec")
                jugador_tag = play.select_one(".pp-item-mes-portrait__name")
                accion_tag = play.select_one(".pp-item-mes-info-text__desc")
                stats_tag = play.select_one(".pp-item-mes-info-text__stats")
                equipo_img_tag = play.select_one(".pp-item-mes__team")
                marcador_local_tag = play.select_one(".pp-item-mes-score__local")
                marcador_visitante_tag = play.select_one(".pp-item-mes-score__visitor")

                play_data = {
                    'periodo': periodo_tag.text if periodo_tag else None,
                    'tiempo': tiempo_tag.text if tiempo_tag else None,
                    'marcador_local': marcador_local_tag.text if marcador_local_tag else None,
                    'marcador_visitante': marcador_visitante_tag.text if marcador_visitante_tag else None,
                    'equipo': equipo_img_tag['alt'] if equipo_img_tag else None,
                    'jugador': jugador_tag.text if jugador_tag else None,
                    'accion': accion_tag.text if accion_tag else None,
                    'estadistica': stats_tag.text if stats_tag else None,
                }
                extracted_data.append(play_data)
            except Exception as e:
                print(f"⚠️ Error extrayendo una jugada: {e}")

        print(f"✅ Extracción finalizada. Jugadas encontradas: {len(extracted_data)}")

        # --- Guardar los datos en un fichero CSV ---
        if extracted_data:
            filename = f"partido_{self.game_id}.csv"
            print(f"💾 Guardando datos en el fichero: {filename}")
            
            # Las cabeceras del CSV
            fieldnames = ['periodo', 'tiempo', 'marcador_local', 'marcador_visitante', 'equipo', 'jugador', 'accion', 'estadistica']
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(extracted_data)
                
            print(f"👍 Fichero '{filename}' guardado correctamente.")
        
        return len(extracted_data)

# --- PUNTO DE ENTRADA PRINCIPAL DEL SCRIPT ---
if __name__ == "__main__":
    scraper = None
    try:
        scraper = HumanLikeScraper(game_id=104452) 
        # La función ahora se llama extract_and_save_plays
        num_plays = scraper.extract_and_save_plays()
        print(f"\nProceso finalizado con éxito. Se han procesado y guardado {num_plays} jugadas.")
        
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante la ejecución: {e}")
        
    finally:
        if scraper and scraper.driver:
            try:
                scraper.driver.quit()
                print("👍 Navegador cerrado correctamente.")
            except OSError as e:
                if "WinError 6" in str(e):
                    print("👍 Navegador cerrado (se ignoró el error benigno WinError 6).")
                else:
                    raise e