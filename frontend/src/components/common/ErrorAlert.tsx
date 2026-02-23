export default function ErrorAlert({ message }: { message: string }) {
  return (
    <div className="border border-accent-orange bg-accent-orange/10 p-4">
      <p className="text-[11px] uppercase">{message}</p>
    </div>
  );
}
