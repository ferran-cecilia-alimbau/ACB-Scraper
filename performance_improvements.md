# Performance Improvements for ACB Scraper

After analyzing the code, I've identified these performance bottlenecks and their solutions:

## 1. Inefficient Player Profile Lookups

**Issue**: In `main.py`, line 121 performs an inefficient lookup using DataFrames values:
```python
if profile['player_id'] not in dataframes['output_file_player_profiles']['player_id'].values
```
This is an O(n) operation performed repeatedly, which can be slow with large datasets.

**Solution**: Convert to a set for O(1) lookups:
```python
# At the beginning of process_and_save_data function:
existing_profile_ids_set = set(dataframes['output_file_player_profiles']['player_id'].values)

# Then replace the lookup with:
if profile['player_id'] not in existing_profile_ids_set
```

## 2. Rate Limiting Blocks Event Loop

**Issue**: In `scraper.py`, the rate limiting implementation blocks the entire event loop:
```python
async with session.get(url, headers=headers) as response:
    await asyncio.sleep(config.get('rate_limit', 1))
    response.raise_for_status()
    return await response.text()
```

**Solution**: Move the sleep *after* getting the response text to avoid blocking:
```python
async with session.get(url, headers=headers) as response:
    response.raise_for_status()
    text = await response.text()
    await asyncio.sleep(config.get('rate_limit', 1))
    return text
```

## 3. Fixed Memory Configuration in PySpark

**Issue**: In `calculate_team_stats.py`, hard-coded memory values may not be optimal:
```python
.config("spark.executor.memory", "4g")
.config("spark.driver.memory", "4g")
```

**Solution**: Make memory configurable based on environment or system resources:
```python
import os

# Get memory from environment or use default
executor_memory = os.environ.get("SPARK_EXECUTOR_MEMORY", "4g")
driver_memory = os.environ.get("SPARK_DRIVER_MEMORY", "4g")

spark = SparkSession.builder \
    .appName("EstadisticasBaloncesto") \
    .config("spark.executor.memory", executor_memory) \
    .config("spark.driver.memory", driver_memory) \
    .getOrCreate()
```

## 4. Inefficient DataFrame Duplicate Removal

**Issue**: In `main.py`, line 131 uses `drop_duplicates` with `keep='last'` which can be slow:
```python
dataframes[key].drop_duplicates(subset=config['id_columns'][key], keep='last', inplace=True)
```

**Solution**: Use `keep='first'` if possible as it's more efficient or process in chunks for large datasets.

## 5. Unnecessary Recomputation in calculate_team_stats.py

**Issue**: Several columns are recalculated that could be cached or stored.

**Solution**: Use Spark's caching for frequently reused DataFrames:
```python
# After computing important transformations
df_equipos.cache()
```

## 6. Repeated DataFrame Conversions

**Issue**: Converting between native Python types and DataFrame structures repeatedly.

**Solution**: Minimize conversions and batch operations where possible.
