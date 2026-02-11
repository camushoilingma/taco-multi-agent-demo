import { useState } from 'react';

interface ThinkingDisplayProps {
  text: string;
}

export default function ThinkingDisplay({ text }: ThinkingDisplayProps) {
  const [expanded, setExpanded] = useState(false);

  if (!text) return null;

  return (
    <div className="mt-2 animate-fade-in">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs text-purple-400 hover:text-purple-300 transition-colors"
      >
        <svg className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`} fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
        <span className="flex items-center gap-1">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          Model Reasoning (Qwen3 Think Mode)
        </span>
      </button>
      {expanded && (
        <div className="mt-2 p-3 bg-purple-950/30 border border-purple-900/50 rounded-lg">
          <pre className="text-xs text-purple-300/80 whitespace-pre-wrap font-mono leading-relaxed">{text}</pre>
        </div>
      )}
    </div>
  );
}
