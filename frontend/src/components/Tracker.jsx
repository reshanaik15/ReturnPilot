const STAGES = ['Requested', 'Initiated', 'In Transit', 'Refunded'];

function stageIndexFor(status) {
  // Backend can only ever hand us "Requested" right now — advancing further needs the
  // dashboard advance-status flow (Task 23a), which doesn't exist yet. Kept generic so
  // this reads correctly once real status values start flowing in.
  const map = {
    Requested: 1,
    initiated: 1,
    Initiated: 1,
    shipped: 2,
    in_transit: 2,
    'In Transit': 2,
    refunded: 3,
    Refunded: 3,
  };
  return map[status] ?? 0;
}

export default function Tracker({ returnItem, onBack }) {
  const activeIndex = stageIndexFor(returnItem.status);

  return (
    <main className="flex-1 overflow-y-auto custom-scrollbar w-full max-w-3xl mx-auto px-4 md:px-10 py-8 md:py-12">
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={onBack}
          className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-low transition-colors text-on-surface-variant"
        >
          <span className="material-symbols-outlined">arrow_back</span>
        </button>
        <div>
          <h1 className="text-headline-md font-headline-md font-extrabold text-primary">Track Return</h1>
          <p className="text-body-sm font-body-sm text-on-surface-variant">
            {returnItem.itemName ?? returnItem.product} | Order #{returnItem.orderId ?? '—'}
          </p>
        </div>
      </div>

      <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 md:p-10 shadow-sm mb-8">
        <h2 className="text-body-lg font-body-lg text-on-surface font-semibold mb-8">Return Status</h2>
        <div className="flex flex-col sm:flex-row justify-between gap-8 sm:gap-0">
          {STAGES.map((stage, i) => {
            const done = i <= activeIndex;
            const current = i === activeIndex;
            return (
              <div key={stage} className="flex flex-row sm:flex-col items-center gap-4 sm:gap-2 w-full sm:w-1/4">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center shadow-sm shrink-0 ${
                    done ? 'bg-primary text-on-primary' : 'bg-surface-container text-outline'
                  }`}
                >
                  <span className="material-symbols-outlined">{done ? 'check' : 'schedule'}</span>
                </div>
                <div className="text-left sm:text-center">
                  <h3
                    className={`text-label-md font-label-md ${current ? 'text-primary font-bold' : 'text-on-surface'}`}
                  >
                    {stage}
                  </h3>
                  <p className="text-label-sm font-label-sm text-on-surface-variant">
                    {done ? returnItem.date : 'Upcoming'}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm">
        <h3 className="text-body-lg font-body-lg text-on-surface font-semibold mb-4 border-b border-surface-container-low pb-2">
          Return Details
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-8">
          <div>
            <p className="text-label-sm font-label-sm text-on-surface-variant">Product</p>
            <p className="text-body-md font-body-md text-on-surface font-medium">
              {returnItem.itemName ?? returnItem.product}
            </p>
          </div>
          <div>
            <p className="text-label-sm font-label-sm text-on-surface-variant">Order ID</p>
            <p className="text-body-md font-body-md text-on-surface font-medium">#{returnItem.orderId ?? '—'}</p>
          </div>
          <div>
            <p className="text-label-sm font-label-sm text-on-surface-variant">Requested On</p>
            <p className="text-body-md font-body-md text-on-surface font-medium">{returnItem.date}</p>
          </div>
          {returnItem.reason && (
            <div className="sm:col-span-2">
              <p className="text-label-sm font-label-sm text-on-surface-variant">Reason</p>
              <p className="text-body-md font-body-md text-on-surface font-medium">{returnItem.reason}</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
