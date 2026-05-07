import { teamColor } from '../lib/formatters';

interface TeamBadgeProps {
  name: string;
  color: string;
  size?: 'sm' | 'md';
}

export function TeamBadge({ name, color, size = 'sm' }: TeamBadgeProps) {
  const dotSize = size === 'sm' ? 'h-2.5 w-2.5' : 'h-3.5 w-3.5';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm font-medium';

  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`${dotSize} rounded-full inline-block shrink-0`}
        style={{ backgroundColor: teamColor(color) }}
      />
      <span className={textSize}>{name}</span>
    </span>
  );
}
