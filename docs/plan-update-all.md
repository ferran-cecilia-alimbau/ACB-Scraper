# Automatización del proceso de scraping ACB

> **Estado: No implementado.** Este plan está pendiente de ejecución.

## Contexto
Actualmente el pipeline de datos requiere 3 comandos manuales separados:
1. `python scripts/get_match_ids.py` — descubre IDs de partidos del calendario ACB
2. `python main.py` — scrapea estadísticas (4 CSVs)
3. `python scripts/batch_play_by_play_v2.py` — scrapea PBP (Selenium, lento)

El objetivo es unificarlo en un solo script orquestador que detecte partidos nuevos y ejecute todo el pipeline automáticamente.

---

## Plan: Crear `scripts/update_all.py`

### Diseño general

Un orquestador que ejecuta los 3 pasos secuencialmente. Usa **subprocess** para los 3 pasos (evita conflictos de `sys.path`, `asyncio` y aislamiento de Chrome).

```
python scripts/update_all.py                    # Stats + PBP
python scripts/update_all.py --skip-pbp         # Solo stats (sin Chrome)
python scripts/update_all.py --dry-run           # Muestra qué haría sin ejecutar
python scripts/update_all.py --season-id 2026    # Temporada diferente
python scripts/update_all.py --verify-pbp        # Verificar PBP después de scrapear
```

### Flujo del orquestador

```
1. Descubrir match IDs (importar get_match_ids.get_match_ids())
   ├─ Comparar con match_ids.json existente → calcular new_ids
   └─ Actualizar match_ids.json (ordenado ascendente)

2. Scrapear estadísticas (subprocess: python main.py)
   └─ main.py ya gestiona incremental (solo partidos nuevos)

3. Scrapear PBP (subprocess: python batch_play_by_play_v2.py --only <new_ids>)
   └─ También incluir IDs con stats pero sin fichero PBP

4. [Opcional] Verificar PBP (subprocess: --verify)

5. Resumen final: cuántos partidos nuevos, qué pasos OK/FAIL, tiempo total
```

### CLI (argparse)

| Flag | Descripción | Default |
|------|-------------|---------|
| `--season-id INT` | Temporada ACB | 2026 |
| `--skip-pbp` | Saltar paso PBP | false |
| `--verify-pbp` | Verificar marcadores PBP | false |
| `--pbp-workers INT` | Browsers concurrentes | 1 |
| `--force-pbp` | Re-scrapear PBP existentes | false |
| `--dry-run` | Solo mostrar qué haría | false |

### Gestión de errores

- **Paso 1 falla** (red): abortar, match_ids.json intacto
- **Paso 1 OK, Paso 2 falla**: match_ids.json actualizado; en la siguiente ejecución main.py reintenta los mismos partidos
- **Paso 2 OK, Paso 3 falla**: stats guardadas; PBP parcialmente guardado (ficheros individuales). En la siguiente ejecución se detectan los PBP que faltan
- Cada paso envuelto en try/except; el resumen final siempre se muestra

### Detección de partidos nuevos para PBP

No solo los `new_ids` del paso 1, sino también partidos que tienen stats pero les falta el fichero PBP (por fallos previos):
```python
existing_pbp = {int(f.stem.replace("play_by_play_", "")) for f in PBP_DIR.glob("play_by_play_*.csv")}
missing_pbp = [id for id in all_ids if id not in existing_pbp]
pbp_ids = sorted(set(new_ids) | set(missing_pbp))
```

---

## Ficheros a modificar

| Fichero | Acción |
|---------|--------|
| `scripts/get_match_ids.py` | Mover líneas 52-61 dentro de `if __name__ == "__main__":` para que sea importable sin efecto secundario |
| `scripts/update_all.py` | **NUEVO** — orquestador (~150 líneas) |

### Refactor de `get_match_ids.py` (mínimo)

Mover el código de ejecución (líneas 52-61) dentro de `if __name__ == "__main__":`. Las funciones `get_match_ids()` y `save_to_json()` quedan intactas y se pueden importar.

---

## Verificación

1. `python scripts/update_all.py --dry-run` — debe mostrar los pasos sin ejecutar nada
2. `python scripts/update_all.py --skip-pbp` — ejecuta pasos 1+2, reporta resumen
3. `python scripts/update_all.py` — pipeline completo (necesita Chrome)
4. Comprobar que `match_ids.json` queda actualizado y ordenado
5. Comprobar que ejecutar dos veces seguidas no re-scrapea nada ("0 nuevos partidos")
