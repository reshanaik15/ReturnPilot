import { useEffect, useState } from 'react';
import { getMyReturns } from '../api';

const STATUS_DISPLAY = {
  initiated: { label: 'Initiated', statusClass: 'bg-[#dbe1ff] text-[#00174c]', icon: 'assignment_turned_in' },
  shipped: { label: 'In Transit', statusClass: 'bg-primary-fixed text-on-primary-fixed', icon: 'local_shipping' },
  in_transit: { label: 'In Transit', statusClass: 'bg-primary-fixed text-on-primary-fixed', icon: 'local_shipping' },
  refunded: { label: 'Refunded', statusClass: 'bg-[#dcfce7] text-[#166534]', icon: 'check_circle' },
};

export default function MyReturns({ customer, onTrackReturn }) {
  const [returns, setReturns] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setReturns(null);
    setError(null);
    getMyReturns(customer.name)
      .then((data) => {
        if (!cancelled) setReturns(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [customer.name]);

  return (
    <main className="flex-1 overflow-y-auto custom-scrollbar w-full max-w-3xl mx-auto px-4 md:px-10 py-8 md:py-12">
      <div className="mb-8">
        <h1 className="text-display-lg font-display-lg text-on-background mb-2">My Returns</h1>
        <p className="text-body-lg font-body-lg text-on-surface-variant">View and track your return requests.</p>
      </div>

      {returns === null && !error && (
        <div className="text-center text-body-md font-body-md text-on-surface-variant py-12">Loading…</div>
      )}

      {error && (
        <div className="bg-error-container text-on-error-container rounded-xl p-6 text-body-md font-body-md">
          Couldn't load your returns: {error}
        </div>
      )}

      {returns && returns.length === 0 && (
        <div className="text-center text-body-md font-body-md text-on-surface-variant py-12">
          No returns yet — start one in AI Chat.
        </div>
      )}

      {returns && returns.length > 0 && (
        <div className="flex flex-col gap-4">
          {returns.map((r) => {
            const display = STATUS_DISPLAY[r.status] ?? {
              label: r.status,
              statusClass: 'bg-primary-fixed text-on-primary-fixed',
              icon: 'pending',
            };
            return (
              <div
                key={r.rowid}
                className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:border-outline transition-colors shadow-[0px_4px_20px_rgba(0,0,0,0.05)] flex flex-col md:flex-row gap-6 md:items-center justify-between"
              >
                <div className="flex-grow flex flex-col gap-1">
                  <div className="flex items-center gap-3 flex-wrap">
                    <h3 className="text-headline-md font-headline-md font-bold text-on-background">{r.itemName}</h3>
                    <span className="px-2 py-1 rounded text-label-sm font-label-sm bg-[#e1e0ff] text-[#07006c]">
                      Order #{r.orderId}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-body-sm font-body-sm text-on-surface-variant mt-1">
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[16px]">calendar_today</span>
                      {r.date}
                    </span>
                    <span
                      className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-label-sm font-label-sm font-bold ${display.statusClass}`}
                    >
                      <span className="material-symbols-outlined text-[14px]">{display.icon}</span>
                      {display.label}
                    </span>
                  </div>
                  <p className="text-body-sm font-body-sm mt-3 text-on-surface-variant max-w-2xl bg-surface p-3 rounded-lg border border-surface-variant">
                    {r.reason}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <button
                    onClick={() => onTrackReturn?.(r)}
                    className="w-full md:w-auto px-6 py-2.5 bg-secondary-fixed text-on-secondary-fixed hover:bg-secondary-fixed-dim transition-colors rounded-lg text-label-md font-label-md flex items-center justify-center gap-2"
                  >
                    Track Return
                    <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
