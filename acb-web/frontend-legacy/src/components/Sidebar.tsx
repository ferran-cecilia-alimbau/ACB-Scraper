import { NavLink } from 'react-router-dom';
import {
  Home, Trophy, Users, User, GitCompare,
  Gamepad2, BarChart3, LayoutGrid, Timer,
  ChevronLeft, ChevronRight,
} from 'lucide-react';
import { SEASON } from '../lib/constants';

const links = [
  { to: '/', icon: Home, label: 'Inicio' },
  { to: '/clasificacion', icon: Trophy, label: 'Clasificación' },
  { to: '/equipos', icon: Users, label: 'Equipos' },
  { to: '/jugadores', icon: User, label: 'Jugadores' },
  { to: '/comparador', icon: GitCompare, label: 'Comparador' },
  { to: '/partidos', icon: Gamepad2, label: 'Partidos' },
  { to: '/rankings', icon: BarChart3, label: 'Rankings' },
  { to: '/quintetos', icon: LayoutGrid, label: 'Quintetos' },
  { to: '/clutch', icon: Timer, label: 'Clutch' },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={`fixed top-0 left-0 z-30 flex h-screen flex-col border-r border-border bg-bg-card transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-56'
      }`}
    >
      {/* Brand */}
      <div className="flex h-14 items-center justify-between px-4 border-b border-border">
        {!collapsed && (
          <span className="text-lg font-bold tracking-tight">
            <span className="text-accent">ACB</span> Stats
          </span>
        )}
        <button
          onClick={onToggle}
          className="rounded p-1 text-text-secondary hover:bg-bg-hover hover:text-text-primary transition-colors"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 mb-0.5 text-sm transition-colors duration-150 ${
                isActive
                  ? 'bg-accent/15 text-accent font-medium'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="border-t border-border px-4 py-3">
          <p className="text-[10px] text-text-secondary">Liga Endesa {SEASON}</p>
        </div>
      )}
    </aside>
  );
}
