# verify_pbp_completeness.py

import os
import csv

def verify_completeness(pbp_directory="../data/play_by_play"):
    """
    Verifica los ficheros CSV de Play-by-Play para identificar los que están incompletos.
    Ahora considera válidos los partidos con 9 o más 'Cinco Inicial'.
    """
    if not os.path.exists(pbp_directory):
        print(f"Error: El directorio '{pbp_directory}' no existe.")
        return

    all_files = [f for f in os.listdir(pbp_directory) if f.endswith('.csv')]
    incomplete_games = []

    print(f"🔎 Verificando {len(all_files)} ficheros en '{pbp_directory}'...")

    for filename in all_files:
        filepath = os.path.join(pbp_directory, filename)
        
        try:
            game_id = filename.replace("play_by_play_", "").replace(".csv", "")
            
            cinco_inicial_count = 0
            final_partido_found = False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    accion = row.get('accion', '')
                    
                    if "Cinco Inicial" in accion:
                        cinco_inicial_count += 1
                    if "Final del Partido" in accion:
                        final_partido_found = True

            # --- INICIO DE LA MODIFICACIÓN ---
            # Ahora la condición es tener MENOS DE 9 "Cinco Inicial" para ser considerado incompleto.
            if cinco_inicial_count < 9 or not final_partido_found:
            # --- FIN DE LA MODIFICACIÓN ---
                incomplete_games.append(game_id)
                print(f"❌ Incompleto: {filename} (Cinco Inicial: {cinco_inicial_count}/10, Final: {final_partido_found})")

        except Exception as e:
            print(f"Error procesando el fichero {filename}: {e}")

    print("\n--- Verificación Finalizada ---")
    if incomplete_games:
        print("\n📋 Lista de IDs de partidos para borrar y reprocesar:")
        print(",".join(incomplete_games))
    else:
        print("\n✅ ¡Todos los partidos parecen estar completos según el nuevo criterio!")


if __name__ == "__main__":
    verify_completeness()