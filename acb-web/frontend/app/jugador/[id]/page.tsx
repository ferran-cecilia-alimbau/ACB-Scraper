import { notFound } from 'next/navigation';
import Link from 'next/link';
import { getPlayer, type PlayerDetail } from '@/lib/api';
import { Kicker } from '@/components/kicker';
import { TeamMonogram } from '@/components/team-monogram';
import { StatGrid } from '@/components/stat-grid';
import { PercentileBar } from '@/components/percentile-bar';
import { teamMeta } from '@/lib/teams';
import { formatDate } from '@/lib/format';
import { GameLogTable } from './game-log-table';

export const revalidate = 60;
export const dynamic = 'force-dynamic';

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const p = await getPlayer(id);
    if ('error' in p) throw new Error('not found');
    const team = teamMeta(p.equipo).short;
    return {
      title: `${p.nombre} — ${team} · ACB Editorial`,
      description: `Estadísticas de ${p.nombre} en la Liga Endesa 2025-26: medias, percentiles, splits casa/fuera, últimos 5 partidos y game log completo.`,
    };
  } catch {
    return { title: 'Jugador · ACB Editorial' };
  }
}

const PERCENTILE_GROUPS: Array<{
  title: string;
  rows: Array<{
    key: keyof PlayerDetail['percentiles'];
    label: string;
    statKey: keyof PlayerDetail['stats'];
    suffix?: string;
    decimals?: number;
  }>;
}> = [
  {
    title: 'Producción',
    rows: [
      { key: 'puntos_avg', label: 'Puntos', statKey: 'puntos_avg', decimals: 1 },
      { key: 'rebotes_avg', label: 'Rebotes', statKey: 'rebotes_avg', decimals: 1 },
      { key: 'asistencias_avg', label: 'Asistencias', statKey: 'asistencias_avg', decimals: 1 },
      { key: 'valoracion_avg', label: 'Valoración', statKey: 'valoracion_avg', decimals: 1 },
    ],
  },
  {
    title: 'Eficiencia y impacto',
    rows: [
      { key: 'ts_pct', label: 'TS%', statKey: 'ts_pct', suffix: '%', decimals: 1 },
      { key: 'efg_pct', label: 'eFG%', statKey: 'efg_pct', suffix: '%', decimals: 1 },
      { key: 'plus_minus_avg', label: '+/-', statKey: 'plus_minus_avg', decimals: 1 },
      { key: 'minutos_avg', label: 'Minutos', statKey: 'minutos_avg', decimals: 1 },
    ],
  },
  {
    title: 'Producción por 36 minutos',
    rows: [
      { key: 'puntos_per36', label: 'Puntos/36', statKey: 'puntos_per36', decimals: 1 },
      { key: 'rebotes_per36', label: 'Rebotes/36', statKey: 'rebotes_per36', decimals: 1 },
      { key: 'asistencias_per36', label: 'Asistencias/36', statKey: 'asistencias_per36', decimals: 1 },
      { key: 'valoracion_per36', label: 'Valoración/36', statKey: 'valoracion_per36', decimals: 1 },
    ],
  },
];

export default async function JugadorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let player!: PlayerDetail;
  try {
    const result = await getPlayer(id);
    if ('error' in result) notFound();
    player = result as PlayerDetail;
  } catch {
    notFound();
  }

  const teamM = teamMeta(player.equipo);
  const s = player.stats;
  const split = (sede: 'Casa' | 'Fuera') => player.splits.find((x) => x.sede === sede);
  const home = split('Casa');
  const away = split('Fuera');
  const hasBestGame = player.best_game && 'puntos' in player.best_game;
  const last5 = player.last_5;

  return (
    <>
      {/* Hero */}
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-12 sm:py-16">
          <div className="flex items-start justify-between flex-wrap gap-6">
            <div className="min-w-0">
              <Kicker className="mb-3 inline-block">
                <Link href={`/jugadores`} className="link-underline">
                  Jugadores
                </Link>
                <span className="mx-2 opacity-50">·</span>
                <span>{player.profile.posicion_full || player.profile.posicion}</span>
              </Kicker>
              <h1 className="font-serif text-5xl sm:text-6xl tracking-tight leading-[0.95] mb-5">
                {player.nombre}
              </h1>
              <div className="flex items-center gap-3 text-sm text-[var(--ink-muted)]">
                <TeamMonogram name={player.equipo} size="md" />
                <Link href={`/jornada/1`} className="link-underline">
                  {teamM.short}
                </Link>
                {player.profile.dorsal ? (
                  <>
                    <span aria-hidden>·</span>
                    <span className="font-mono uppercase tracking-wider">
                      #{player.profile.dorsal}
                    </span>
                  </>
                ) : null}
                {player.profile.altura ? (
                  <>
                    <span aria-hidden>·</span>
                    <span>{player.profile.altura} cm</span>
                  </>
                ) : null}
                {player.profile.edad ? (
                  <>
                    <span aria-hidden>·</span>
                    <span>{player.profile.edad} años</span>
                  </>
                ) : null}
                {player.profile.nacionalidad ? (
                  <>
                    <span aria-hidden>·</span>
                    <span>{player.profile.nacionalidad}</span>
                  </>
                ) : null}
              </div>
            </div>
          </div>

          <StatGrid
            className="mt-10"
            cols={5}
            items={[
              { label: 'Partidos', value: s.partidos, hint: `${s.titularidades} titulares` },
              { label: 'Minutos', value: s.minutos_avg.toFixed(1) },
              { label: 'Puntos', value: s.puntos_avg.toFixed(1) },
              { label: 'Rebotes', value: s.rebotes_avg.toFixed(1) },
              { label: 'Asistencias', value: s.asistencias_avg.toFixed(1) },
              { label: 'Valoración', value: s.valoracion_avg.toFixed(1) },
              { label: 'eFG%', value: `${s.efg_pct.toFixed(1)}%` },
              { label: 'TS%', value: `${s.ts_pct.toFixed(1)}%` },
              { label: 'T3%', value: `${s.t3_pct.toFixed(1)}%` },
              {
                label: '+/-',
                value: s.plus_minus_avg > 0 ? `+${s.plus_minus_avg.toFixed(1)}` : s.plus_minus_avg.toFixed(1),
                tone:
                  s.plus_minus_avg > 0
                    ? 'positive'
                    : s.plus_minus_avg < 0
                      ? 'negative'
                      : 'neutral',
              },
            ]}
          />
        </div>
      </section>

      {/* Percentiles + ranking relativo */}
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-12">
          <Kicker className="mb-2 inline-block">Ranking relativo en la Liga</Kicker>
          <h2 className="font-serif text-3xl mb-1.5">Percentiles</h2>
          <p className="text-sm text-[var(--ink-muted)] mb-8 max-w-xl">
            Comparación contra los jugadores con al menos 5 partidos y 10 minutos por encuentro.
            Cuanto mayor el percentil, mejor el rendimiento relativo.
          </p>
          <div className="grid lg:grid-cols-3 gap-x-12 gap-y-10">
            {PERCENTILE_GROUPS.map((group) => (
              <div key={group.title}>
                <h3 className="kicker mb-5">{group.title}</h3>
                <div className="space-y-5">
                  {group.rows.map((r) => {
                    const pct = player.percentiles[String(r.key)];
                    const rank = player.rankings[String(r.key)];
                    const raw = (s as Record<string, number>)[String(r.statKey)];
                    const valueText = `${raw?.toFixed(r.decimals ?? 1) ?? '—'}${r.suffix ?? ''}`;
                    const rankText =
                      rank?.rank != null ? `${rank.rank}º de ${rank.total}` : undefined;
                    return (
                      <PercentileBar
                        key={String(r.key)}
                        label={r.label}
                        value={valueText}
                        percentile={pct ?? null}
                        rank={rankText}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Splits + Last 5 + Best game */}
      <section className="border-b border-[var(--rule)]">
        <div className="container-editorial py-12 grid gap-12 lg:grid-cols-3">
          <div>
            <Kicker className="mb-2 inline-block">Casa vs Fuera</Kicker>
            <h2 className="font-serif text-2xl mb-6">Splits</h2>
            {home && away ? (
              <div className="grid grid-cols-2 gap-x-6 text-sm">
                <SplitColumn label="Casa" split={home} />
                <SplitColumn label="Fuera" split={away} />
              </div>
            ) : (
              <p className="text-[var(--ink-muted)] italic">Sin datos suficientes.</p>
            )}
          </div>

          <div>
            <Kicker className="mb-2 inline-block">Forma reciente</Kicker>
            <h2 className="font-serif text-2xl mb-6">
              Últimos {last5.games || 5} partidos
            </h2>
            {last5.games > 0 ? (
              <dl className="space-y-3 text-sm">
                <RecentRow
                  label="Puntos"
                  value={last5.stats.puntos.toFixed(1)}
                  diff={last5.diff_vs_season.puntos}
                />
                <RecentRow
                  label="Rebotes"
                  value={last5.stats.rebotes_totales.toFixed(1)}
                  diff={last5.diff_vs_season.rebotes_totales}
                />
                <RecentRow
                  label="Asistencias"
                  value={last5.stats.asistencias.toFixed(1)}
                  diff={last5.diff_vs_season.asistencias}
                />
                <RecentRow
                  label="Valoración"
                  value={last5.stats.valoracion.toFixed(1)}
                  diff={last5.diff_vs_season.valoracion}
                />
                <RecentRow
                  label="Minutos"
                  value={last5.stats.minutos_decimal.toFixed(1)}
                  diff={last5.diff_vs_season.minutos_decimal}
                />
              </dl>
            ) : (
              <p className="text-[var(--ink-muted)] italic">Sin partidos recientes.</p>
            )}
          </div>

          <div>
            <Kicker className="mb-2 inline-block">Mejor partido</Kicker>
            <h2 className="font-serif text-2xl mb-6">Top performance</h2>
            {hasBestGame ? (
              <Link
                href={`/partido/${player.best_game.id_partido}`}
                className="block bg-[var(--bg-elev)] border border-[var(--rule)] p-5 hover:border-[var(--rule-strong)] transition-colors"
              >
                <p className="text-[0.7rem] uppercase tracking-[0.16em] text-[var(--ink-muted)] mb-1">
                  Jornada {player.best_game.jornada_num} · {formatDate(player.best_game.fecha)}
                </p>
                <p className="font-serif text-xl mb-3">vs {teamMeta(player.best_game.rival).short}</p>
                <div className="grid grid-cols-4 gap-x-3 font-mono tabular-nums">
                  <BestStat label="VAL" value={player.best_game.valoracion} accent />
                  <BestStat label="PTS" value={player.best_game.puntos} />
                  <BestStat label="REB" value={player.best_game.rebotes} />
                  <BestStat label="AST" value={player.best_game.asistencias} />
                </div>
              </Link>
            ) : (
              <p className="text-[var(--ink-muted)] italic">Sin datos.</p>
            )}
          </div>
        </div>
      </section>

      {/* Game log */}
      <section>
        <div className="container-editorial py-12">
          <Kicker className="mb-2 inline-block">Game log</Kicker>
          <h2 className="font-serif text-2xl mb-6">Partido a partido</h2>
          <GameLogTable rows={player.game_log} />
        </div>
      </section>
    </>
  );
}

function SplitColumn({
  label,
  split,
}: {
  label: string;
  split: NonNullable<ReturnType<PlayerDetail['splits']['find']>>;
}) {
  return (
    <div>
      <p className="kicker mb-3">
        {label} <span className="text-[var(--ink-muted)] normal-case ml-1">· {split.PJ} PJ</span>
      </p>
      <dl className="space-y-1.5 font-mono tabular-nums text-sm">
        <Row label="MIN" value={split.minutos_decimal.toFixed(1)} />
        <Row label="PTS" value={split.puntos.toFixed(1)} />
        <Row label="REB" value={split.rebotes_totales.toFixed(1)} />
        <Row label="AST" value={split.asistencias.toFixed(1)} />
        <Row label="VAL" value={split.valoracion.toFixed(1)} />
      </dl>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between border-t border-[var(--rule)] pt-1.5 first:border-t-0">
      <dt className="text-[var(--ink-muted)] font-sans uppercase tracking-wider text-[0.7rem]">
        {label}
      </dt>
      <dd>{value}</dd>
    </div>
  );
}

function RecentRow({
  label,
  value,
  diff,
}: {
  label: string;
  value: string | number;
  diff: number;
}) {
  const sign = diff > 0 ? '+' : '';
  const tone =
    diff > 0.1 ? 'text-[var(--positive)]' : diff < -0.1 ? 'text-[var(--negative)]' : 'text-[var(--ink-muted)]';
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-[var(--rule)] pt-2 first:border-t-0 first:pt-0">
      <dt className="text-[var(--ink-muted)] uppercase tracking-wider text-[0.7rem]">{label}</dt>
      <dd className="flex items-baseline gap-3">
        <span className="font-mono tabular-nums">{value}</span>
        <span className={`font-mono tabular-nums text-[0.7rem] ${tone}`}>
          {sign}
          {diff.toFixed(1)}
        </span>
      </dd>
    </div>
  );
}

function BestStat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[0.7rem] uppercase tracking-wider text-[var(--ink-muted)] font-sans">
        {label}
      </span>
      <span className={`text-2xl ${accent ? 'text-[var(--accent)]' : ''}`}>{value}</span>
    </div>
  );
}
