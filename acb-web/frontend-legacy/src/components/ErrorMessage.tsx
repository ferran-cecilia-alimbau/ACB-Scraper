export function ErrorMessage({ message = 'Error al cargar los datos. Inténtalo de nuevo más tarde.' }: { message?: string }) {
  return (
    <div className="rounded-lg border border-danger/30 bg-danger/5 px-6 py-12 text-center">
      <p className="text-sm text-danger">{message}</p>
    </div>
  );
}
