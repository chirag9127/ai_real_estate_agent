const statusStyles: Record<string, { bg: string; border: string }> = {
  uploaded: { bg: 'transparent', border: '#0d0d0d' },
  extracting: { bg: '#ff5e25', border: '#0d0d0d' },
  extracted: { bg: '#4f9664', border: '#0d0d0d' },
  failed: { bg: '#ff5e25', border: '#ff5e25' },
  pending: { bg: 'transparent', border: '#0d0d0d' },
  active: { bg: '#ff5e25', border: '#0d0d0d' },
  in_progress: { bg: '#ff5e25', border: '#0d0d0d' },
  completed: { bg: '#4f9664', border: '#0d0d0d' },
};

export default function StatusBadge({ status }: { status: string }) {
  const style = statusStyles[status] ?? { bg: 'transparent', border: '#0d0d0d' };
  return (
    <span
      className="inline-block px-2.5 py-0.5 rounded-full text-[9px] uppercase tracking-[0.5px] font-medium border"
      style={{
        background: style.bg,
        borderColor: style.border,
        color: '#0d0d0d',
      }}
    >
      {status.replace('_', ' ')}
    </span>
  );
}
