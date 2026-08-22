import React, { createContext, useContext, useState, useEffect } from 'react'

// The 3 real customers seeded in the backend database. There is no real
// auth system — every backend endpoint just trusts a customer_id, so
// "login" here is really just picking which seeded customer to act as.
export const DEMO_CUSTOMERS = [
  {
    id: '7b1e359b-e01a-5a2d-ae0c-5cb09e4a5e84',
    name: 'Amara Chen',
    email: 'amara@demo.dev',
  },
  {
    id: '8bf621ad-b367-56e5-9442-d1c1039b69f4',
    name: 'Jordan Reyes',
    email: 'jordan@demo.dev',
  },
  {
    id: '7c0028d1-9b02-5498-9b6f-cb94bdb9f0e6',
    name: 'Priya Nair',
    email: 'priya@demo.dev',
  },
]

const CustomerContext = createContext(null)

const STORAGE_KEY = 'returnease_customer_id'

export function CustomerProvider({ children }) {
  const [customer, setCustomerState] = useState(() => {
    const savedId = localStorage.getItem(STORAGE_KEY)
    return DEMO_CUSTOMERS.find((c) => c.id === savedId) || null
  })

  useEffect(() => {
    if (customer) {
      localStorage.setItem(STORAGE_KEY, customer.id)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [customer])

  const setCustomer = (customerId) => {
    const found = DEMO_CUSTOMERS.find((c) => c.id === customerId)
    setCustomerState(found || null)
  }

  const logout = () => setCustomerState(null)

  return (
    <CustomerContext.Provider value={{ customer, setCustomer, logout }}>
      {children}
    </CustomerContext.Provider>
  )
}

export function useCustomer() {
  const ctx = useContext(CustomerContext)
  if (!ctx) throw new Error('useCustomer must be used within a CustomerProvider')
  return ctx
}
