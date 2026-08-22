import { useEffect, useState } from 'react';
import LoginScreen from './components/LoginScreen';
import Layout from './components/Layout';
import ChatView from './components/ChatView';
import MyReturns from './components/MyReturns';
import Tracker from './components/Tracker';
import { sendMessage } from './api';

const STORAGE_KEY = 'returnpilot_customer';

const GREETING = {
  role: 'ai',
  text: "Hi! I'm your AI Return Assistant. I can help you initiate a return, check the status of an existing return, or answer questions about your return.",
  reasoningSteps: [],
};

function App() {
  const [customer, setCustomer] = useState(null);
  const [view, setView] = useState('chat');
  const [messages, setMessages] = useState([GREETING]);
  const [activeReturn, setActiveReturn] = useState(null);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setCustomer(JSON.parse(stored));
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  function handleLogin(c) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
    setCustomer(c);
    setView('chat');
  }

  function handleLogout() {
    localStorage.removeItem(STORAGE_KEY);
    setCustomer(null);
    setMessages([GREETING]);
    setActiveReturn(null);
  }

  async function handleSend(text) {
    setMessages((prev) => [...prev, { role: 'user', text }]);

    try {
      const { customerMessage, reasoningSteps, createdReturn } = await sendMessage(customer.id, text);
      // Matches the [RETURN_CREATED] shape: {return_id, order_id, item_name, status}.
      // Used only for the inline chat card / instant "Track Return" — My Returns itself
      // always re-fetches live from the backend rather than trusting this echoed data.
      const returnEntry = createdReturn
        ? {
            id: createdReturn.return_id,
            orderId: createdReturn.order_id,
            itemName: createdReturn.item_name ?? 'Item',
            status: createdReturn.status ?? 'initiated',
            date: new Date().toISOString().slice(0, 10),
          }
        : null;
      setMessages((prev) => [...prev, { role: 'ai', text: customerMessage, reasoningSteps, returnEntry }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'ai',
          text: `Something went wrong reaching the assistant: ${err.message}. Please try again.`,
          reasoningSteps: [],
          isError: true,
        },
      ]);
    }
  }

  function handleTrackReturn(returnItem) {
    setActiveReturn(returnItem);
    setView('tracker');
  }

  if (!customer) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <Layout customer={customer} view={view} onNavigate={setView} onLogout={handleLogout}>
      <div className={`flex-1 flex flex-col min-w-0 ${view === 'chat' ? '' : 'hidden'}`}>
        <ChatView messages={messages} onSend={handleSend} onTrackReturn={handleTrackReturn} />
      </div>
      {view === 'myReturns' && <MyReturns customer={customer} onTrackReturn={handleTrackReturn} />}
      {view === 'tracker' && activeReturn && (
        <Tracker returnItem={activeReturn} onBack={() => setView('myReturns')} />
      )}
    </Layout>
  );
}

export default App;
