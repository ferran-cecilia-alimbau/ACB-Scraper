import Link from 'next/link';

const navItems = [
  { href: '/', label: 'Portada' },
  { href: '/clasificacion', label: 'Clasificación' },
  { href: '/partidos', label: 'Partidos' },
];

export function SiteHeader() {
  return (
    <header className="border-b border-[var(--rule)] bg-[var(--bg)]">
      <div className="container-editorial flex items-center justify-between gap-8 py-6">
        <Link href="/" className="block group" aria-label="ACB Editorial — inicio">
          <span className="kicker block">Liga Endesa · 2025-26</span>
          <span className="font-serif text-2xl tracking-tight leading-none mt-1 block">
            ACB <span className="italic text-[var(--accent)]">Editorial</span>
          </span>
        </Link>

        <nav aria-label="Principal" className="hidden sm:flex items-center gap-8">
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

        {/* Mobile: muestra solo enlaces clave en barra inferior */}
        <nav aria-label="Principal móvil" className="sm:hidden flex items-center gap-4 text-sm">
          <Link href="/clasificacion" className="link-underline">
            Tabla
          </Link>
          <Link href="/partidos" className="link-underline">
            Partidos
          </Link>
        </nav>
      </div>
    </header>
  );
}
