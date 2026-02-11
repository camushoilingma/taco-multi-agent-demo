import { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import ImageUpload from './ImageUpload';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
  model?: string;
  image?: string;
  timestamp: number;
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

interface ChatPanelProps {
  messages: Message[];
  onSend: (text: string, imageBase64?: string) => void;
  isProcessing: boolean;
  scenarios: Scenario[];
  onScenario: (scenario: Scenario) => void;
}

export default function ChatPanel({ messages, onSend, isProcessing, scenarios, onScenario }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [showScenarios, setShowScenarios] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (messages.length > 0) setShowScenarios(false);
  }, [messages.length]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() && !imageBase64) return;
    onSend(input, imageBase64 || undefined);
    setInput('');
    setImageBase64(null);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && showScenarios && (
          <div className="animate-fade-in">
            <div className="text-center mb-6 mt-8">
              <div className="w-16 h-16 bg-gradient-to-br from-tencent-blue to-blue-400 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-white mb-1">Multi-Agent AI Customer Service</h2>
              <p className="text-sm text-gray-400">Try a demo scenario or type your own message</p>
            </div>

            <div className="grid grid-cols-1 gap-2 max-w-lg mx-auto">
              {scenarios.map((s) => (
                <button
                  key={s.id}
                  onClick={() => onScenario(s)}
                  className="text-left p-3 bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 rounded-xl transition-all group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gray-800 group-hover:bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-400 shrink-0">
                      {s.id}
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-gray-200 truncate">{s.name}</div>
                      <div className="text-xs text-gray-500 truncate">{s.description}</div>
                    </div>
                    {s.image && (
                      <span className="ml-auto text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded-full shrink-0">Vision</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isProcessing && (
          <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse ml-2">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-tencent-blue rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-tencent-blue rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-tencent-blue rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            Agent is processing...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Image preview */}
      {imageBase64 && (
        <div className="px-4 py-2 border-t border-gray-800">
          <div className="flex items-center gap-2 bg-gray-900 rounded-lg p-2 max-w-xs">
            <img src={`data:image/png;base64,${imageBase64}`} alt="Upload" className="w-12 h-12 rounded object-cover" />
            <span className="text-xs text-gray-400 flex-1">Image attached</span>
            <button onClick={() => setImageBase64(null)} className="text-gray-500 hover:text-gray-300">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-800 shrink-0">
        <div className="flex items-center gap-2 bg-gray-900 border border-gray-700 rounded-xl px-4 py-2 focus-within:border-tencent-blue transition-colors">
          <ImageUpload onImageSelect={setImageBase64} />
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 bg-transparent text-white placeholder-gray-500 outline-none text-sm"
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={isProcessing || (!input.trim() && !imageBase64)}
            className="p-1.5 bg-tencent-blue hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
