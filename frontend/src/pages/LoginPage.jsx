import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCustomer, DEMO_CUSTOMERS } from '../context/CustomerContext'

export default function LoginPage() {
  const { setCustomer } = useCustomer()
  const navigate = useNavigate()
  const [selected, setSelected] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!selected) {
      setError('Select your account to continue.')
      return
    }
    setCustomer(selected)
    navigate('/chat')
  }

  return (
    <div className="h-full min-h-screen flex items-center justify-center bg-surface font-body-md text-body-md text-on-surface antialiased p-margin-mobile md:p-margin-desktop">
      <main className="w-full max-w-md">
        <div className="bg-surface-container-lowest rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] border border-outline-variant p-8 md:p-12 text-center">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-primary-container rounded-full flex items-center justify-center shadow-[0_12px_32px_rgba(0,0,0,0.10)]">
              <span
                className="material-symbols-outlined text-[32px] text-on-primary-container"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                assignment_return
              </span>
            </div>
          </div>

          <h1 className="text-headline-lg font-headline-lg text-primary mb-2">ReturnPilot</h1>
          <p className="text-body-md font-body-md text-on-surface-variant mb-8">
            Your AI-powered assistant for fast and easy product returns.
          </p>

          <form className="space-y-6 text-left" onSubmit={handleSubmit}>
            <div>
              <label className="block text-label-md font-label-md text-on-surface mb-2" htmlFor="account">
                Select your account to continue
              </label>
              <div className="relative">
                <select
                  className="block w-full appearance-none rounded-lg border border-outline-variant bg-surface-container-lowest py-3 pl-4 pr-10 text-body-md font-body-md text-on-surface focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/20 hover:border-outline transition-colors cursor-pointer"
                  id="account"
                  name="account"
                  value={selected}
                  onChange={(e) => {
                    setSelected(e.target.value)
                    setError('')
                  }}
                >
                  <option disabled value="">Choose an account</option>
                  {DEMO_CUSTOMERS.map((c) => (
                    <option key={c.id} value={c.id}>{c.email}</option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                  <span className="material-symbols-outlined text-outline">expand_more</span>
                </div>
              </div>
              <p className="mt-2 text-body-sm font-body-sm text-on-surface-variant">
                {error || 'Select your account to continue.'}
              </p>
            </div>

            <button
              className="w-full flex justify-center rounded-lg bg-primary py-3 px-4 text-label-md font-label-md text-on-primary hover:bg-[#003da9] focus:outline-none focus:ring-4 focus:ring-primary/20 transition-colors shadow-sm"
              type="submit"
            >
              Continue
            </button>
          </form>
        </div>

        <div className="mt-8 text-center">
          <p className="text-label-sm font-label-sm text-on-surface-variant">
            Secure, AI-driven return processing.
          </p>
        </div>
      </main>
    </div>
  )
}
