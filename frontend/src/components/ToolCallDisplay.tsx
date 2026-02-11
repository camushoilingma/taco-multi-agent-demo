import { useState } from 'react';

interface ToolCallDisplayProps {
  tool: string;
  args: Record<string, any>;
  result?: Record<string, any>;
  latency_ms?: number;
}

export default function ToolCallDisplay({ tool, args, result, latency_ms }: ToolCallDisplayProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden animate-fade-in">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-800/50 hover:bg-gray-800 text-left transition-colors"
      >
        <svg className="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <code className="text-xs text-amber-300 font-mono">{tool}</code>
        <span className="text-[10px] text-gray-500 ml-auto">
          {latency_ms !== undefined ? `${latency_ms}ms` : ''}
        </span>
        <svg className={`w-3 h-3 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && (
        <div className="px-3 py-2 text-xs font-mono space-y-2 bg-gray-900/50">
          <div>
            <span className="text-gray-500">args: </span>
            <span className="text-gray-300">{JSON.stringify(args, null, 2)}</span>
          </div>
          {result && (
            <div>
              <span className="text-gray-500">result: </span>
              <pre className="text-gray-400 whitespace-pre-wrap max-h-32 overflow-y-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
