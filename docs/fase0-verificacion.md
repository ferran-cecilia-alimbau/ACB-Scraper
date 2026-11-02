# Fase 0: verificación de la API `api2.acb.com` con tráfico real

Fecha: 2026-11-02. Ejecutada contra la API en vivo desde una sesión con acceso a
`acb.com`, `live.acb.com` y `api2.acb.com`. Las respuestas están guardadas tal cual
en `tests/fixtures/api2/` (44 ficheros, ~2,6 MB).

## Resultado global

**Todas las hipótesis del plan (`docs/plan-scraper-v2.md`) se confirman.** No hay
ninguna corrección de diseño pendiente; solo matices que se anotan abajo.

## 1. Clave `X-APIKEY`

- `https://www.acb.com/` responde 301 a `https://acb.com/es/liga` (hay que seguir
  redirecciones). El HTML no contiene la clave; sí uno de los 32 chunks JS
  (`/_next/static/chunks/39clus-40usgt.js`), con el patrón
  `apiKey:"<uuid>"`. El valor coincide con el documentado en la especificación.
- Sin cabecera: **401**. Con clave: 200.
- `robots.txt`: `User-agent: * / Allow: /` (también lista bots de IA, sin
  `Disallow`). Sitemaps en `acb.com/sitemap.xml`.

## 2. Las 33 rutas

| Resultado | Rutas |
|---|---|
| 200 | las 33, en los ids de referencia (105401 → 2026-27; 17718 → 2016-17; 12559 → 2005-06; ediciones 91, 90, 80, 48; club 2; licencia 20209407) |
| 204 | `Overview/serie` para un partido de liga regular (105401); 200 con la final de 2016-17 (17718) |
| 400 | `competition-data?competitionIds=1,2` (`"The value '1,2' is not valid"`); el parámetro repetido funciona |

Latencia: 0,55–1,3 s por petición. 46 peticiones seguidas a 1 req/s sin ningún
rechazo. Tamaños: play-by-play ~420 KB, calendario ~330 KB, competition-data
~260 KB, box score ~125 KB; el resto < 50 KB.

## 3. Consistencia de datos (partido 105401, Barça 89-86 Valencia Basket)

- Marcador del header = suma de cuartos = `boxscores.total.points` (quarter 0) =
  suma de los totales por cuarto = último `scoreHome/scoreAway` del play-by-play.
- `total` = Σ jugadores + `team` (team = 0 en este partido). 12 jugadores por
  equipo, periodos 0-4, 24 columnas por jugador (las previstas).
- Play-by-play: 735 eventos; 10 filas `599` (quinteto inicial, 5 por equipo);
  109 `112` y 109 `115` (cambios emparejados); 1 `122` y 1 `123`; 40 filas `600`
  (una por minuto, sin jugador, `local=true`): se confirma como marcador de
  minuto y **se debe ignorar**. `playTag` observados: 13, 12, 15, 9 y un `1` sin
  mapear.
- `playerStats` acumulado del último evento de cada jugador coincide con su línea
  del box score en los 24 jugadores.
- Tiros: 188 puntos, 145 de campo = FGA del box score (145). Tiros libres en
  (0,0) con `zone`, `made` y `points` nulos.
- Coordenadas nuevas (mm desde la canasta): distancia mínima de un triple 6.748,
  máxima de un tiro de dos 6.278; `posX` 0–11.001, `posY` −7.204…+7.231. Encaja
  con el arco FIBA (6,75 m) y los laterales (±7,5 m).
- Coordenadas legacy (17718): `posX` 3–95, `posY` 2–98 (porcentaje de pista
  completa), 133 tiros de campo. `zone` legacy presente pero se descarta como
  preveía el plan.
- Overview: `lineup` totales 89/86 con +/-, `lead-tracker` 97 puntos de serie y
  rachas, `match-team-comparison`, `match-leaders`, `match-advanced-stats`
  (pace partido 77,7 vs temporada 73,6, con splits win/loss) y
  `player-advanced-stats` responden con la forma documentada.

## 4. Eras antiguas

- 2005-06 (12559): header con `currentQuarter=0`, `availableContent.playbyplay=false`,
  `advanced=false`; box score completo (22 KB); play-by-play con `plays: []` y
  `matchFinished=false`. Hay que usar `availableContent` para no pedir rutas vacías.
- 1983-84 (`editionId=48`): calendario con 40 jornadas y 260 partidos; ids de
  partido de 4 cifras (p. ej. 4390).

## 5. Entidades

- `player-data` (Tavares): `birthDate` `"22-03-1992"` (DD-MM-YYYY), `height`
  `"2,20"` (string con coma), `playerNumber` 22, `gameRole` `Pívot`, `licensing`
  `JFL`. En `current-roster` la altura es entero en cm (193) y hay `age`,
  `licensing` (`FIBA-E`, `JFL`...) y `nationalityCountry`.
- **Entrenadores:** `player-data?playerLicenceId=20300079` (Pedro Martínez)
  responde 200 con `availableLicenses.coachLicenseData` relleno. Confirmado: la
  misma ruta sirve para fichas de técnico. El staff de `current-roster` trae
  licencia (`CRE`) e id (30005390 Sekulic...).
- `current-roster` con `editionId=80` devuelve la plantilla 2015-16 (16 jugadores).
- `player-stats`: 13 filas temporada×competición×equipo; `career`: etapas
  Herbalife GC 2013-15 y Real Madrid 2017-27 más títulos por competición;
  `matches` (game log 2025-26) y `search` funcionan. `search` devolvió `coaches`
  y `teams` vacíos para "tavares" (esperable).
- `competition-data`: edición actual 91, jornada actual 6020, semana 2992. Liga:
  44 ediciones (48–91); Copa: 43 (48–90). Los nombres que devuelve son los de la
  edición más antigua ("Liga Nacional", "Copa de España").
- Calendario 2026-27: 34 jornadas, 306 partidos, 18 equipos; 54 `FINALIZED`,
  243 `NOT_STARTED`, 9 `NOT_SCHEDULED`. Clasificación con historial jornada a
  jornada por equipo. Bracket 2025-26 con `quarterFinals`, `semifinals`, `final`,
  `otherPositions`.

## 6. Ajustes al plan derivados de la verificación

1. El descubridor de clave debe seguir redirecciones y recorrer los chunks JS;
   el HTML de la portada no basta.
2. Filtrar `playType == 600` al cargar el play-by-play (o guardarlo en una tabla
   aparte de marcadores de minuto).
3. Añadir `playTag == 1` al catálogo como "desconocido".
4. Las fichas de entrenador se obtienen con `PlayerProfile/player-data` usando
   la licencia del staff; no hace falta parsear `/es/liga/entrenadores/...`.
5. Para ediciones ≤ 2019-20, consultar `availableContent` del header antes de
   pedir play-by-play, tiros, overview y avanzadas.

Nada de lo anterior cambia la arquitectura ni el modelo de datos propuestos.
