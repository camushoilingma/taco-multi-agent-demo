import { useEffect, useRef } from 'react';
import { WSEvent } from '../hooks/useWebSocket';
import ToolCallDisplay from './ToolCallDisplay';
import ThinkingDisplay from './ThinkingDisplay';
import CostTracker from './CostTracker';

interface AgentDebugPanelProps {
  events: WSEvent[];
  activeSlice: string | null;
}

const SLICE_COLORS: Record<string, string> = {
  'Slice 1 (16GB)': 'border-blue-500',
  'Slice 2 (16GB)': 'border-emerald-500',
};

const SLICE_BG: Record<string, string> = {
  'Slice 1 (16GB)': 'bg-blue-500/10',
  'Slice 2 (16GB)': 'bg-emerald-500/10',
};

const AGENT_ICONS: Record<string, string> = {
  router: '🔀',
  order_tracker: '📦',
  returns: '↩️',
  product_advisor: '💡',
  escalation: '🚨',
};

const AGENT_LABELS: Record<string, string> = {
  router: 'ROUTER',
  order_tracker: 'ORDER TRACKER',
  returns: 'RETURNS',
  product_advisor: 'PRODUCT ADVISOR',
  escalation: 'ESCALATION',
};

export default function AgentDebugPanel({ events, activeSlice }: AgentDebugPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [events]);

  if (events.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center text-gray-600">
          <svg className="w-12 h-12 mx-auto mb-3 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
          </svg>
          <p className="text-sm font-medium text-gray-500">Agent Pipeline</p>
          <p className="text-xs text-gray-600 mt-1">Send a message to see the routing, model selection, and tool calls in real-time</p>
        </div>
      </div>
    );
  }

  // Group events into agent sections
  const sections: { agent: string; model: string; slice: string; events: WSEvent[] }[] = [];
  let currentSection: typeof sections[0] | null = null;

  for (const ev of events) {
    if (ev.type === 'agent_start' || ev.type === 'routing') {
      currentSection = {
        agent: ev.data.agent || 'router',
        model: ev.data.model || '',
        slice: ev.data.qgpu_slice || '',
        events: [ev],
      };
      sections.push(currentSection);
    } else if (ev.type === 'model_switch' || ev.type === 'reroute') {
      // Add as standalone section
      sections.push({
        agent: '_transition',
        model: '',
        slice: '',
        events: [ev],
      });
    } else if (currentSection) {
      currentSection.events.push(ev);
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-2.5 border-b border-gray-800 bg-gray-900/50 shrink-0">
        <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
          <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
          </svg>
          Agent Pipeline
        </h2>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {sections.map((section, idx) => {
          if (section.agent === '_transition') {
            const ev = section.events[0];
            if (ev.type === 'model_switch') {
              return (
                <div key={idx} className="flex items-center gap-2 py-2 animate-slide-in">
                  <div className="flex-1 h-px bg-gradient-to-r from-blue-500/50 to-emerald-500/50" />
                  <span className="text-[10px] font-bold text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded-full whitespace-nowrap">
                    ⚡ Model Switch!
                  </span>
                  <div className="flex-1 h-px bg-gradient-to-r from-emerald-500/50 to-blue-500/50" />
                </div>
              );
            }
            if (ev.type === 'reroute') {
              return (
                <div key={idx} className="flex items-center gap-2 py-2 animate-slide-in">
                  <div className="flex-1 h-px bg-orange-500/30" />
                  <div className="text-center">
                    <span className="text-[10px] font-bold text-orange-400 bg-orange-400/10 px-2 py-0.5 rounded-full">
                      🔄 Reroute: {ev.data.from} → {ev.data.to}
                    </span>
                    <div className="text-[9px] text-gray-500 mt-0.5">{ev.data.reason}</div>
                  </div>
                  <div className="flex-1 h-px bg-orange-500/30" />
                </div>
              );
            }
          }

          const sliceBorder = SLICE_COLORS[section.slice] || 'border-gray-700';
          const sliceBg = SLICE_BG[section.slice] || '';
          const icon = AGENT_ICONS[section.agent] || '🤖';
          const label = AGENT_LABELS[section.agent] || section.agent.toUpperCase();

          // Extract specific event types
          const routingEv = section.events.find(e => e.type === 'routing');
          const toolCalls = section.events.filter(e => e.type === 'tool_call');
          const toolResults = section.events.filter(e => e.type === 'tool_result');
          const thinkingEv = section.events.find(e => e.type === 'thinking');
          const costEv = section.events.find(e => e.type === 'cost');
          const responseEv = section.events.find(e => e.type === 'response');

          return (
            <div key={idx} className={`border ${sliceBorder} rounded-xl ${sliceBg} overflow-hidden animate-slide-in`}>
              {/* Header */}
              <div className="flex items-center justify-between px-3 py-2 bg-gray-900/50">
                <div className="flex items-center gap-2">
                  <span className="text-base">{icon}</span>
                  <span className="text-xs font-bold text-gray-200">{label}</span>
                </div>
                <div className="flex items-center gap-2">
                  {section.model && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      section.slice.includes('1') ? 'bg-blue-900/50 text-blue-300' : 'bg-emerald-900/50 text-emerald-300'
                    }`}>
                      {section.model}
                    </span>
                  )}
                  {section.slice && (
                    <span className="text-[10px] text-gray-500">{section.slice}</span>
                  )}
                </div>
              </div>

              <div className="px-3 py-2 space-y-2">
                {/* Routing result */}
                {routingEv && (
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-gray-500">Intent:</span>
                    <span className="font-bold text-white">{routingEv.data.category}</span>
                    <span className="text-gray-500">Confidence:</span>
                    <span className={`font-mono ${
                      routingEv.data.confidence > 0.9 ? 'text-green-400' :
                      routingEv.data.confidence > 0.7 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {Math.round(routingEv.data.confidence * 100)}%
                    </span>
                    {routingEv.data.latency_ms && (
                      <span className="text-gray-600 text-[10px]">{routingEv.data.latency_ms}ms</span>
                    )}
                  </div>
                )}

                {/* Thinking */}
                {thinkingEv && <ThinkingDisplay text={thinkingEv.data.text} />}

                {/* Tool calls */}
                {toolCalls.map((tc, tcIdx) => {
                  const matchingResult = toolResults.find(tr => tr.data.tool === tc.data.tool);
                  return (
                    <ToolCallDisplay
                      key={tcIdx}
                      tool={tc.data.tool}
                      args={tc.data.args}
                      result={matchingResult?.data.result}
                      latency_ms={matchingResult?.data.latency_ms}
                    />
                  );
                })}

                {/* Cost */}
                {costEv && (
                  <CostTracker
                    inputTokens={costEv.data.input_tokens}
                    outputTokens={costEv.data.output_tokens}
                    model={costEv.data.model}
                    costUsd={costEv.data.estimated_cost_usd}
                  />
                )}

                {/* Response latency */}
                {responseEv && (
                  <div className="text-[10px] text-gray-500 text-right">
                    Total: {responseEv.data.total_latency_ms}ms
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
