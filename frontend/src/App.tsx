import { useState, useEffect, useRef, useCallback } from 'react';
import { useWebSocket, WSEvent } from './hooks/useWebSocket';
import ChatPanel from './components/ChatPanel';
import AgentDebugPanel from './components/AgentDebugPanel';
import CustomerSelector from './components/CustomerSelector';
import QGPUMonitor from './components/QGPUMonitor';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
  model?: string;
  image?: string;
  timestamp: number;
}

interface Customer {
  customer_id: string;
  name: string;
  language: string;
  is_premium: boolean;
}

interface Scenario {
  id: number;
  name: string;
  message: string;
  messages?: string[];
  customer_id: string;
  image?: boolean;
  description: string;
}

const BACKEND_URL = '/api';
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [customerId, setCustomerId] = useState('C-1001');
  const [conversationId, setConversationId] = useState<string>(crypto.randomUUID());
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineEvents, setPipelineEvents] = useState<WSEvent[]>([]);
  const [activeSlice, setActiveSlice] = useState<string | null>(null);
  const { connected, events, sendMessage, clearEvents } = useWebSocket(WS_URL);

  // Fetch customers and scenarios
  useEffect(() => {
    fetch(`${BACKEND_URL}/customers`)
      .then(r => r.json())
      .then(d => setCustomers(d.customers || []))
      .catch(() => {});
    fetch(`${BACKEND_URL}/scenarios`)
      .then(r => r.json())
      .then(d => setScenarios(d.scenarios || []))
      .catch(() => {});
  }, []);

  // Process incoming WebSocket events
  useEffect(() => {
    if (events.length === 0) return;
    const latest = events[events.length - 1];

    // Track active slice
    if (latest.type === 'agent_start' || latest.type === 'routing') {
      setActiveSlice(latest.data?.qgpu_slice || null);
    }

    // Add to pipeline events for debug panel
    if (latest.type !== 'done') {
      setPipelineEvents(prev => [...prev, latest]);
    }

    // Handle final response
    if (latest.type === 'done') {
      setIsProcessing(false);
      const data = latest.data;
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response,
        agent: data.agent,
        model: data.model,
        timestamp: Date.now(),
      }]);
      setActiveSlice(null);
    }
  }, [events]);

  const handleSend = useCallback((text: string, imageBase64?: string) => {
    if (!text.trim() && !imageBase64) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      image: imageBase64,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    setPipelineEvents([]);
    clearEvents();
    setIsProcessing(true);

    sendMessage({
      message: text,
      customer_id: customerId,
      conversation_id: conversationId,
      image: imageBase64 || undefined,
    });
  }, [customerId, conversationId, sendMessage, clearEvents]);

  const handleScenario = useCallback((scenario: Scenario) => {
    // Reset conversation
    const newConvId = crypto.randomUUID();
    setConversationId(newConvId);
    setMessages([]);
    setPipelineEvents([]);
    clearEvents();
    if (scenario.customer_id) setCustomerId(scenario.customer_id);

    // Send first message (with a fake image placeholder if needed)
    setTimeout(() => {
      const fakeImage = scenario.image ? 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' : undefined;
      const msg = scenario.messages ? scenario.messages[0] : scenario.message;
      handleSend(msg, fakeImage);
    }, 100);
  }, [handleSend, clearEvents]);

  // For scenario 6 (two-message scenario), send second message after first response
  const scenario6Pending = useRef<string | null>(null);
  const handleScenario6 = useCallback((scenario: Scenario) => {
    if (scenario.messages && scenario.messages.length > 1) {
      scenario6Pending.current = scenario.messages[1];
    }
    handleScenario(scenario);
  }, [handleScenario]);

  // Auto-send second message for scenario 6
  useEffect(() => {
    if (!isProcessing && scenario6Pending.current && messages.length >= 2) {
      const secondMsg = scenario6Pending.current;
      scenario6Pending.current = null;
      setTimeout(() => handleSend(secondMsg), 800);
    }
  }, [isProcessing, messages.length, handleSend]);

  const handleCustomerChange = (id: string) => {
    setCustomerId(id);
    setConversationId(crypto.randomUUID());
    setMessages([]);
    setPipelineEvents([]);
    clearEvents();
  };

  const handleNewChat = () => {
    setConversationId(crypto.randomUUID());
    setMessages([]);
    setPipelineEvents([]);
    clearEvents();
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-tencent-blue rounded-lg flex items-center justify-center text-sm font-bold">AI</div>
          <div>
            <h1 className="text-lg font-semibold text-white">Multi-Agent Customer Service</h1>
            <p className="text-xs text-gray-400">Powered by TACO-LLM + qGPU on Tencent Cloud</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 text-xs ${connected ? 'text-green-400' : 'text-red-400'}`}>
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
            {connected ? 'Connected' : 'Reconnecting...'}
          </div>
          <button onClick={handleNewChat} className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-gray-300 transition-colors">
            New Chat
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Chat Panel */}
        <div className="w-1/2 flex flex-col border-r border-gray-800">
          <ChatPanel
            messages={messages}
            onSend={handleSend}
            isProcessing={isProcessing}
            scenarios={scenarios}
            onScenario={(s) => s.messages ? handleScenario6(s) : handleScenario(s)}
          />
        </div>

        {/* Right: Debug Panel */}
        <div className="w-1/2 flex flex-col overflow-hidden">
          <AgentDebugPanel events={pipelineEvents} activeSlice={activeSlice} />
          <QGPUMonitor activeSlice={activeSlice} />
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 border-t border-gray-800 px-6 py-2 flex items-center justify-between shrink-0">
        <CustomerSelector
          customers={customers}
          selected={customerId}
          onChange={handleCustomerChange}
        />
        <div className="text-xs text-gray-500">
          TACO-LLM + qGPU &middot; Tencent Cloud
        </div>
      </footer>
    </div>
  );
}
