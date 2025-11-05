# 🏀 Guía Completa de Análisis Avanzados ACB

Esta guía documenta TODOS los análisis implementados en el sistema de analytics.

## 📊 Tabla de Contenidos

1. [Métricas de Jugadores](#métricas-de-jugadores)
2. [Métricas de Equipos](#métricas-de-equipos)
3. [Análisis de Quintetos](#análisis-de-quintetos)
4. [Clustering](#clustering)
5. [Análisis de Consistencia](#análisis-de-consistencia)

---

## 1. 📈 Métricas de Jugadores

### Métricas Implementadas (11)

| Métrica | Descripción | Interpretación | Bueno | Élite |
|---------|-------------|----------------|-------|-------|
| **TS%** | True Shooting % | Eficiencia real de tiro | >55% | >65% |
| **eFG%** | Effective FG% | FG% ajustado por triples | >50% | >60% |
| **Usage Rate** | % de posesiones usadas | Volumen de uso | >25% | >30% |
| **AST Ratio** | % posesiones en asistencia | Creación de juego | >20% | >30% |
| **TOV Ratio** | % posesiones en pérdida | Cuidado del balón | <15% | <10% |
| **AST/TOV** | Ratio asist/pérdidas | Playmaking | >2.0 | >3.0 |
| **REB/MIN** | Rebotes por minuto | Eficiencia rebote | >0.3 | >0.5 |
| **PPS** | Puntos por intento | Eficiencia scoring | >1.0 | >1.2 |
| **PER** | Player Efficiency Rating | Rating global | >15 | >25 |
| **3P Rate** | % de tiros que son 3s | Estilo de tiro | >35% | >45% |
| **FT Rate** | Ratio TL/FGA | Generación faltas | >0.3 | >0.5 |

### Código de Ejemplo

```python
from pyspark.sql import SparkSession
from metrics.player_metrics import calculate_all_advanced_metrics

spark = SparkSession.builder.appName("ACB").getOrCreate()
df = spark.read.csv("data/estadisticas_todos_partidos.csv", header=True)

# Calcular TODAS las métricas de una vez
df_with_metrics = calculate_all_advanced_metrics(df)

# Ver top performers
df_with_metrics.select("nombre", "ts_percentage", "per_simple") \
    .orderBy("per_simple", ascending=False) \
    .show(10)
```

---

## 2. 🏛️ Métricas de Equipos

### Four Factors de Dean Oliver

Los 4 factores que más correlacionan con victorias:

1. **Shooting (eFG%)**: Eficiencia de tiro
2. **Turnovers (TOV%)**: Cuidado del balón (menor mejor)
3. **Rebounding (OREB%)**: Rebote ofensivo
4. **Free Throws (FT Rate)**: Tiros libres generados

### Métricas Adicionales

- **Pace**: Posesiones por partido (velocidad de juego)
- **Offensive Rating**: Puntos por 100 posesiones
- **3P Rate**: % de tiros que son triples
- **Assist Rate**: % de canastas asistidas

### Identificación de Estilos

El sistema clasifica automáticamente a equipos en:

**Por Pace:**
- Fast (>75 posesiones)
- Medium (65-75)
- Slow (<65)

**Por Tiro:**
- Three Heavy (>40% triples)
- Balanced (30-40%)
- Inside Game (<30%)

**Por Ofensiva:**
- Ball Movement (>65% AST rate)
- Mixed (55-65%)
- Isolation (<55%)

### Ejemplo de Uso

```python
from metrics.team_metrics import calculate_all_team_metrics

# Calcula TODAS las métricas de equipo
df_totals, df_averages = calculate_all_team_metrics(df_players)

# Ver Four Factors
df_averages.select("equipo", "efg_percent_avg", "tov_percent_avg",
                   "ft_rate_avg", "pace_avg").show()

# Ver estilos identificados
df_averages.select("equipo", "style_pace", "style_shooting", "style_offense").show()
```

---

## 3. 👥 Análisis de Quintetos

### Funcionalidades

1. **Identificación de Quintetos Iniciales**
   - Detecta automáticamente los 5 titulares por partido
   - Crea ID único por combinación

2. **Performance por Quinteto**
   - +/- promedio
   - Puntos promedio
   - Número de partidos jugados

3. **Top/Bottom Lineups**
   - Mejores quintetos por +/-
   - Peores combinaciones (para evitar)

4. **Análisis de Sinergia**
   - Compara rendimiento de jugador A con jugador B vs sin él
   - Identifica mejores compañeros para cada jugador

### Ejemplo de Uso

```python
from models.lineup_analysis import (
    identify_lineups_from_starters,
    calculate_lineup_performance,
    get_best_lineups_by_plus_minus,
    find_best_teammates_for_player
)

# Identificar quintetos
lineups = identify_lineups_from_starters(df)
lineup_stats = calculate_lineup_performance(lineups)

# Top 10 quintetos
best_lineups = get_best_lineups_by_plus_minus(lineup_stats, top_n=10)
best_lineups.select("equipo", "avg_plus_minus", "player_names").show()

# Mejores compañeros de un jugador específico
best_teammates = find_best_teammates_for_player(df, player_id=12345)
best_teammates.show()
```

### Insights que Provee

- ✅ Qué combinaciones de 5 jugadores funcionan mejor
- ✅ Cuánto mejora/empeora un jugador con ciertos compañeros
- ✅ Identifica "chemistry" entre jugadores
- ✅ Ayuda a optimizar rotaciones

---

## 4. 🎨 Clustering (Machine Learning)

### Clustering de Jugadores

**Algoritmo**: K-Means
**Features usadas**:
- Puntos promedio
- Rebotes promedio
- Asistencias promedio
- TS% (eficiencia)
- Usage Rate
- Three Point Rate
- AST/TOV

**Arquetipos típicos identificados**:
1. **Scorers**: Alto PPG, alto usage, TS% alto
2. **Playmakers**: Alto AST, bajo TOV, AST/TOV élite
3. **Big Men**: Alto rebote, bajo 3P rate, interior
4. **3&D Wings**: Alto 3P%, defensa (robos+tapones)
5. **Role Players**: Stats balanceadas, bajo usage

### Clustering de Equipos

**Features usadas**:
- Pace
- 3PA per game
- Assist rate
- eFG%
- TOV%

**Estilos identificados**:
- **Pace & Space**: Rápido + muchos triples
- **Traditional**: Lento + interior
- **Balanced**: Equilibrado

### Ejemplo de Uso

```python
from models.clustering import (
    cluster_players_by_style,
    cluster_teams_by_style,
    find_similar_players
)

# Clustering de jugadores (5 grupos)
df_clustered, model, centers = cluster_players_by_style(
    df_summary, n_clusters=5, min_minutes=100.0
)

# Ver distribución
df_clustered.groupBy("cluster").count().show()

# Encontrar jugadores similares a uno específico
similar = find_similar_players(df_clustered, player_id=12345, top_n=5)
similar.show()

# Clustering de equipos
df_team_clustered, team_model = cluster_teams_by_style(df_team_avg, n_clusters=3)
df_team_clustered.select("equipo", "style_cluster", "pace_avg").show()
```

### Insights que Provee

- ✅ Identifica jugadores con perfil similar (comparables)
- ✅ Agrupa equipos por filosofía de juego
- ✅ Ayuda en scouting (buscar tipo de jugador específico)
- ✅ Identifica "nicho" de cada jugador

---

## 5. 📊 Análisis de Consistencia

### Métricas de Consistencia

1. **Coefficient of Variation (CV)**
   - Fórmula: stddev / mean
   - Menor = más consistente
   - CV < 0.3 = muy consistente
   - CV > 0.5 = volátil

2. **Consistency Score**
   - Escala 0-100
   - 100 = perfectamente consistente
   - >80 = muy predecible

3. **Range & IQR**
   - Range: max - min
   - IQR: Q3 - Q1 (excluye outliers)

### Detección de Rachas (Streaks)

**Hot Streak**: 3+ partidos consecutivos por encima de media personal × 1.5

**Cold Streak**: 3+ partidos por debajo

**Funcionalidad**:
- Identifica jugadores actualmente en racha
- Detecta patrones de "hot hand"
- Analiza probabilidad de mantener racha

### Análisis de Volatilidad

**Player Types**:
- **Stable** (CV < 30%): Predecibles, confiables
- **Moderate** (30-50%): Variabilidad normal
- **Volatile** (>50%): Alto riesgo, alto reward

### Análisis Clutch

**Clutch Performers**: Jugadores que rinden MEJOR en:
- Partidos cerrados (diferencia ≤ 5 puntos)
- Últimos minutos
- Situaciones de presión

### Tendencias

**Moving Average**: Ventana deslizante para detectar:
- Improving: Últimos partidos mejor que anteriores
- Declining: Bajando el nivel
- Stable: Sin cambios

### Game Score Variance

**Game Score** (John Hollinger):
```
GS = PTS + 0.4×FGM - 0.7×FGA - 0.4×(FTA-FTM) + 0.7×OREB +
     0.3×DREB + STL + 0.7×AST + 0.7×BLK - 0.4×PF - TOV
```

Mide performance completa. Su varianza indica consistencia global.

### Ejemplo de Uso

```python
from models.consistency_analysis import (
    calculate_consistency_metrics,
    detect_scoring_streaks,
    identify_hot_hand_players,
    calculate_player_volatility
)

# Consistencia
consistency = calculate_consistency_metrics(df)
consistency.orderBy("cv_points").show(10)  # Más consistentes

# Jugadores en racha AHORA
streaks = detect_scoring_streaks(df)
hot_players = identify_hot_hand_players(streaks, min_streak_games=3)
hot_players.show()

# Volatilidad
volatility = calculate_player_volatility(df)
volatility.filter(col("player_type") == "Volatile").show()
```

### Insights que Provee

- ✅ Identifica jugadores "confiables" vs "inconsistentes"
- ✅ Detecta rachas calientes (para aprovechar)
- ✅ Identifica clutch performers
- ✅ Predice regresión a la media
- ✅ Ayuda en fantasy y apuestas

---

## 🚀 Scripts Disponibles

### 1. `analyze_players.py`
Análisis básico de jugadores:
- Métricas avanzadas
- Top performers
- Resumen por jugador

```bash
python analyze_players.py
```

### 2. `analyze_advanced.py` ⭐
Análisis COMPLETO:
- Todo lo de analyze_players.py
- Métricas de equipos
- Quintetos óptimos
- Clustering (jugadores y equipos)
- Consistencia y streaks
- 10+ outputs generados

```bash
python analyze_advanced.py
```

---

## 📁 Outputs Generados

Todos los análisis se guardan en `outputs/`:

### Parquet Files (para Spark)
- `player_metrics.parquet` - Todas las métricas por partido
- `player_summary.parquet` - Resumen por jugador
- `team_totals.parquet` - Totales de equipo por partido
- `team_averages.parquet` - Promedios de temporada
- `lineup_stats.parquet` - Estadísticas de quintetos
- `player_clusters.parquet` - Clustering de jugadores
- `team_clusters.parquet` - Clustering de equipos
- `consistency.parquet` - Métricas de consistencia
- `volatility.parquet` - Análisis de volatilidad
- `hot_hands.parquet` - Jugadores en racha

### CSV Files (para Excel)
- `player_summary.csv`
- `team_summary.csv`
- `top_lineups.csv`
- `consistency_leaders.csv`

---

## 💡 Casos de Uso

### Para Coaches
- Identificar quintetos óptimos
- Analizar sinergias entre jugadores
- Optimizar rotaciones
- Identificar estilos de oponentes

### Para GMs/Scouts
- Clustering para encontrar jugadores similares
- Análisis de consistencia para firmas
- Identificar arquetipos necesarios
- Métricas avanzadas para valuación

### Para Analistas
- Four Factors para predecir victorias
- Trends para detectar mejoras/declives
- Métricas de eficiencia vs volumen
- Análisis comparativo entre jugadores

### Para Fantasy/Betting
- Hot hand detection
- Consistency scores
- Volatility analysis
- Clutch performers

---

## 🎯 Próximas Implementaciones Sugeridas

- [ ] Network analysis (passing networks)
- [ ] Shot charts & heat maps
- [ ] Modelos predictivos ML
- [ ] Dashboard interactivo (Plotly/Streamlit)
- [ ] Defensive metrics (cuando haya datos)
- [ ] Play-by-play analysis (si hay datos disponibles)
- [ ] Plus/Minus lineups ajustados
- [ ] Win probability models

---

## 📚 Referencias & Bibliografía

1. **Dean Oliver** - "Basketball on Paper" (Four Factors)
2. **John Hollinger** - PER y Game Score
3. **Basketball Reference** - Definiciones de métricas
4. **NBA Advanced Stats** - TS%, eFG%, Usage
5. **Nylon Calculus** - Modern analytics

---

**Creado para análisis profesional de basketball ACB** 🏀
