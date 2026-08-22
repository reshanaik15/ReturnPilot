import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// Requested and Initiated always complete together — a Return row in this
// system is created already in status="initiated", there's no separate
// backend timestamp for an earlier "requested but not yet initiated" state.
function stagesFor(status) {
  const base = [
    { key: 'requested', label: 'Requested' },
    { key: 'initiated', label: 'Initiated' },
    { key: 'in_transit', label: 'In Transit' },
    { key: 'refunded', label: 'Refunded' },
  ]
  let completedCount
  let activeIndex = -1
  if (status === 'initiated') {
    completedCount = 1
    activeIndex = 1
  } else if (status === 'shipped') {
    completedCount = 2
    activeIndex = 2
  } else if (status === 'refunded') {
    completedCount = 4
    activeIndex = -1
  } else {
    // declined — halted after Initiated, no further progress implied
    completedCount = 2
    activeIndex = -1
  }
  return base.map((s, i) => ({
    ...s,
    done: i < completedCount || (status === 'refunded' && i === 3),
    active: i === activeIndex,
  }))
}

const STATUS_META = {
  initiated: { label: 'Requested', dateLabel: 'Requested' },
  shipped: { label: 'In Transit', dateLabel: 'In Transit since' },
  refunded: { label: 'Refunded', dateLabel: 'Refunded' },
  declined: { label: 'Declined', dateLabel: 'Declined' },
}

export default function TrackerPage() {
  const { returnId } = useParams()
  const navigate = useNavigate()
  const [ret, setRet] = useState(null)
  const [error, setError] = useState('')
  const [toastVisible, setToastVisible] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .getReturn(returnId)
      .then((data) => {
        if (!cancelled) setRet(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [returnId])

  useEffect(() => {
    if (!ret) return
    const t = setTimeout(() => setToastVisible(false), 5000)
    return () => clearTimeout(t)
  }, [ret])

  if (error) {
    return (
      <div className="bg-background text-on-surface font-sans antialiased min-h-screen flex flex-col items-center justify-center gap-4 p-8">
        <p className="text-body-lg font-body-lg text-error">Couldn't load this return: {error}</p>
        <button
          className="px-6 py-2.5 bg-primary text-on-primary rounded-lg text-label-md font-label-md"
          onClick={() => navigate('/returns')}
        >
          Back to My Returns
        </button>
      </div>
    )
  }

  if (!ret) {
    return (
      <div className="bg-background text-on-surface font-sans antialiased min-h-screen flex items-center justify-center">
        <p className="text-body-md font-body-md text-on-surface-variant">Loading return…</p>
      </div>
    )
  }

  const stages = stagesFor(ret.status)
  const completedForLine = stages.filter((s) => s.done).length
  const lineWidth = Math.min(100, Math.max(0, ((completedForLine - 0.5) / 3) * 100))
  const meta = STATUS_META[ret.status] || STATUS_META.initiated

  return (
    <div className="bg-background text-on-surface font-sans antialiased min-h-screen flex flex-col">
      <header className="bg-surface sticky top-0 z-50 flex justify-between items-center w-full px-margin-desktop h-16 max-w-container-max mx-auto shadow-sm">
        <div className="flex items-center gap-4">
          <button
            className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-low transition-colors text-on-surface-variant"
            onClick={() => navigate('/returns')}
          >
            <span className="material-symbols-outlined">arrow_back</span>
          </button>
          <div>
            <h1 className="text-headline-md font-headline-md font-extrabold text-primary">Track Return</h1>
            <p className="text-body-sm font-body-sm text-on-surface-variant">
              {ret.item_name} | ID: {ret.id}
            </p>
          </div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 flex flex-col gap-8">
        {/* Progress Tracker */}
        <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 md:p-10 shadow-sm relative overflow-hidden">
          <h2 className="text-body-lg font-body-lg text-on-surface font-semibold mb-8">Return Status</h2>
          <div className="relative max-w-3xl mx-auto">
            <div className="absolute top-6 left-6 right-6 h-1 bg-surface-container-high rounded-full -z-10 hidden sm:block"></div>
            <div
              className="absolute top-6 left-6 h-1 bg-primary rounded-full -z-10 hidden sm:block transition-all duration-1000 ease-in-out"
              style={{ width: `${lineWidth}%` }}
            ></div>
            <div className="flex flex-col sm:flex-row justify-between relative z-10 gap-8 sm:gap-0">
              {stages.map((s) => (
                <div key={s.key} className="flex flex-row sm:flex-col items-center gap-4 sm:gap-2 relative group w-full sm:w-1/4">
                  {s.active && (
                    <div className="absolute -inset-2 bg-primary/10 rounded-full animate-pulse blur-xl z-0 pointer-events-none hidden sm:block"></div>
                  )}
                  {s.done ? (
                    <div className="w-12 h-12 rounded-full bg-primary flex items-center justify-center text-on-primary shadow-sm shrink-0">
                      <span className="material-symbols-outlined">check</span>
                    </div>
                  ) : s.active ? (
                    <div className="w-14 h-14 -ml-1 sm:ml-0 rounded-full bg-primary-container border-4 border-surface-container-lowest flex items-center justify-center text-primary shadow-md shrink-0 relative z-10">
                      <span
                        className="material-symbols-outlined text-[28px]"
                        style={{ fontVariationSettings: "'FILL' 1" }}
                      >
                        local_shipping
                      </span>
                    </div>
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-surface-container flex items-center justify-center text-outline shadow-sm shrink-0 border-2 border-surface-container-lowest">
                      <span className="material-symbols-outlined">
                        {s.key === 'refunded' ? 'payments' : 'radio_button_unchecked'}
                      </span>
                    </div>
                  )}
                  <div className="text-left sm:text-center relative z-10">
                    <h3 className={`text-label-md font-label-md ${s.active ? 'text-primary font-bold' : s.done ? 'text-on-surface' : 'text-outline'}`}>
                      {s.label}
                    </h3>
                    <p className={`text-label-sm font-label-sm ${s.active ? 'text-primary' : 'text-outline-variant'}`}>
                      {s.done ? formatDate(s.key === 'requested' || s.key === 'initiated' ? ret.created_at : ret.updated_at) : s.active ? 'In progress' : 'Upcoming'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          {ret.status === 'declined' && (
            <p className="mt-8 text-center text-body-sm font-body-sm text-error">
              This return was declined after review.
            </p>
          )}
        </section>

        {/* Return Details */}
        <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 hover:border-outline transition-colors shadow-sm">
          <h3 className="text-body-lg font-body-lg text-on-surface font-semibold mb-4 border-b border-surface-container-low pb-2">
            Return Details
          </h3>
          <div className="flex flex-col sm:flex-row gap-6">
            <div className="w-full sm:w-32 h-32 rounded-lg overflow-hidden shrink-0 bg-surface-container flex items-center justify-center relative">
              <span className="material-symbols-outlined text-outline text-[48px]">inventory_2</span>
            </div>
            <div className="flex-1 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-8">
                <div>
                  <p className="text-label-sm font-label-sm text-on-surface-variant">Product</p>
                  <p className="text-body-md font-body-md text-on-surface font-medium">{ret.item_name}</p>
                </div>
                <div>
                  <p className="text-label-sm font-label-sm text-on-surface-variant">Return ID</p>
                  <p className="text-body-md font-body-md text-on-surface font-medium">{ret.id}</p>
                </div>
                <div>
                  <p className="text-label-sm font-label-sm text-on-surface-variant">Reason</p>
                  <p className="text-body-md font-body-md text-on-surface font-medium">{ret.reason}</p>
                </div>
                <div>
                  <p className="text-label-sm font-label-sm text-on-surface-variant">Requested On</p>
                  <p className="text-body-md font-body-md text-on-surface font-medium">{formatDate(ret.created_at)}</p>
                </div>
                {ret.price != null && (
                  <div>
                    <p className="text-label-sm font-label-sm text-on-surface-variant">Refund Amount</p>
                    <p className="text-body-md font-body-md text-on-surface font-medium">${ret.price.toFixed(2)}</p>
                  </div>
                )}
                {ret.ai_verdict && (
                  <div>
                    <p className="text-label-sm font-label-sm text-on-surface-variant">Photo Review</p>
                    <p className="text-body-md font-body-md text-on-surface font-medium">
                      {ret.ai_verdict.consistent ? 'Verified' : 'Flagged for review'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>

      {toastVisible && (
        <div className="fixed bottom-margin-desktop left-1/2 transform -translate-x-1/2 bg-inverse-surface text-inverse-on-surface px-6 py-4 rounded-xl shadow-lg flex items-center gap-4 z-[100] transition-all duration-500">
          <span className="material-symbols-outlined text-inverse-primary">info</span>
          <div>
            <p className="text-label-md font-label-md font-bold">Return Status</p>
            <p className="text-body-sm font-body-sm">Current status: {meta.label}</p>
          </div>
          <button className="ml-4 text-outline hover:text-inverse-on-surface transition-colors" onClick={() => setToastVisible(false)}>
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
      )}
    </div>
  )
}
