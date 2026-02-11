import ReactMarkdown from 'react-markdown';
import ModelInfoBadge from './ModelInfoBadge';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
  model?: string;
  image?: string;
  timestamp: number;
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-slide-in`}>
      <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Agent badge */}
        {!isUser && message.agent && (
          <div className="flex items-center gap-2 mb-1 ml-1">
            <ModelInfoBadge agent={message.agent} model={message.model} />
          </div>
        )}

        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-tencent-blue text-white rounded-tr-md'
              : 'bg-gray-800 text-gray-100 rounded-tl-md border border-gray-700'
          }`}
        >
          {/* Image preview */}
          {message.image && (
            <div className="mb-2">
              <div className="w-32 h-24 bg-gray-700 rounded-lg flex items-center justify-center text-xs text-gray-400 border border-gray-600">
                <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            </div>
          )}

          <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>

        <div className={`text-[10px] text-gray-600 mt-1 ${isUser ? 'text-right mr-1' : 'ml-1'}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}
