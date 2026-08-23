import Sidebar from './Sidebar';

export default function Layout({ customer, view, onNavigate, onLogout, children }) {
  return (
    <div className="bg-background text-on-background font-body-md h-screen flex flex-col overflow-hidden">
      <header className="sticky top-0 z-50 flex justify-between items-center w-full px-4 md:px-8 h-16 shadow-sm bg-surface shrink-0">
        <div className="text-headline-md font-headline-md font-extrabold text-primary tracking-tight">
          ReturnEase AI
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2 rounded-full hover:bg-surface-container-low transition-all text-on-surface-variant">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button
            onClick={onLogout}
            title={`Log out (${customer.name})`}
            className="p-2 rounded-full hover:bg-surface-container-low transition-all text-on-surface-variant"
          >
            <span className="material-symbols-outlined">account_circle</span>
          </button>
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden w-full relative">
        <Sidebar customer={customer} view={view} onNavigate={onNavigate} />
        {children}
      </div>
    </div>
  );
}
