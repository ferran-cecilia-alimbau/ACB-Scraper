import { Kicker } from '@/components/kicker';

export default function Loading() {
  return (
    <section className="container-editorial py-24">
      <Kicker className="block mb-6 animate-pulse">Cargando edición</Kicker>
      <div className="space-y-4 max-w-3xl">
        <div className="h-12 bg-[var(--rule)] animate-pulse" />
        <div className="h-12 w-3/4 bg-[var(--rule)] animate-pulse" />
        <div className="h-6 w-2/3 bg-[var(--rule)] animate-pulse mt-8" />
        <div className="h-6 w-1/2 bg-[var(--rule)] animate-pulse" />
      </div>
    </section>
  );
}
