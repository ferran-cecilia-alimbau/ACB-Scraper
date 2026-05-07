import Link from 'next/link';
import { Kicker } from '@/components/kicker';

export default function NotFound() {
  return (
    <section className="container-editorial py-24 sm:py-32 text-center">
      <Kicker className="block mb-6">404 · No publicado</Kicker>
      <h1 className="headline mb-6 max-w-2xl mx-auto">
        Esta página aún no se ha escrito.
      </h1>
      <p className="lede max-w-lg mx-auto mb-10">
        Quizá un partido sin resultado, una jornada todavía por jugarse, o un enlace
        antiguo. Vuelve a la portada y sigue leyendo.
      </p>
      <Link href="/" className="link-underline text-[var(--accent)] font-medium">
        ← Volver a portada
      </Link>
    </section>
  );
}
