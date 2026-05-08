# ACB Editorial

Web sobria de la Liga Endesa, en clave editorial. Tipografía cuidada, paleta cálida, datos como protagonistas.

> Proyecto no oficial. No esta afiliado, patrocinado ni aprobado por ACB, Liga Endesa o clubes. Los datos proceden de fuentes publicas y las marcas/logotipos pertenecen a sus propietarios.

## Stack

- **Frontend**: Next.js 15 (App Router) · React 19 · TypeScript estricto · Tailwind v4 · Newsreader / Inter / IBM Plex Mono.
- **Backend**: FastAPI con CSVs en memoria — sin cambios respecto al MVP previo.

```
acb-web/
├── backend/         # FastAPI (no tocar en V1)
├── frontend/        # Next.js — el rediseño editorial
└── frontend-legacy/ # Snapshot del MVP React+Vite anterior (referencia)
```

## Páginas en V1

| Ruta | Contenido |
|---|---|
| `/` | Portada editorial (hero + últimos resultados + top 8 + próxima jornada) |
| `/clasificacion` | Tabla completa |
| `/partidos` | Listado por jornada (todas) |
| `/jornada/[n]` | Slate de la jornada con navegación prev/next |
| `/partido/[id]` | Boxscore íntegro |

## Desarrollo local

```bash
# 1. Backend (FastAPI) — desde la raíz del repo
python -m uvicorn acb-web.backend.main:app --port 8000 --reload

# 2. Frontend (Next.js)
cd acb-web/frontend
npm install   # primera vez
npm run dev   # http://localhost:3000

# Si el backend corre en otro puerto:
BACKEND_URL=http://127.0.0.1:8001 npm run dev
```

El frontend reescribe `/api/*` → `BACKEND_URL` (ver `next.config.mjs`), por lo que no hay CORS en desarrollo.

## Build de producción

```bash
cd acb-web/frontend
npm run build
npm start
```

Las páginas con datos se sirven con `force-dynamic` (server-rendered en cada request, con `revalidate=60`). En el futuro podrían pasar a ISR si el backend está disponible en build time.

## Sistema de diseño

Los tokens viven en `frontend/app/globals.css` como CSS vars y Tailwind v4 `@theme`:

- `--bg`, `--bg-elev`, `--ink`, `--ink-muted`, `--rule`, `--accent` (#E8792B)
- Tema claro por defecto, dark via `prefers-color-scheme: dark`.
- Tres familias tipográficas: Newsreader (display), Inter (body), IBM Plex Mono (numérico).
- Patrones reutilizables: `.kicker`, `.headline`, `.lede`, `.score-xl`, `.score-md`, `.team-monogram`, `.table-editorial`, `.link-underline`, `.container-editorial`.

Sin glass, sin gradientes saturados, sin sombras dramáticas. Todo se construye con hairlines.

## Pendiente (V2+)

- Páginas Equipos, Jugadores, Comparador, Rankings, Quintetos, Clutch.
- Búsqueda global.
- Logos SVG opcionales por equipo.
- Despliegue.
- Eliminar `frontend-legacy/`.
