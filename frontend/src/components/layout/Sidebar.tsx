import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

function NavItem({ to, label, end }: { to: string; label: string; end?: boolean }) {
  const [hovered, setHovered] = useState(false);
  const location = useLocation();
  const isActive = end ? location.pathname === to : location.pathname.startsWith(to);
  const show = hovered || isActive;

  return (
    <NavLink
      to={to}
      end={end}
      className="block border-b border-ink no-underline text-ink"
      style={{
        padding: show ? '24px 24px 24px 32px' : '24px',
        background: show ? 'rgba(0,0,0,0.05)' : 'transparent',
        transition: 'background 0.2s, padding-left 0.2s',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="flex justify-between items-center">
        <span className="font-heading text-[28px] uppercase tracking-[0.5px] font-normal">
          {label}
        </span>
        <span
          className="text-[16px] transition-opacity duration-200"
          style={{ opacity: show ? 1 : 0 }}
        >
          {isActive ? '●' : '→'}
        </span>
      </div>
    </NavLink>
  );
}

export default function Sidebar() {
  return (
    <aside className="border-r border-ink flex flex-col bg-surface">
      <div className="p-6 border-b border-ink flex justify-between items-center">
        <div className="font-heading uppercase text-[20px] tracking-[1px]">EstateOS</div>
        <div className="font-heading uppercase text-[20px] tracking-[1px]">V2.0</div>
      </div>

      <nav className="flex flex-col">
        <NavItem to="/" label="Dashboard" end />
        <NavItem to="/upload" label="Upload" />
        <NavItem to="/whatsapp" label="WhatsApp" />
      </nav>

      <div className="mt-auto p-6 border-t border-ink text-[10px] uppercase flex justify-between">
        <span>User: Harry</span>
      </div>
    </aside>
  );
}
