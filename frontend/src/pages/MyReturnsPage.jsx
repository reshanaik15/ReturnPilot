import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCustomer } from '../context/CustomerContext'
import api from '../api'

const STATUS_BADGE = {
  initiated: {
    label: 'Requested',
    icon: 'pending',
    classes: 'bg-primary-fixed text-on-primary-fixed',
  },
  shipped: {
    label: 'In Transit',
    icon: 'local_shipping',
    classes: 'bg-[#dbe1ff] text-[#00174c]',
  },
  refunded: {
    label: 'Refunded',
    icon: 'check_circle',
    classes: 'bg-[#dcfce7] text-[#166534]',
  },
  declined: {
    label: 'Declined',
    icon: 'cancel',
    classes: 'bg-error-container text-error',
  },
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function MyReturnsPage() {
  const { customer } = useCustomer()
  const navigate = useNavigate()
  const [returns, setReturns] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    api
      .getCustomerReturns(customer.id)
      .then((data) => {
        if (!cancelled) setReturns(data.returns)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [customer.id])

  return (
    <div className="bg-background text-on-background font-body-md min-h-screen flex flex-col md:flex-row">
      {/* Desktop SideNavBar */}
      <nav className="hidden lg:flex flex-col w-60 fixed h-full py-6 bg-surface-container-lowest border-r border-outline-variant z-40">
        <div className="px-6 mb-8 flex flex-col gap-2">
          <div className="w-12 h-12 rounded-full overflow-hidden bg-surface-container-high mb-2 flex items-center justify-center">
            <span className="material-symbols-outlined text-outline">account_circle</span>
          </div>
          <div>
            <h2 className="text-headline-md font-headline-md font-bold text-primary">Welcome back</h2>
            <p className="text-label-md font-label-md text-on-surface-variant">{customer?.name}</p>
          </div>
        </div>
        <div className="flex-grow flex flex-col gap-1 px-4">
          <a
            className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:bg-surface-container-high rounded-lg mx-2 transition-colors cursor-pointer"
            onClick={() => navigate('/chat')}
          >
            <span className="material-symbols-outlined">forum</span>
            <span className="text-label-md font-label-md">AI Assistant</span>
          </a>
          <a className="flex items-center gap-3 px-4 py-3 bg-primary-container text-on-primary-container font-semibold rounded-lg mx-2 scale-98 transition-all cursor-default">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>assignment_return</span>
            <span className="text-label-md font-label-md">My Returns</span>
          </a>
        </div>
        <div className="px-6 mt-auto">
          <button
            className="w-full bg-primary text-on-primary hover:bg-[#003da9] transition-colors py-3 rounded-lg text-label-md font-label-md flex items-center justify-center gap-2 shadow-sm"
            onClick={() => navigate('/chat')}
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            New Return
          </button>
        </div>
      </nav>

      {/* Mobile TopNavBar */}
      <header className="md:hidden sticky top-0 z-50 flex justify-between items-center w-full px-margin-mobile h-16 shadow-sm bg-surface transition-all">
        <a className="text-headline-lg-mobile font-headline-lg-mobile font-extrabold text-primary">ReturnEase AI</a>
        <div className="flex items-center gap-4">
          <button className="text-on-surface-variant hover:bg-surface-container-low p-2 rounded-full transition-all">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="text-on-surface-variant hover:bg-surface-container-low p-2 rounded-full transition-all">
            <span className="material-symbols-outlined">account_circle</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop lg:pl-[280px] py-8 md:py-12">
        <div className="mb-10">
          <h1 className="text-display-lg font-display-lg text-on-background mb-2">My Returns</h1>
          <p className="text-body-lg font-body-lg text-on-surface-variant">View and track your return requests.</p>
        </div>

        <div className="flex flex-col gap-4">
          {error && (
            <p className="text-body-md font-body-md text-error">Couldn't load your returns: {error}</p>
          )}

          {returns === null && !error && (
            <p className="text-body-md font-body-md text-on-surface-variant">Loading your returns…</p>
          )}

          {returns && returns.length === 0 && (
            <p className="text-body-lg font-body-lg text-on-surface-variant">
              You haven't started any returns yet.
            </p>
          )}

          {returns &&
            returns.map((r) => {
              const badge = STATUS_BADGE[r.status] || STATUS_BADGE.initiated
              const isTerminal = r.status === 'refunded' || r.status === 'declined'
              return (
                <div
                  key={r.id}
                  className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:border-outline transition-colors shadow-[0px_4px_20px_rgba(0,0,0,0.05)] flex flex-col md:flex-row gap-6 md:items-center justify-between"
                >
                  <div className="flex-grow flex flex-col md:flex-row gap-6">
                    <div className="w-16 h-16 rounded-lg bg-surface-container-low flex-shrink-0 flex items-center justify-center border border-outline-variant overflow-hidden">
                      <span className="material-symbols-outlined text-outline text-[28px]">inventory_2</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-3 flex-wrap">
                        <h3 className="text-headline-md font-headline-md text-on-background">{r.item_name}</h3>
                        <span className="px-2 py-1 rounded text-label-sm font-label-sm bg-[#e1e0ff] text-[#07006c]">
                          ID: {r.id}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-body-sm font-body-sm text-on-surface-variant mt-1">
                        <span className="flex items-center gap-1">
                          <span className="material-symbols-outlined text-[16px]">calendar_today</span>
                          {formatDate(r.created_at)}
                        </span>
                        <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-label-sm font-label-sm ${badge.classes}`}>
                          <span className="material-symbols-outlined text-[14px]">{badge.icon}</span>
                          {badge.label}
                        </span>
                      </div>
                      <p className="text-body-sm font-body-sm mt-3 text-on-surface-variant max-w-2xl bg-surface p-3 rounded-lg border border-surface-variant">
                        "{r.reason}"
                      </p>
                    </div>
                  </div>
                  <div className="flex-shrink-0 mt-4 md:mt-0">
                    {isTerminal ? (
                      <button
                        className="w-full md:w-auto px-6 py-2.5 bg-surface-container-low text-on-surface hover:bg-surface-container-highest transition-colors rounded-lg text-label-md font-label-md border border-outline-variant flex items-center justify-center gap-2"
                        onClick={() => navigate(`/returns/${r.id}`)}
                      >
                        View Details
                      </button>
                    ) : (
                      <button
                        className="w-full md:w-auto px-6 py-2.5 bg-secondary-fixed text-on-secondary-fixed hover:bg-secondary-fixed-dim transition-colors rounded-lg text-label-md font-label-md flex items-center justify-center gap-2"
                        onClick={() => navigate(`/returns/${r.id}`)}
                      >
                        Track Return
                        <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
        </div>
      </main>

      {/* Mobile Bottom NavBar */}
      <nav className="md:hidden fixed bottom-0 w-full bg-surface shadow-[0_-4px_20px_rgba(0,0,0,0.05)] border-t border-outline-variant z-50 flex justify-around items-center h-16 pb-safe">
        <a
          className="flex flex-col items-center justify-center w-full h-full text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
          onClick={() => navigate('/chat')}
        >
          <span className="material-symbols-outlined mb-1">forum</span>
          <span className="text-[10px] font-medium">Assistant</span>
        </a>
        <a className="flex flex-col items-center justify-center w-full h-full text-primary font-bold cursor-default">
          <div className="bg-primary-container text-on-primary-container px-4 py-1 rounded-full mb-1">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>assignment_return</span>
          </div>
          <span className="text-[10px] font-medium">Returns</span>
        </a>
      </nav>
    </div>
  )
}
