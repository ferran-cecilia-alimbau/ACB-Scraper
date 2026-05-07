/**
 * Mapeo y metadatos de equipos ACB.
 * Los nombres canonical largos se usan en perfiles_jugadores.csv;
 * los cortos en estadisticas_partido.csv. Aquí derivamos forma corta canonica,
 * monograma (1-3 letras) y un acento opcional.
 */

interface TeamMeta {
  /** Nombre tal cual viene en estadisticas_partido.csv (forma corta) */
  short: string;
  /** Nombre largo / oficial */
  long: string;
  /** Slug url-safe */
  slug: string;
  /** Monograma 2-3 chars uppercase para tarjetas (fallback sin logo) */
  monogram: string;
  /** Color de marca opcional (referencia, no se usa por defecto) */
  accent?: string;
  /** Ruta al logo en /public/logos/{slug}.png (undefined si no existe) */
  logo?: string;
}

const META: TeamMeta[] = [
  { short: 'Real Madrid', long: 'Real Madrid', slug: 'real-madrid', monogram: 'RMA', accent: '#FFFFFF', logo: '/logos/real-madrid.png' },
  { short: 'Barça', long: 'FC Barcelona', slug: 'barca', monogram: 'BAR', accent: '#A50044', logo: '/logos/barca.png' },
  { short: 'Unicaja', long: 'Unicaja Málaga', slug: 'unicaja', monogram: 'UNI', accent: '#1A8246', logo: '/logos/unicaja.png' },
  { short: 'Valencia Basket', long: 'Valencia Basket', slug: 'valencia', monogram: 'VAL', accent: '#FF6F00', logo: '/logos/valencia.png' },
  { short: 'Baskonia', long: 'Baskonia', slug: 'baskonia', monogram: 'BAS', accent: '#003C82', logo: '/logos/baskonia.png' },
  { short: 'Kosner Baskonia', long: 'Baskonia', slug: 'baskonia', monogram: 'BAS', accent: '#003C82', logo: '/logos/baskonia.png' },
  { short: 'Joventut', long: 'Joventut Badalona', slug: 'joventut', monogram: 'JOV', accent: '#39A335', logo: '/logos/joventut.png' },
  { short: 'Joventut Badalona', long: 'Joventut Badalona', slug: 'joventut', monogram: 'JOV', accent: '#39A335', logo: '/logos/joventut.png' },
  { short: 'Casademont Zgz', long: 'Casademont Zaragoza', slug: 'zaragoza', monogram: 'ZGZ', accent: '#0C2F84', logo: '/logos/zaragoza.png' },
  { short: 'Casademont Zaragoza', long: 'Casademont Zaragoza', slug: 'zaragoza', monogram: 'ZGZ', accent: '#0C2F84', logo: '/logos/zaragoza.png' },
  { short: 'Bàsquet Girona', long: 'Bàsquet Girona', slug: 'girona', monogram: 'GIR', accent: '#D6001C', logo: '/logos/girona.png' },
  { short: 'BAXI Manresa', long: 'BAXI Manresa', slug: 'manresa', monogram: 'MAN', accent: '#5D2382', logo: '/logos/manresa.png' },
  { short: 'Manresa', long: 'BAXI Manresa', slug: 'manresa', monogram: 'MAN', accent: '#5D2382', logo: '/logos/manresa.png' },
  { short: 'Surne Bilbao', long: 'Bilbao Basket', slug: 'bilbao', monogram: 'BIL', accent: '#000000', logo: '/logos/bilbao.png' },
  { short: 'Bilbao Basket', long: 'Bilbao Basket', slug: 'bilbao', monogram: 'BIL', accent: '#000000', logo: '/logos/bilbao.png' },
  { short: 'MoraBanc And', long: 'MoraBanc Andorra', slug: 'andorra', monogram: 'AND', accent: '#FFD200', logo: '/logos/andorra.png' },
  { short: 'MoraBanc Andorra', long: 'MoraBanc Andorra', slug: 'andorra', monogram: 'AND', accent: '#FFD200', logo: '/logos/andorra.png' },
  { short: 'UCAM Murcia', long: 'UCAM Murcia', slug: 'murcia', monogram: 'MUR', accent: '#9F1B32', logo: '/logos/murcia.png' },
  { short: 'Río Breogán', long: 'Río Breogán', slug: 'breogan', monogram: 'BRE', accent: '#D31A1C', logo: '/logos/breogan.png' },
  { short: 'Hiopos Lleida', long: 'Hiopos Lleida', slug: 'lleida', monogram: 'LLE', accent: '#1B4789', logo: '/logos/lleida.png' },
  { short: 'Coviran Granada', long: 'Coviran Granada', slug: 'granada', monogram: 'GRA', accent: '#C8102E', logo: '/logos/granada.png' },
  { short: 'Dreamland GC', long: 'Dreamland Gran Canaria', slug: 'gran-canaria', monogram: 'GC', accent: '#FFCD00', logo: '/logos/gran-canaria.png' },
  { short: 'Dreamland Gran Canaria', long: 'Dreamland Gran Canaria', slug: 'gran-canaria', monogram: 'GC', accent: '#FFCD00', logo: '/logos/gran-canaria.png' },
  { short: 'La Laguna TFE', long: 'La Laguna Tenerife', slug: 'tenerife', monogram: 'TFE', accent: '#005EB8', logo: '/logos/tenerife.png' },
  { short: 'La Laguna Tenerife', long: 'La Laguna Tenerife', slug: 'tenerife', monogram: 'TFE', accent: '#005EB8', logo: '/logos/tenerife.png' },
  { short: 'Recoletas Salud', long: 'Recoletas Salud San Pablo Burgos', slug: 'burgos', monogram: 'BUR', accent: '#0E437C', logo: '/logos/burgos.png' },
  { short: 'Recoletas Salud San Pablo Burgos', long: 'Recoletas Salud San Pablo Burgos', slug: 'burgos', monogram: 'BUR', accent: '#0E437C', logo: '/logos/burgos.png' },
  { short: 'Lenovo Tenerife', long: 'La Laguna Tenerife', slug: 'tenerife', monogram: 'TFE', accent: '#005EB8', logo: '/logos/tenerife.png' },
];

const indexByShort = new Map(META.map((t) => [t.short, t]));

export function teamMeta(name: string | undefined | null): TeamMeta {
  if (!name) {
    return { short: '—', long: '—', slug: 'unknown', monogram: '—' };
  }
  const found = indexByShort.get(name);
  if (found) return found;
  // Fallback: derive monogram from name initials
  const initials = name
    .replace(/[^\p{L}\s]/gu, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 3)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
  return {
    short: name,
    long: name,
    slug: name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, ''),
    monogram: initials || '—',
  };
}
