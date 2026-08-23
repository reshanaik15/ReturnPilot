export default function Sidebar({ customer, view, onNavigate }) {
  return (
    <aside className="hidden lg:flex flex-col w-60 h-full py-6 bg-surface-container-lowest border-r border-outline-variant z-10 shrink-0">
      <div className="px-6 mb-8 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-primary-fixed flex items-center justify-center text-on-primary-fixed font-bold">
          <span className="material-symbols-outlined">person</span>
        </div>
        <div>
          <p className="text-label-sm font-label-sm text-on-surface-variant">Welcome back</p>
          <p className="text-label-md font-label-md font-bold text-on-surface">{customer.name}</p>
        </div>
      </div>
      <nav className="flex flex-col gap-2 px-4 flex-1">
        <button
          onClick={() => onNavigate('chat')}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg mx-2 transition-colors text-left ${
            view === 'chat'
              ? 'bg-primary-container text-on-primary-container font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          <span className="material-symbols-outlined">forum</span>
          <span className="text-label-md font-label-md">AI Assistant</span>
        </button>
        <button
          onClick={() => onNavigate('myReturns')}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg mx-2 transition-colors text-left ${
            view === 'myReturns'
              ? 'bg-primary-container text-on-primary-container font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          <span className="material-symbols-outlined">assignment_return</span>
          <span className="text-label-md font-label-md">My Returns</span>
        </button>
      </nav>
    </aside>
  );
}
