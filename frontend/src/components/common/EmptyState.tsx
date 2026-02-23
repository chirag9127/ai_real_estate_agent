export default function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="text-center py-12 border border-ink/20">
      <h3 className="font-heading text-[20px] uppercase">{title}</h3>
      <p className="mt-2 text-[11px] uppercase opacity-50">{description}</p>
    </div>
  );
}
