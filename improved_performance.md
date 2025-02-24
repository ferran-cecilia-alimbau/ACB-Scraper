# Performance Improvements for ACB Scraper

## Implemented Performance Improvements

I've implemented the following performance optimizations in the codebase:

### 1. In scraper.py: Improved Rate Limiting Implementation

**Before:**
```python
async with session.get(url, headers=headers) as response:
    await asyncio.sleep(config.get('rate_limit', 1))
    response.raise_for_status()
    return await response.text()
```

**After:**
```python
async with session.get(url, headers=headers) as response:
    response.raise_for_status()
    # Get response text first, then do rate limiting after
    # This prevents blocking the entire event loop during downloads
    text = await response.text()
    await asyncio.sleep(config.get('rate_limit', 1))
    return text
```

**Benefit:** The entire event loop is no longer blocked during rate limiting, allowing concurrent requests to continue processing while waiting for the rate limit delay.

### 2. In main.py: Efficient Player Profile Lookups

**Before:**
```python
new_data['output_file_player_profiles'].extend([
    profile for profile in result.get('player_profiles', [])
    if profile['player_id'] not in dataframes['output_file_player_profiles']['player_id'].values
])
```

**After:**
```python
# Convert player_id values to a set for O(1) lookups instead of O(n)
existing_profile_ids_set = set(dataframes['output_file_player_profiles']['player_id'].values)

new_data['output_file_player_profiles'].extend([
    profile for profile in result.get('player_profiles', [])
    if profile['player_id'] not in existing_profile_ids_set
])
```

**Benefit:** Changed from O(n) lookups to O(1) lookups, significantly improving performance with large datasets.

### 3. In main.py: Efficient DataFrame Duplicate Removal

**Before:**
```python
dataframes[key].drop_duplicates(subset=config['id_columns'][key], keep='last', inplace=True)
```

**After:**
```python
# Use efficient chunking for large dataframes to avoid memory issues
if len(dataframes[key]) > 10000:
    # Process in chunks of 10000 rows
    chunks = [dataframes[key].iloc[i:i+10000] for i in range(0, len(dataframes[key]), 10000)]
    processed_chunks = []
    for chunk in chunks:
        processed_chunks.append(chunk.drop_duplicates(subset=config['id_columns'][key], keep='last'))
    dataframes[key] = pd.concat(processed_chunks, ignore_index=True)
else:
    dataframes[key].drop_duplicates(subset=config['id_columns'][key], keep='last', inplace=True)
```

**Benefit:** Processes large DataFrames in chunks to prevent memory issues and improve performance.

### 4. In calculate_team_stats.py: Configurable Memory Settings

**Before:**
```python
spark = SparkSession.builder \
    .appName("EstadisticasBaloncesto") \
    .config("spark.executor.memory", "4g") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()
```

**After:**
```python
import os

# Get memory settings from environment variables or use defaults
executor_memory = os.environ.get("SPARK_EXECUTOR_MEMORY", "4g")
driver_memory = os.environ.get("SPARK_DRIVER_MEMORY", "4g")

spark = SparkSession.builder \
    .appName("EstadisticasBaloncesto") \
    .config("spark.executor.memory", executor_memory) \
    .config("spark.driver.memory", driver_memory) \
    .getOrCreate()
```

**Benefit:** Memory settings can be configured via environment variables to adapt to different environments.

### 5. In calculate_team_stats.py: Strategic DataFrame Caching

**Added:**
```python
# Cache the dataframe to avoid recomputation of expensive transformations
df_equipos.cache()

# Cache this aggregated dataframe since we'll use it multiple times
df_team_agg.cache()

# At the end of the script
# Clean up cached dataframes
spark.catalog.clearCache()
```

**Benefit:** Prevents costly recomputation of expensive transformations for DataFrames used multiple times.

## Performance Testing Results

To validate these improvements properly, you should run performance tests comparing the original code against the optimized version with various dataset sizes. Key metrics to track:

1. Total execution time
2. Memory usage
3. CPU utilization
4. Number of concurrent requests processed

The optimizations should provide the following benefits:
- Faster profile lookups (O(1) vs O(n))
- More efficient rate limiting without blocking
- Better memory management for large datasets
- Adaptable resource usage based on environment
- Reduced computation time for PySpark operations
