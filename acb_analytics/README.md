# 🏀 ACB Advanced Analytics con PySpark

Sistema de análisis avanzado de estadísticas de basketball de la ACB usando PySpark.

## 📊 Métricas Implementadas

### Métricas de Eficiencia
- **True Shooting % (TS%)**: Eficiencia real considerando t2, t3 y tl
- **Effective Field Goal % (eFG%)**: FG% ajustado por valor de triples
- **Points Per Shot (PPS)**: Puntos generados por intento

### Métricas de Uso
- **Usage Rate**: % de posesiones usadas por jugador
- **Assist Ratio**: % de posesiones terminadas en asistencia
- **Turnover Ratio**: % de posesiones terminadas en pérdida

### Métricas de Creación
- **AST/TOV Ratio**: Ratio asistencias vs pérdidas (para playmakers)
- **Three Point Rate**: % de tiros que son triples
- **Free Throw Rate**: Capacidad de generar faltas

### Rating Global
- **PER (Player Efficiency Rating)**: Rating completo de performance
- **Rebounds Per Minute**: Eficiencia en rebote

## 🚀 Quick Start

### 1. Instalación

```bash
# Instalar dependencias
pip install -r requirements_analytics.txt
```

### 2. Generar Datos (si no los tienes)

```bash
# Desde el directorio raíz
python main.py
```

### 3. Ejecutar Análisis

```bash
cd acb_analytics
python analyze_players.py
```

## 📁 Estructura del Proyecto

```
acb_analytics/
├── data/
│   ├── raw/              # CSVs originales del scraper
│   └── processed/        # Parquet files procesados
├── notebooks/
│   └── (próximamente análisis interactivos)
├── src/
│   ├── metrics/
│   │   └── player_metrics.py    # Métricas avanzadas
│   ├── models/
│   │   └── (próximamente ML models)
│   └── utils/
│       └── spark_utils.py       # Utilidades Spark
├── outputs/                      # Resultados del análisis
├── analyze_players.py            # Script principal
└── requirements_analytics.txt    # Dependencias
```

## 📊 Outputs Generados

Después de ejecutar `analyze_players.py`:

1. **`outputs/player_stats_with_metrics.parquet`**
   - Datos completos con todas las métricas por partido

2. **`outputs/player_summary.csv`**
   - Resumen agregado por jugador
   - Promedios, totales, desviaciones estándar
   - Fácil de abrir en Excel/Sheets

## 🔍 Análisis Disponibles

### Top Performers
- Top scorers por eficiencia (TS%)
- Top playmakers (AST/TOV)
- Top usage players
- Top overall (PER)

### Agregaciones
- Estadísticas promedio por jugador
- Totales de temporada
- Métricas de consistencia (stddev)

## 📈 Próximas Implementaciones

- [ ] Análisis de quintetos óptimos
- [ ] Clustering de estilos de juego
- [ ] Modelos predictivos (ML)
- [ ] Network analysis (passing networks)
- [ ] Análisis temporal (form, streaks)
- [ ] Dashboard interactivo

## 💡 Ejemplos de Uso

### Cargar datos procesados en notebook:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ACB Analysis").getOrCreate()

# Cargar datos con métricas
df = spark.read.parquet("outputs/player_stats_with_metrics.parquet")

# Top 10 por TS%
df.select("nombre", "ts_percentage").orderBy("ts_percentage", ascending=False).show(10)
```

### Filtrar jugadores eficientes:

```python
# Jugadores con TS% > 60 y min 100 minutos jugados
efficient_players = df.filter(
    (df.ts_percentage > 60) &
    (df.minutos_float > 100)
)
```

## 🎯 Interpretación de Métricas

| Métrica | Bueno | Muy Bueno | Élite |
|---------|-------|-----------|-------|
| **TS%** | >55% | >60% | >65% |
| **eFG%** | >50% | >55% | >60% |
| **AST/TOV** | >1.5 | >2.0 | >3.0 |
| **PER** | >15 | >20 | >25 |
| **3P%** | >35% | >40% | >45% |

## 📚 Referencias

- [Basketball Reference - Advanced Stats](https://www.basketball-reference.com/about/glossary.html)
- [NBA Stats Glossary](https://www.nba.com/stats/help/glossary)
- [Dean Oliver's Four Factors](https://www.basketball-reference.com/about/factors.html)

## 🤝 Contribuir

Para añadir nuevas métricas:

1. Añadir función en `src/metrics/player_metrics.py`
2. Actualizar `calculate_all_advanced_metrics()`
3. Documentar en este README

## 📝 Notas Técnicas

- **PySpark Version**: 3.5.0+
- **Optimizaciones**: Adaptive Query Execution habilitado
- **Partitions**: 200 por defecto (ajustable según datos)
- **Memory**: Configurado para 4GB (ajustable en scripts)

---

**Creado para análisis avanzado de basketball ACB** 🏀
