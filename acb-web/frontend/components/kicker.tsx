import { cn } from '@/lib/cn';

interface KickerProps extends React.HTMLAttributes<HTMLSpanElement> {
  muted?: boolean;
}

export function Kicker({ children, className, muted, ...rest }: KickerProps) {
  return (
    <span
      className={cn('kicker', muted && 'kicker-muted', className)}
      {...rest}
    >
      {children}
    </span>
  );
}
