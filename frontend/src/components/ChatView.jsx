import { useEffect, useRef, useState } from 'react';
import MarkdownLite from './MarkdownLite';

const THINKING_STATUSES = [
  'Looking up your orders...',
  'Checking return policy...',
  'Preparing your answer...',
];

export default function ChatView({ messages, onSend, onTrackReturn }) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight });
  }, [messages, loading]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setLoading(true);
    try {
      await onSend(text);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex-1 flex flex-col h-full chat-area-bg min-w-0">
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar scroll-smooth flex flex-col gap-6"
      >
        {messages.map((m, i) => (
          <ChatBubble key={i} message={m} onTrackReturn={onTrackReturn} />
        ))}
        {loading && <TypingBubble />}
      </div>

      <form
        onSubmit={handleSend}
        className="p-4 md:p-6 bg-surface-container-lowest border-t border-outline-variant shadow-[0px_-4px_20px_rgba(0,0,0,0.03)]"
      >
        <div className="max-w-4xl mx-auto relative flex items-center">
          <input
            autoComplete="off"
            className="w-full pl-4 pr-14 py-4 bg-surface rounded-xl border border-outline-variant focus:border-primary focus:ring-4 focus:ring-primary focus:ring-opacity-20 text-body-md font-body-md text-on-surface placeholder:text-on-surface-variant outline-none transition-all shadow-sm"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="absolute right-2 p-2.5 bg-primary text-white rounded-lg hover:bg-[#0052dd] transition-colors shadow-sm flex items-center justify-center disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[20px]">send</span>
          </button>
        </div>
        <div className="text-center mt-3 text-label-sm font-label-sm text-outline">
          AI Return Assistant may produce inaccurate information. Responses can take up to 30 seconds.
        </div>
      </form>
    </main>
  );
}

function ChatBubble({ message, onTrackReturn }) {
  const isUser = message.role === 'user';
  const [visibleSteps, setVisibleSteps] = useState(0);
  const [showMessage, setShowMessage] = useState(isUser);
  const [showCard, setShowCard] = useState(false);

  // Sequenced reveal, matching the real response order: reasoning trace first, then the
  // customer-facing message, then the return-created card. Not real streaming — the whole
  // response already arrived at once — this is purely a staged reveal for readability.
  useEffect(() => {
    if (isUser) return;
    const steps = message.reasoningSteps ?? [];
    let cancelled = false;

    function revealStep(i) {
      if (cancelled) return;
      if (i < steps.length) {
        setVisibleSteps(i + 1);
        setTimeout(() => revealStep(i + 1), 450);
      } else {
        setTimeout(() => {
          if (!cancelled) setShowMessage(true);
        }, steps.length > 0 ? 300 : 0);
      }
    }
    revealStep(0);

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!showMessage || !message.returnEntry) return;
    const timer = setTimeout(() => setShowCard(true), 500);
    return () => clearTimeout(timer);
  }, [showMessage, message.returnEntry]);

  if (isUser) {
    return (
      <div className="flex justify-end w-full">
        <div className="flex gap-4 max-w-[85%] md:max-w-[70%] flex-row-reverse">
          <div className="w-8 h-8 rounded-full bg-surface-container-high flex-shrink-0 flex items-center justify-center text-on-surface-variant mt-1">
            <span className="material-symbols-outlined text-[18px]">person</span>
          </div>
          <div className="bg-primary text-white p-4 rounded-xl rounded-br-none shadow-[0px_4px_20px_rgba(0,0,0,0.05)] text-body-md font-body-md whitespace-pre-wrap">
            {message.text}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4 max-w-[85%] md:max-w-[70%]">
      <div className="w-8 h-8 rounded-full bg-primary flex-shrink-0 flex items-center justify-center text-white mt-1 shadow-sm">
        <span className="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
      <div className="flex flex-col gap-1">
        {message.reasoningSteps?.length > 0 && (
          <div className="reasoning-trace">
            {message.reasoningSteps.slice(0, visibleSteps).map((step, i) => (
              <span className="step" key={i}>
                {step}
              </span>
            ))}
          </div>
        )}
        {showMessage && (
          <div
            className={`p-4 rounded-xl rounded-bl-none shadow-[0px_4px_20px_rgba(0,0,0,0.02)] border text-body-md font-body-md ${
              message.isError
                ? 'bg-error-container text-on-error-container border-error'
                : 'bg-[#F0F7FF] text-on-surface border-primary-fixed border-opacity-50'
            }`}
          >
            <MarkdownLite text={message.text} />
          </div>
        )}
        {showCard && message.returnEntry && (
          <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-5 shadow-[0px_4px_20px_rgba(0,0,0,0.05)] w-full max-w-sm mt-1">
            <div className="flex items-center gap-2 text-primary font-label-md mb-3">
              <span className="material-symbols-outlined text-[20px]">check_circle</span>
              <span className="text-label-md font-label-md">Return Request Created</span>
            </div>
            <div className="space-y-2 mb-4 text-body-sm font-body-sm">
              <div className="flex justify-between border-b border-surface-container-high pb-2">
                <span className="text-on-surface-variant">Product</span>
                <span className="text-on-surface font-medium text-right max-w-[60%]">
                  {message.returnEntry.itemName}
                </span>
              </div>
              <div className="flex justify-between border-b border-surface-container-high pb-2">
                <span className="text-on-surface-variant">Order ID</span>
                <span className="text-on-surface text-label-sm font-label-sm bg-surface-container px-2 py-1 rounded">
                  #{message.returnEntry.orderId}
                </span>
              </div>
              <div className="flex justify-between pt-1">
                <span className="text-on-surface-variant">Status</span>
                <span className="text-primary font-medium">{message.returnEntry.status}</span>
              </div>
            </div>
            <button
              onClick={() => onTrackReturn?.(message.returnEntry)}
              className="w-full py-2.5 bg-primary-fixed text-primary font-label-md rounded-lg hover:bg-primary hover:text-white transition-colors"
            >
              Track Return
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function TypingBubble() {
  const [statusIndex, setStatusIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStatusIndex((i) => (i + 1) % THINKING_STATUSES.length);
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex gap-4 max-w-[85%] md:max-w-[70%]">
      <div className="w-8 h-8 rounded-full bg-primary flex-shrink-0 flex items-center justify-center text-white mt-1 shadow-sm">
        <span className="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
      <div className="flex flex-col gap-1">
        <div className="bg-[#F0F7FF] text-on-surface p-4 rounded-xl rounded-bl-none shadow-[0px_4px_20px_rgba(0,0,0,0.02)] border border-primary-fixed border-opacity-50 flex items-center gap-2 typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <div className="reasoning-trace">
          <span className="step">{THINKING_STATUSES[statusIndex]}</span>
        </div>
      </div>
    </div>
  );
}
