import Image from 'next/image';
import { cn } from '@/lib/cn';
import { teamMeta } from '@/lib/teams';

interface TeamMonogramProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZE_PX: Record<string, number> = {
  sm: 28,
  md: 36,
  lg: 52,
};

export function TeamMonogram({ name, size = 'md', className }: TeamMonogramProps) {
  const meta = teamMeta(name);
  const px = SIZE_PX[size] ?? 36;

  if (meta.logo) {
    return (
      <span
        className={cn(
          'inline-flex items-center justify-center shrink-0',
          size === 'sm' && 'w-7 h-7',
          size === 'md' && 'w-9 h-9',
          size === 'lg' && 'w-13 h-13',
          className,
        )}
        aria-hidden
      >
        <Image
          src={meta.logo}
          alt={meta.short}
          width={px}
          height={px}
          className="object-contain w-full h-full"
          unoptimized
        />
      </span>
    );
  }

  // Fallback tipográfico si no hay logo
  return (
    <span
      className={cn(
        'team-monogram',
        size === 'sm' && 'team-monogram--sm',
        size === 'lg' && 'team-monogram--lg',
        className,
      )}
      aria-hidden
    >
      {meta.monogram}
    </span>
  );
}
