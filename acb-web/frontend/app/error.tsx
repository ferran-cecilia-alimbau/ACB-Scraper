'use client';

import Link from 'next/link';
import { Kicker } from '@/components/kicker';

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="container-editorial py-24 sm:py-32 text-center">
      <Kicker className="block mb-6">Error de redacción</Kicker>
      <h1 className="headline mb-6 max-w-2xl mx-auto">
        Algo se ha torcido al imprimir esta página.
      </h1>
      <p className="lede max-w-lg mx-auto mb-10">
        Suele resolverse al reintentar. Si insiste, comprueba que el backend FastAPI
        esté arrancado en el puerto 8000.
      </p>
      <div className="flex items-center justify-center gap-6 text-sm">
        <button
          type="button"
          onClick={reset}
          className="link-underline text-[var(--accent)] font-medium cursor-pointer"
        >
          Reintentar
        </button>
        <Link href="/" className="link-underline text-[var(--ink-muted)]">
          Volver a portada
        </Link>
      </div>
      {error.message && (
        <pre className="mt-12 text-[0.7rem] font-mono text-[var(--ink-muted)] max-w-xl mx-auto overflow-auto whitespace-pre-wrap">
          {error.message}
        </pre>
      )}
    </section>
  );
}
