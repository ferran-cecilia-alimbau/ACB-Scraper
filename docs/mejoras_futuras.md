# Mejoras Futuras para ACB-Scraper

Este documento lista las mejoras identificadas pero no implementadas aún, organizadas por prioridad.

> **Nota**: Los items 4-5 aplican a `scripts/batch_play_by_play.py` (v1). Existe una v2 (`scripts/batch_play_by_play_v2.py`) con implementación diferente que usa webdriver-manager + opciones de Chromium para Ubuntu Server.

## ~~🟡 Nivel 2 - Alta Prioridad~~ ✅ COMPLETADO

### ~~1. Refactorizar Variables Globales a Clase RateLimiter~~ ✅
**Ubicación**: `http_client.py:22-23`

**Problema Actual**:
```python
last_request_time = 0  # Global mutable
rate_limit_lock = asyncio.Lock()  # Global
```

**Riesgo**: Estado compartido entre importaciones, tests difíciles de aislar, no reutilizable.

**Solución Propuesta**:
```python
class RateLimiter:
    def __init__(self, rate_limit: float = 1.0):
        self._last_request_time = 0
        self._lock = asyncio.Lock()
        self._rate_limit = rate_limit

    async def wait_if_needed(self):
        async with self._lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self._rate_limit:
                wait_time = self._rate_limit - time_since_last
                await asyncio.sleep(wait_time)
            self._last_request_time = time.time()
```

**Impacto**: Mejor encapsulación, tests más fáciles, código más reutilizable.

---

### ~~2. Unificar Validación HTML~~ ✅
**Ubicación**: `http_client.py:84` vs `scraper.py:61`

**Problema Actual**:
- `http_client.py` valida `>= 100 bytes`
- `scraper.py` valida `>= 200 bytes`

**Riesgo**: Inconsistencia puede causar false positives/negatives.

**Solución**:
1. Crear constante `MIN_VALID_HTML_LENGTH = 200` en `constants.py`
2. Usar en ambos lugares:
```python
# En ambos archivos
if not html or len(html) < const.MIN_VALID_HTML_LENGTH:
    logger.error(f"HTML demasiado corto: {len(html)} bytes")
    return None
```

**Impacto**: Validación consistente, menos falsos positivos.

---

### ~~3. Proteger .strip() en utils.py~~ ✅
**Ubicación**: `utils.py:78, 80`

**Problema Actual**:
```python
except Exception as e:
    logger.warning(f"Error al procesar lugar de nacimiento '{birthplace_str}': {str(e)}")
    return birthplace_str.strip(), ""  # ❌ Crashea si birthplace_str es None
```

**Solución**:
```python
except Exception as e:
    logger.warning(f"Error al procesar lugar de nacimiento '{birthplace_str}': {str(e)}")
    return birthplace_str.strip() if birthplace_str else "", ""
```

**Impacto**: Evita crashes con datos None inesperados.

---

## 🟢 Nivel 3 - Mejoras Opcionales (Considerar)

### 4. Optimizar Timeout Excesivo
**Ubicación**: `scripts/batch_play_by_play.py:225` (v1 — v2 tiene implementación diferente)

**Problema Actual**:
```python
scroll_timeout = 600  # 10 minutos máximo
```

**Riesgo**: Si el servidor deja de responder, el proceso queda colgado 10 minutos.

**Solución Propuesta**:
- Implementar detección de inactividad (si no hay nuevos elementos en 30 segundos, salir)
- Timeout progresivo basado en tamaño de página
- Verificación periódica de "página stuck"

```python
scroll_timeout = 300  # 5 minutos máximo
inactivity_timeout = 30  # 30 segundos sin cambios
last_item_count = 0
no_change_count = 0

while time.time() - start_time < scroll_timeout:
    current_count = len(driver.find_elements(By.CSS_SELECTOR, ".pp-item"))

    if current_count == last_item_count:
        no_change_count += 1
        if no_change_count >= 6:  # 30 segundos sin cambios
            print("   [OK] No hay más contenido nuevo")
            break
    else:
        no_change_count = 0
        last_item_count = current_count

    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
    time.sleep(5)
```

**Impacto**: Menos tiempo desperdiciado, detección más rápida de errores.

---

### 5. Mejorar Gestión de Recursos en ThreadPoolExecutor
**Ubicación**: `scripts/batch_play_by_play.py:322-343` (v1 — v2 tiene implementación diferente)

**Problema Actual**:
- ThreadPoolExecutor sin context manager completo
- Drivers pueden quedar abiertos si hay exception
- Queue puede tener drivers zombie

**Solución Propuesta**:
```python
def run_batch(self, game_ids, max_workers=4):
    start_time = time.time()
    drivers = []

    try:
        print(f"[INFO] Creando pool de {max_workers} navegadores...")
        for _ in range(max_workers):
            driver = self.setup_undetected_driver()
            drivers.append(driver)
            self.driver_pool.put(driver)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._scrape_and_process_game, gid)
                      for gid in game_ids]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if "SALTADO" not in result:
                        print(result)
                except Exception as e:
                    print(f"Error en un hilo de ejecución: {e}")
    finally:
        # Asegurar limpieza de todos los drivers
        print("[INFO] Limpiando y cerrando navegadores...")
        for driver in drivers:
            try:
                driver.quit()
            except Exception as e:
                print(f"Error cerrando driver: {e}")

        # Limpiar queue
        while not self.driver_pool.empty():
            try:
                self.driver_pool.get_nowait()
            except:
                break

    end_time = time.time()
    print(f"\n--- Lote completado en {end_time - start_time:.2f} segundos ---")
```

**Impacto**: No más memory leaks, cleanup garantizado.

---

### 6. Estandarizar Logging con __name__
**Ubicación**: Todos los archivos Python

**Problema Actual**:
```python
logger = logging.getLogger('basketball_scraper')  # Nombre hardcoded
```

**Solución**:
```python
logger = logging.getLogger(__name__)  # Usa el nombre del módulo
```

**Beneficios**:
- Logs jerárquicos más claros (e.g., `acb_scraper.http_client`)
- Mejor trazabilidad del origen de cada log
- Estándar de Python

**Cambios Necesarios** (4 archivos usan `getLogger('basketball_scraper')`):
1. `scraper.py`: `logger = logging.getLogger(__name__)`
2. `parsers.py`: `logger = logging.getLogger(__name__)`
3. `http_client.py`: `logger = logging.getLogger(__name__)`
4. `utils.py`: `logger = logging.getLogger(__name__)`

**Impacto**: Logs más profesionales y trazables.

---

## 📋 Otros Riesgos Identificados (No Priorizados)

### 7. Potencial Memory Leak en Scraping Largo
**Ubicación**: `scraper.py:230`

**Problema**: El set `current_profile_ids` crece indefinidamente.

**Solución**: Implementar límite máximo o limpieza periódica.

---

### 8. Sin Manejo de Señales (SIGTERM, SIGINT)
**Problema**: Si matas el proceso con Ctrl+C, los drivers quedan abiertos y CSV pueden corromperse.

**Solución**: Implementar signal handlers:
```python
import signal
import sys

def signal_handler(sig, frame):
    print('\n[INFO] Interrupción detectada. Limpiando recursos...')
    # Cerrar drivers
    # Guardar estado
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

---

## 📊 Resumen de Prioridades

| Mejora | Prioridad | Esfuerzo | Impacto | Estado |
|--------|-----------|----------|---------|--------|
| ~~Refactorizar Variables Globales~~ | ~~🟡 Alta~~ | ~~Medio~~ | ~~Alto~~ | ✅ Completado |
| ~~Unificar Validación HTML~~ | ~~🟡 Alta~~ | ~~Bajo~~ | ~~Medio~~ | ✅ Completado |
| ~~Proteger .strip()~~ | ~~🟡 Alta~~ | ~~Bajo~~ | ~~Medio~~ | ✅ Completado |
| Optimizar Timeout | 🟢 Media | Medio | Medio | 📋 Pendiente |
| Mejorar Gestión Recursos | 🟢 Media | Alto | Alto | 📋 Pendiente |
| Estandarizar Logging | 🟢 Baja | Bajo | Bajo | 📋 Pendiente |
| Memory Leak | 🟢 Baja | Bajo | Bajo | 📋 Pendiente |
| Signal Handlers | 🟢 Baja | Medio | Medio | 📋 Pendiente |

---

## ✅ Mejoras Ya Implementadas

### Fase 1 - Estabilidad (2024-11-04)
1. ✅ Consistencia de tipos en player_ids (int vs str)
2. ✅ Validación completa de config.json
3. ✅ Bounds checking en parseo de tablas
4. ✅ Manejo de DataFrame vacío

### Fase 2 - Rendimiento (2024-11-04)
5. ✅ Optimización de drop_duplicates (2-3x más rápido)
6. ✅ Paralelización de perfiles (10-15x más rápido)

### Fase 3 - Seguridad y Estabilidad (2024-11-04)
7. ✅ SSL habilitado para HTTPS verificado
8. ✅ Bare exceptions corregidas en batch_play_by_play
9. ✅ Rutas relativas convertidas a absolutas

### Fase 4 - Calidad de Código (2024-11-05)
10. ✅ Variables globales refactorizadas a clase RateLimiter
11. ✅ Validación HTML unificada (200 bytes consistente)
12. ✅ Protección .strip() en utils.py para valores None

**Mejora total**: ~6x más rápido end-to-end, más estable, seguro y mantenible.

---

## 📝 Notas Finales

- Este documento debe revisarse periódicamente antes de agregar nuevas funcionalidades
- Las prioridades pueden cambiar según necesidades del proyecto
- Cada mejora debe testearse en entorno de desarrollo antes de producción
- Mantener este documento actualizado al implementar mejoras

**Última actualización**: 2026-02-07
**Estado del proyecto**: ✅ Producción-ready con mejoras pendientes opcionales
