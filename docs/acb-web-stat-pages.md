# Nuevas Paginas Estadisticas Para ACB Editorial

## Resumen

Este documento define la V2 estadistica de `acb-web`, centrada en jugadores y equipos. La intencion es ampliar la web editorial actual con paginas de datos densos, jerarquia clara, tablas legibles y contexto suficiente para un aficionado avanzado.

La V1 actual ya cubre portada, clasificacion, partidos, jornadas y detalle de partido. La V2 debe anadir navegacion profunda para:

- medias de temporada de jugadores;
- fichas individuales con contexto, splits y game log;
- indice y fichas de equipos;
- hub de rankings de jugadores y equipos.

## Principios De Producto

- Priorizar claridad: cada pagina debe responder a una pregunta principal antes de mostrar tablas largas.
- Evitar rankings enganosos: aplicar filtros visibles de partidos/minutos minimos.
- Dar contexto de liga: siempre que sea util, comparar una metrica contra media ACB o ranking relativo.
- Mantener estetica editorial: tipografia sobria, hairlines, logos/monogramas, tablas densas pero limpias.
- Evitar layouts de dashboard pesado y colecciones de graficos sin lectura.

## Paginas V2

### `/jugadores`

**Objetivo:** descubrir y comparar rendimiento individual de temporada.

**Fuente inicial:** `GET /api/players`.

**Controles:**

- buscador por nombre;
- filtro por equipo;
- filtro por posicion;
- minimo de partidos, default `5`;
- minimo de minutos medios, default `10`;
- selector de vista: `Medias`, `Eficiencia`, `Per 36`, `Totales`.

**Columnas base:**

- jugador, equipo, posicion;
- partidos, titularidades, minutos;
- puntos, rebotes, asistencias, robos, perdidas, tapones, valoracion;
- T2%, T3%, TL%, eFG%, TS%;
- per36 para puntos, rebotes, asistencias, robos, tapones, perdidas y valoracion.

**Interaccion:**

- columnas ordenables;
- click en jugador -> `/jugador/[id]`;
- click en equipo -> `/equipo/[name]`;
- estado vacio claro cuando los filtros no devuelven resultados.

**Notas de implementacion:**

- El backend ya devuelve gran parte de estas columnas.
- Ampliar `GET /api/players` para aceptar `team`, `position`, `min_games`, `min_minutes`, `sort` y `direction`.
- Mantener el filtrado tambien en cliente para busqueda instantanea si el payload no crece demasiado.

### `/jugador/[id]`

**Objetivo:** entender el perfil completo de un jugador y su contexto dentro de la liga.

**Fuente inicial:** `GET /api/players/{id}`.

**Bloques:**

- cabecera: nombre, equipo, posicion, dorsal, altura, edad, nacionalidad;
- resumen de temporada: partidos, titularidades, minutos, puntos, rebotes, asistencias, valoracion;
- eficiencia: T2%, T3%, TL%, eFG%, TS%;
- volumen normalizado: per36;
- ranking relativo: posicion en liga para puntos, rebotes, asistencias y valoracion;
- percentiles: anotacion, creacion, rebote, eficiencia, impacto;
- splits casa/fuera;
- ultimos 5 partidos;
- game log completo.

**Stats recomendadas:**

- `plus_minus_avg`;
- totales de temporada junto a medias;
- forma reciente: medias de los ultimos 5 partidos y diferencia contra media de temporada;
- best game: maxima anotacion, valoracion, rebotes y asistencias.

**Notas de implementacion:**

- El endpoint actual ya devuelve `splits` y `game_log`.
- Anadir al backend `last_5`, `best_games`, `plus_minus_avg` y percentiles.
- En frontend, usar una tabla compacta para game log y tarjetas pequenas solo para stats principales.

### `/equipos`

**Objetivo:** comparar perfiles de equipo de un vistazo.

**Fuente inicial:** `GET /api/teams` + `GET /api/rankings/teams`.

**Controles:**

- selector de vista: `Balance`, `Ataque`, `Defensa`, `Tiro`, `Ritmo`;
- orden por posicion, NetRtg, ORtg, DRtg, pace o diferencial.

**Columnas base:**

- equipo, posicion, balance, partidos;
- puntos a favor, puntos en contra, diferencial;
- ORtg, DRtg, NetRtg, pace;
- rebotes, asistencias, perdidas;
- T2%, T3%, TL%, eFG%, TS%.

**Interaccion:**

- click en equipo -> `/equipo/[name]`;
- destacar top 3 y bottom 3 por metrica seleccionada sin saturar visualmente.

**Notas de implementacion:**

- `GET /api/teams` ahora no devuelve ORtg/DRtg/NetRtg; puede ampliarse o combinarse con `/api/rankings/teams`.
- Usar URL-safe team slugs en frontend si los nombres con espacios/acentos dan problemas.

### `/equipo/[name]`

**Objetivo:** explicar como gana, pierde y evoluciona un equipo.

**Fuente inicial:** `GET /api/teams/{name}`.

**Bloques:**

- cabecera: nombre, posicion, balance, colores/logo;
- resumen: puntos, rebotes, asistencias, perdidas, valoracion;
- ratings: ORtg, DRtg, NetRtg, pace;
- four factors: eFG%, TOV%, OREB%, FT rate;
- forma reciente: ultimos 5 partidos, balance y diferencial;
- splits casa/fuera;
- roster con medias principales;
- resultados/calendario;
- rankings internos: maximos anotadores, reboteadores, asistentes, valoracion.

**Notas de implementacion:**

- Anadir splits casa/fuera de equipo en backend.
- Anadir `last_5` y `internal_rankings`.
- Mantener roster enlazado a `/jugador/[id]`.

### `/rankings`

**Objetivo:** hub de lideres y tablas comparativas.

**Fuentes iniciales:**

- `GET /api/rankings/players`;
- `GET /api/rankings/teams`.

**Tabs jugadores:**

- anotacion: puntos, puntos per36;
- rebote: rebotes totales, ofensivos, defensivos;
- creacion: asistencias, asistencias/perdidas si se anade;
- defensa: robos, tapones;
- eficiencia: valoracion, TS%, eFG%;
- tiro: T2%, T3%, TL%, volumen minimo;
- impacto: plus-minus medio si se anade.

**Tabs equipos:**

- ataque: puntos, ORtg, eFG%, TS%;
- defensa: DRtg, puntos recibidos, rebote defensivo;
- balance: NetRtg, diferencial, victorias;
- ritmo: pace, posesiones estimadas;
- cuidado de balon: perdidas, TOV%;
- rebote: rebotes, OREB%.

**Controles comunes:**

- minimo partidos;
- minimo minutos para jugadores;
- equipo/posicion para jugadores;
- top N: 10, 25, 50.

## Cambios De Backend

### Endpoints A Reutilizar

- `GET /api/players`
- `GET /api/players/{player_id}`
- `GET /api/teams`
- `GET /api/teams/{name}`
- `GET /api/rankings/players`
- `GET /api/rankings/teams`

### Ampliaciones Necesarias

**Jugadores**

- `GET /api/players` debe aceptar filtros reales: `team`, `position`, `min_games`, `min_minutes`, `sort`, `direction`.
- `GET /api/players/{player_id}` debe anadir:
  - `plus_minus_avg`;
  - `totals`;
  - `last_5`;
  - `best_games`;
  - percentiles por categoria;
  - rankings para mas stats, no solo cuatro columnas.

**Equipos**

- `GET /api/teams` debe incluir ratings avanzados o documentar que el frontend combine con `/api/rankings/teams`.
- `GET /api/teams/{name}` debe anadir:
  - splits casa/fuera;
  - forma reciente;
  - four factors agregados;
  - rankings internos de jugadores;
  - comparacion contra media de liga.

**Rankings**

- `GET /api/rankings/players` debe aceptar `stat`, `min_games`, `min_minutes`, `team`, `position`, `limit`.
- `GET /api/rankings/teams` debe aceptar `stat` y `limit`.
- Todos los endpoints deben limpiar `NaN`, `inf` y valores nulos antes de serializar.

### Normalizacion De Equipos

Actualizar el backend de `acb-web` para incluir los mappings recientes:

- `Asisa Joventut` -> `Joventut`
- `ASISA Joventut` -> `Joventut`
- `Surne Bilbao Basket` -> `Surne Bilbao`

Esto evita que clasificaciones, fichas y rankings separen el mismo club en varias filas.

## Tipos Frontend

Anadir en `acb-web/frontend/lib/api.ts` tipos para:

- `PlayerSummary`
- `PlayerDetail`
- `PlayerGameLogRow`
- `TeamSummary`
- `TeamDetail`
- `TeamGameRow`
- `PlayerRankingRow`
- `TeamRankingRow`

Las funciones nuevas deben ser:

- `getPlayers(params?)`
- `getPlayer(id)`
- `getTeams()`
- `getTeam(name)`
- `getPlayerRankings(params?)`
- `getTeamRankings(params?)`

## Componentes Reutilizables

Crear o extender componentes editoriales, no componentes de dashboard generico:

- `StatGrid`: bloque compacto de metricas principales.
- `MetricTable`: tabla ordenable con formato numerico consistente.
- `PlayerLink`: jugador + equipo + posicion.
- `TeamLink`: logo/monograma + nombre.
- `FilterBar`: buscador, selects y minimos.
- `RankingTabs`: tabs sobrias para rankings.
- `RecentFormStrip`: ultimos 5 partidos con W/L y diferencial.

## Reglas De Datos

- Minimos por defecto en rankings de jugadores: `5` partidos y `10` minutos medios.
- Porcentajes de tiro deben ocultarse o atenuarse cuando el volumen sea muy bajo.
- `per36` solo debe mostrarse como complemento, no como ranking principal por defecto.
- Las medias deben redondearse a 1 decimal; porcentajes a 1 decimal; ratings a 1 decimal.
- Los totales pueden mostrarse sin decimales.
- Cualquier ranking debe indicar el filtro activo para evitar interpretaciones falsas.

## Fases Recomendadas

### Fase 1: Jugadores Y Rankings

- `/jugadores`
- `/jugador/[id]`
- `/rankings` con tabs de jugadores
- filtros y tipos frontend

### Fase 2: Equipos

- `/equipos`
- `/equipo/[name]`
- splits casa/fuera y forma reciente
- rankings internos

### Fase 3: Pulido Analitico

- percentiles visuales;
- comparacion contra media de liga;
- best games;
- pequenos graficos editoriales si aportan lectura real.

## Test Plan

### Backend

- Smoke tests de:
  - `/api/players`
  - `/api/players/{id}`
  - `/api/teams`
  - `/api/teams/{name}`
  - `/api/rankings/players`
  - `/api/rankings/teams`
- Verificar que no salen `NaN`, `inf` ni valores no serializables.
- Verificar orden descendente en rankings.
- Verificar que los filtros reducen resultados correctamente.
- Verificar normalizacion de `ASISA Joventut` y `Surne Bilbao Basket`.

### Frontend

- `npm run typecheck`
- `npm run build`
- Smoke visual de:
  - `/jugadores`
  - `/jugador/[id]`
  - `/equipos`
  - `/equipo/[name]`
  - `/rankings`

### Datos

- Comparar conteos principales contra CSVs:
  - numero de jugadores;
  - numero de equipos;
  - partidos por equipo;
  - medias de puntos de jugador/equipo.
- Revisar casos con pocos minutos para asegurar que filtros y atenuaciones funcionan.

## Fuera De Alcance Para Esta V2

- Rehacer la portada.
- Rehacer herramientas internas antiguas de visualizacion.
- PBP avanzado de quintetos, clutch o posesiones como pagina principal.
- Autenticacion, usuarios o favoritos.
- Graficos complejos si no mejoran la lectura editorial.
