import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useCustomer } from '../context/CustomerContext'
import api from '../api'

const MARKDOWN_COMPONENTS = {
  p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
  strong: ({ node, ...props }) => <strong className="font-semibold text-on-surface" {...props} />,
  ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-2 space-y-1" {...props} />,
  ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-2 space-y-1" {...props} />,
  a: ({ node, ...props }) => <a className="text-primary underline" {...props} />,
  table: ({ node, ...props }) => (
    <div className="overflow-x-auto my-2">
      <table className="w-full text-left border-collapse text-body-sm font-body-sm" {...props} />
    </div>
  ),
  thead: ({ node, ...props }) => <thead className="border-b border-outline-variant" {...props} />,
  th: ({ node, ...props }) => <th className="py-1.5 pr-4 font-label-md font-label-md text-on-surface-variant" {...props} />,
  td: ({ node, ...props }) => <td className="py-1.5 pr-4 border-b border-surface-container-high" {...props} />,
}

function MarkdownText({ text }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
      {text}
    </ReactMarkdown>
  )
}

function extractReturnCard(result) {
  if (!result.return_initiated) return null
  const step = (result.reasoning_trace || []).find(
    (s) => s.tool === 'initiate_return' && s.result && s.result.success
  )
  if (!step) return null
  return {
    returnId: step.result.return_id,
    itemName: step.result.item_name,
    price: step.result.price,
    reason: step.input && step.input.reason,
    labelReference: step.result.label_reference,
  }
}

let msgCounter = 0
const nextId = () => `m${++msgCounter}`

export default function ChatPage() {
  const { customer } = useCustomer()
  const navigate = useNavigate()

  const [messages, setMessages] = useState(() => [
    {
      id: nextId(),
      role: 'ai',
      text: "Hi! I'm your AI Return Assistant. I can help you initiate a return, check the status of an existing return, or answer questions about your return.",
      showChips: true,
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const conversationHistoryRef = useRef([])
  const lastReturnRef = useRef(null) // { returnId, reason } — most recent return created in this chat
  const fileInputRef = useRef(null)
  const chatContainerRef = useRef(null)

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages, loading])

  const appendMessage = (msg) => setMessages((prev) => [...prev, { id: nextId(), ...msg }])

  const sendToAgent = async (text, imageBase64 = null) => {
    appendMessage({ role: 'user', text })
    setLoading(true)
    try {
      const result = await api.sendMessage(
        customer.id,
        text,
        imageBase64,
        conversationHistoryRef.current
      )
      conversationHistoryRef.current = [
        ...conversationHistoryRef.current,
        { role: 'user', content: [{ type: 'text', text }] },
        { role: 'assistant', content: [{ type: 'text', text: result.response }] },
      ]
      const returnCard = extractReturnCard(result)
      if (returnCard) {
        lastReturnRef.current = { returnId: returnCard.returnId, reason: returnCard.reason }
      }
      appendMessage({ role: 'ai', text: result.response, returnCard })
    } catch (err) {
      appendMessage({
        role: 'ai',
        text: `Sorry, something went wrong reaching the assistant: ${err.message}`,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSend = () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    sendToAgent(text)
  }

  const handleChip = (text) => {
    if (loading) return
    sendToAgent(text)
  }

  const handleAttachClick = () => {
    if (loading) return
    if (!lastReturnRef.current) {
      appendMessage({
        role: 'ai',
        text: 'Please start a return first — once a return exists, I can attach a photo as evidence for it.',
      })
      return
    }
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    const { returnId, reason } = lastReturnRef.current
    appendMessage({ role: 'user', text: `📎 Attached photo for ${returnId}` })
    setLoading(true)
    try {
      const outcome = await api.verifyPhoto(returnId, reason || 'Photo evidence for return', file)
      const verdict = outcome.ai_verdict || {}
      const routingText =
        outcome.routing === 'fast_track'
          ? "Great news — this has been fast-tracked, no manual review needed."
          : outcome.routing === 'human_review'
          ? "This has been flagged for manual review by our team."
          : 'This will go through standard processing.'
      appendMessage({
        role: 'ai',
        text: `I've reviewed the photo for ${returnId}. ${verdict.notes || ''} ${routingText}`,
      })
    } catch (err) {
      appendMessage({ role: 'ai', text: `Photo verification failed: ${err.message}` })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-background text-on-background font-body-md h-screen flex flex-col overflow-hidden">
      {/* TopNavBar */}
      <header className="sticky top-0 z-50 flex justify-between items-center w-full px-margin-desktop h-16 max-w-container-max mx-auto shadow-sm bg-surface text-primary">
        <div className="text-headline-md font-headline-md font-extrabold text-primary tracking-tight">
          ReturnEase AI
        </div>
        <nav className="hidden md:flex items-center gap-8 h-full">
          <a className="h-full flex items-center text-primary font-bold border-b-2 border-primary pb-1 opacity-80 scale-95 transition-transform text-label-md font-label-md cursor-default">
            AI Chat
          </a>
          <a
            className="h-full flex items-center text-on-surface-variant hover:text-primary transition-colors hover:bg-surface-container-low text-label-md font-label-md cursor-pointer"
            onClick={() => navigate('/returns')}
          >
            My Returns
          </a>
        </nav>
        <div className="flex items-center gap-4">
          <button className="p-2 rounded-full hover:bg-surface-container-low transition-all text-on-surface-variant">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="p-2 rounded-full hover:bg-surface-container-low transition-all text-on-surface-variant">
            <span className="material-symbols-outlined">account_circle</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden max-w-container-max w-full mx-auto relative">
        {/* SideNavBar */}
        <aside className="hidden lg:flex flex-col w-60 h-full py-6 bg-surface-container-lowest border-r border-outline-variant z-10 text-primary">
          <div className="px-6 mb-8 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary-fixed flex items-center justify-center text-on-primary-fixed font-bold">
              <span className="material-symbols-outlined">person</span>
            </div>
            <div>
              <p className="text-label-sm font-label-sm text-on-surface-variant">Welcome back</p>
              <p className="text-label-md font-label-md font-bold text-on-surface">{customer?.name}</p>
            </div>
          </div>
          <nav className="flex flex-col gap-2 px-4 flex-1">
            <a className="flex items-center gap-3 px-4 py-3 bg-primary-container text-on-primary-container font-semibold rounded-lg mx-2 scale-98 transition-all cursor-default">
              <span className="material-symbols-outlined">forum</span>
              <span className="text-label-md font-label-md">AI Assistant</span>
            </a>
            <a
              className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:bg-surface-container-high rounded-lg mx-2 transition-colors cursor-pointer"
              onClick={() => navigate('/returns')}
            >
              <span className="material-symbols-outlined">assignment_return</span>
              <span className="text-label-md font-label-md">My Returns</span>
            </a>
          </nav>
          <div className="px-6 mt-auto">
            <button
              className="w-full py-3 px-4 bg-primary text-on-primary rounded-lg font-label-md hover:bg-surface-tint transition-colors flex items-center justify-center gap-2 shadow-sm"
              onClick={() => handleChip("I'd like to start a return")}
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              New Return
            </button>
          </div>
        </aside>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col relative chat-area-bg h-full">
          <div className="md:hidden flex items-center justify-between p-4 border-b border-outline-variant bg-surface">
            <span className="text-headline-lg-mobile font-headline-lg-mobile font-bold">AI Chat</span>
            <button className="p-2 text-on-surface-variant" onClick={() => navigate('/returns')}>
              <span className="material-symbols-outlined">menu</span>
            </button>
          </div>

          <div
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar scroll-smooth flex flex-col gap-6"
          >
            {messages.map((m) =>
              m.role === 'ai' ? (
                <div key={m.id} className="flex gap-4 max-w-[95%] md:max-w-[85%]">
                  <div className="w-8 h-8 rounded-full bg-primary flex-shrink-0 flex items-center justify-center text-white mt-1 shadow-sm">
                    <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                  </div>
                  <div className="flex flex-col gap-3 w-full">
                    <div className="bg-[#F0F7FF] text-on-surface p-4 rounded-xl rounded-bl-none shadow-[0px_4px_20px_rgba(0,0,0,0.02)] border border-primary-fixed border-opacity-50 text-body-md font-body-md self-start">
                      <MarkdownText text={m.text} />
                    </div>

                    {m.showChips && (
                      <div className="flex flex-wrap gap-2 mt-1">
                        <button
                          className="px-4 py-2 rounded-full border border-outline-variant text-on-surface-variant text-label-sm font-label-sm hover:bg-surface-container-low hover:text-primary hover:border-primary transition-colors flex items-center gap-1 bg-surface-container-lowest"
                          onClick={() => handleChip("I'd like to start a return")}
                        >
                          <span className="material-symbols-outlined text-[14px]">replay</span>
                          Start a Return
                        </button>
                        <button
                          className="px-4 py-2 rounded-full border border-outline-variant text-on-surface-variant text-label-sm font-label-sm hover:bg-surface-container-low hover:text-primary hover:border-primary transition-colors flex items-center gap-1 bg-surface-container-lowest"
                          onClick={() => handleChip('Can you check the status of my return?')}
                        >
                          <span className="material-symbols-outlined text-[14px]">local_shipping</span>
                          Track My Return
                        </button>
                        <button
                          className="px-4 py-2 rounded-full border border-outline-variant text-on-surface-variant text-label-sm font-label-sm hover:bg-surface-container-low hover:text-primary hover:border-primary transition-colors flex items-center gap-1 bg-surface-container-lowest"
                          onClick={() => handleChip("What's your return policy?")}
                        >
                          <span className="material-symbols-outlined text-[14px]">help</span>
                          Return Help
                        </button>
                      </div>
                    )}

                    {m.returnCard && (
                      <div className="bg-surface-container-lowest border border-outline-variant hover:border-[#D1D5DB] rounded-[16px] p-6 shadow-[0px_4px_20px_rgba(0,0,0,0.05)] w-full max-w-md transition-colors">
                        <div className="flex items-center gap-2 text-primary font-label-md mb-4">
                          <span className="material-symbols-outlined text-[20px] text-primary">check_circle</span>
                          <span className="text-label-md font-label-md">Return Request Created</span>
                        </div>
                        <div className="space-y-3 mb-6">
                          <div className="flex justify-between items-start border-b border-surface-container-high pb-3">
                            <span className="text-on-surface-variant text-body-sm font-body-sm">Product</span>
                            <span className="text-on-surface text-body-sm font-body-sm font-medium text-right max-w-[60%]">
                              {m.returnCard.itemName}
                            </span>
                          </div>
                          <div className="flex justify-between items-center border-b border-surface-container-high pb-3">
                            <span className="text-on-surface-variant text-body-sm font-body-sm">Reason</span>
                            <span className="text-on-surface text-body-sm font-body-sm">{m.returnCard.reason || '—'}</span>
                          </div>
                          <div className="flex justify-between items-center border-b border-surface-container-high pb-3">
                            <span className="text-on-surface-variant text-body-sm font-body-sm">ID</span>
                            <span className="text-on-surface text-label-sm font-label-sm bg-surface-container px-2 py-1 rounded">
                              {m.returnCard.returnId}
                            </span>
                          </div>
                          <div className="flex justify-between items-center pt-1">
                            <span className="text-on-surface-variant text-body-sm font-body-sm">Status</span>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-label-sm font-label-sm bg-[rgba(15,98,254,0.1)] text-primary">
                              Requested
                            </span>
                          </div>
                        </div>
                        <button
                          className="w-full py-2.5 bg-primary-fixed text-primary font-label-md rounded-lg hover:bg-primary hover:text-white transition-colors"
                          onClick={() => navigate(`/returns/${m.returnCard.returnId}`)}
                        >
                          Track Return
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div key={m.id} className="flex justify-end w-full">
                  <div className="flex gap-4 max-w-[85%] md:max-w-[70%] flex-row-reverse">
                    <div className="w-8 h-8 rounded-full bg-surface-container-high flex-shrink-0 flex items-center justify-center text-on-surface-variant mt-1">
                      <span className="material-symbols-outlined text-[18px]">person</span>
                    </div>
                    <div className="bg-primary text-white p-4 rounded-xl rounded-br-none shadow-[0px_4px_20px_rgba(0,0,0,0.05)] text-body-md font-body-md">
                      {m.text}
                    </div>
                  </div>
                </div>
              )
            )}

            {loading && (
              <div className="flex gap-4 max-w-[70%]">
                <div className="w-8 h-8 rounded-full bg-primary flex-shrink-0 flex items-center justify-center text-white mt-1 shadow-sm">
                  <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                </div>
                <div className="bg-[#F0F7FF] text-on-surface p-4 rounded-xl rounded-bl-none shadow-[0px_4px_20px_rgba(0,0,0,0.02)] border border-primary-fixed border-opacity-50 flex items-center">
                  <span className="typing-indicator">
                    <span></span><span></span><span></span>
                  </span>
                </div>
              </div>
            )}

            <div className="h-4"></div>
          </div>

          {/* Sticky Chat Input Area */}
          <div className="p-4 md:p-6 bg-surface-container-lowest border-t border-outline-variant bg-opacity-95 backdrop-blur-sm z-20 shadow-[0px_-4px_20px_rgba(0,0,0,0.03)]">
            <div className="max-w-4xl mx-auto relative flex items-center">
              <button
                className="absolute left-3 text-on-surface-variant hover:text-primary transition-colors p-2 rounded-full hover:bg-surface-container-low"
                onClick={handleAttachClick}
                type="button"
              >
                <span className="material-symbols-outlined">attach_file</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileSelected}
              />
              <input
                autoComplete="off"
                className="w-full pl-12 pr-14 py-4 bg-surface rounded-xl border border-outline-variant focus:border-primary focus:ring-4 focus:ring-primary focus:ring-opacity-20 text-body-md font-body-md text-on-surface placeholder:text-on-surface-variant outline-none transition-all shadow-sm"
                placeholder="Type your message..."
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSend()
                }}
              />
              <button
                className="absolute right-2 p-2.5 bg-primary text-white rounded-lg hover:bg-surface-tint transition-colors shadow-sm flex items-center justify-center disabled:opacity-50"
                onClick={handleSend}
                disabled={loading || !input.trim()}
                type="button"
              >
                <span className="material-symbols-outlined text-[20px]">send</span>
              </button>
            </div>
            <div className="text-center mt-3 text-label-sm font-label-sm text-outline">
              AI Return Assistant may produce inaccurate information.
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
