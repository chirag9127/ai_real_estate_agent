import { useLocation } from 'react-router-dom';

const routeTitles: Record<string, string> = {
  '/': 'Overview',
  '/upload': 'Upload Transcript',
};

export default function Header() {
  const location = useLocation();
  let title = routeTitles[location.pathname] ?? 'EstateOS';
  if (/^\/pipeline\/\d+$/.exec(location.pathname)) {
    title = 'Pipeline Detail';
  } else if (/^\/pipeline\/\d+\//.exec(location.pathname)) {
    title = 'Pipeline';
  }

  return (
    <header className="px-8 py-6 border-b border-ink flex justify-between items-center bg-surface z-[1]">
      <div className="font-heading uppercase text-[14px] tracking-[1px] flex items-center gap-2">
        <span>→</span>
        <span>{title}</span>
      </div>
      <div className="flex gap-6 items-center">
        <span className="text-[11px] uppercase">AI Real Estate Assistant</span>
      </div>
    </header>
  );
}
