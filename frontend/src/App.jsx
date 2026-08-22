import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { CustomerProvider, useCustomer } from './context/CustomerContext'
import LoginPage from './pages/LoginPage'
import ChatPage from './pages/ChatPage'
import MyReturnsPage from './pages/MyReturnsPage'
import TrackerPage from './pages/TrackerPage'

function RequireCustomer({ children }) {
  const { customer } = useCustomer()
  if (!customer) return <Navigate to="/login" replace />
  return children
}

function App() {
  return (
    <CustomerProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/chat"
            element={
              <RequireCustomer>
                <ChatPage />
              </RequireCustomer>
            }
          />
          <Route
            path="/returns"
            element={
              <RequireCustomer>
                <MyReturnsPage />
              </RequireCustomer>
            }
          />
          <Route
            path="/returns/:returnId"
            element={
              <RequireCustomer>
                <TrackerPage />
              </RequireCustomer>
            }
          />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </CustomerProvider>
  )
}

export default App
