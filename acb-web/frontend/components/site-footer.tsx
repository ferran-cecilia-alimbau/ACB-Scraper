export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-[var(--rule)] bg-[var(--bg)]">
      <div className="container-editorial py-12 grid gap-8 sm:grid-cols-3 text-sm text-[var(--ink-muted)]">
        <div>
          <p className="kicker block mb-2">ACB Editorial</p>
          <p className="font-serif text-base text-[var(--ink)] leading-snug">
            Crónica de cifras de la Liga Endesa, sin ruido.
          </p>
        </div>
        <div>
          <p className="kicker block mb-2">Datos</p>
          <p className="leading-relaxed">
            Estadísticas extraídas de la web oficial ACB. Recolección automatizada,
            actualizadas a diario.
          </p>
        </div>
        <div>
          <p className="kicker block mb-2">Año</p>
          <p>{new Date().getFullYear()} · Hecho con respeto al espacio en blanco.</p>
        </div>
      </div>
    </footer>
  );
}
