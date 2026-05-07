import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import Home from './pages/Home';
import Clasificacion from './pages/Clasificacion';
import Equipo from './pages/Equipo';
import Jugador from './pages/Jugador';
import Comparador from './pages/Comparador';
import Partido from './pages/Partido';
import Rankings from './pages/Rankings';
import Quintetos from './pages/Quintetos';
import Clutch from './pages/Clutch';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="clasificacion" element={<Clasificacion />} />
            <Route path="equipos" element={<Equipo />} />
            <Route path="jugadores" element={<Jugador />} />
            <Route path="comparador" element={<Comparador />} />
            <Route path="partidos" element={<Partido />} />
            <Route path="rankings" element={<Rankings />} />
            <Route path="quintetos" element={<Quintetos />} />
            <Route path="clutch" element={<Clutch />} />
            <Route path="*" element={
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <p className="text-6xl font-bold text-text-secondary mb-2">404</p>
                <p className="text-lg text-text-secondary mb-6">Página no encontrada</p>
                <Link to="/" className="text-accent hover:text-accent-hover text-sm">← Volver al inicio</Link>
              </div>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
