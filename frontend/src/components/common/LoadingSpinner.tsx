export default function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="h-6 w-6 animate-spin border-2 border-ink border-t-transparent" />
      <p className="mt-3 text-[10px] uppercase tracking-[1px] opacity-50">{message}</p>
    </div>
  );
}
