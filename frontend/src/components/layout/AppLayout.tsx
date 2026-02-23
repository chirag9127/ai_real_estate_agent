import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';

export default function AppLayout() {
  return (
    <div className="grid grid-cols-[260px_1fr] w-full h-screen border border-ink m-3 bg-surface overflow-hidden">
      <Sidebar />
      <main className="flex flex-col overflow-y-auto relative">
        <div className="dot-grid" />
        <Header />
        <div className="flex-1 p-8 z-[1]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
