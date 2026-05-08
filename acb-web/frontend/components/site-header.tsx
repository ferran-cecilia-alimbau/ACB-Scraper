import Link from 'next/link';
import { CommandPalette } from '@/components/command-palette';

const navItems = [
  { href: '/', label: 'Portada' },
  { href: '/clasificacion', label: 'Clasificación' },
  { href: '/jugadores', label: 'Jugadores' },
  { href: '/rankings', label: 'Rankings' },
  { href: '/partidos', label: 'Partidos' },
];

// Equipos con slug — sincronizado con el frontend lib/teams.ts y backend constants.py
const TEAMS = [
  { name: 'Real Madrid', slug: 'real-madrid' },
  { name: 'Barça', slug: 'barca' },
  { name: 'Unicaja', slug: 'unicaja' },
  { name: 'Valencia Basket', slug: 'valencia' },
  { name: 'Baskonia', slug: 'baskonia' },
  { name: 'Joventut', slug: 'joventut' },
  { name: 'Casademont Zgz', slug: 'zaragoza' },
  { name: 'Bàsquet Girona', slug: 'girona' },
  { name: 'BAXI Manresa', slug: 'manresa' },
  { name: 'Surne Bilbao', slug: 'bilbao' },
  { name: 'MoraBanc And', slug: 'andorra' },
  { name: 'UCAM Murcia', slug: 'murcia' },
  { name: 'Río Breogán', slug: 'breogan' },
  { name: 'Hiopos Lleida', slug: 'lleida' },
  { name: 'Coviran Granada', slug: 'granada' },
  { name: 'Dreamland GC', slug: 'gran-canaria' },
  { name: 'La Laguna TFE', slug: 'tenerife' },
  { name: 'Recoletas Salud', slug: 'burgos' },
];

export function SiteHeader() {
  return (
    <header className="border-b border-[var(--rule)] bg-[var(--bg)]">
      <div className="container-editorial flex items-center justify-between gap-6 py-6">
        <Link href="/" className="block group shrink-0" aria-label="ACB Editorial — inicio">
          <span className="kicker block">Liga Endesa · 2025-26</span>
          <span className="font-serif text-2xl tracking-tight leading-none mt-1 block">
            ACB <span className="italic text-[var(--accent)]">Editorial</span>
          </span>
        </Link>

        <nav aria-label="Principal" className="hidden md:flex items-center gap-7">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-[var(--ink)] link-underline"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <CommandPalette teams={TEAMS} />

        {/* Mobile: muestra solo enlaces clave en barra inferior */}
        <nav aria-label="Principal móvil" className="md:hidden flex items-center gap-4 text-sm">
          <Link href="/jugadores" className="link-underline">
            Jugadores
          </Link>
          <Link href="/rankings" className="link-underline">
            Rankings
          </Link>
        </nav>
      </div>
    </header>
  );
}
