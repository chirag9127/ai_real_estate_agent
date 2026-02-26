export default function ConfidenceBadge({ score }: { score: number | null }) {
  if (score === null) return null;

  const pct = Math.round(score * 100);
  const color = score >= 0.8 ? '#4f9664' : '#ff5e25';

  return (
    <span
      className="inline-block px-2.5 py-0.5 rounded-full text-[9px] uppercase tracking-[0.5px] font-medium border"
      style={{ borderColor: color, color }}
    >
      {pct}% confidence
    </span>
  );
}
