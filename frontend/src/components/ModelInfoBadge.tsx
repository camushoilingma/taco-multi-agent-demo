interface ModelInfoBadgeProps {
  agent?: string;
  model?: string;
  slice?: string;
  compact?: boolean;
}

const AGENT_LABELS: Record<string, string> = {
  router: 'Router',
  order_tracker: 'Order Tracker',
  returns: 'Returns',
  product_advisor: 'Product Advisor',
  escalation: 'Escalation',
};

const MODEL_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  'Qwen3-VL-8B': { bg: 'bg-blue-900/40', text: 'text-blue-300', dot: 'bg-blue-400' },
  'Qwen2.5-VL-7B': { bg: 'bg-emerald-900/40', text: 'text-emerald-300', dot: 'bg-emerald-400' },
};

export default function ModelInfoBadge({ agent, model, slice, compact }: ModelInfoBadgeProps) {
  const colors = MODEL_COLORS[model || ''] || { bg: 'bg-gray-800', text: 'text-gray-300', dot: 'bg-gray-400' };
  const label = AGENT_LABELS[agent || ''] || agent || 'Agent';

  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${colors.bg} ${colors.text}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
        {model || 'Unknown'}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs font-medium text-gray-400">{label}</span>
      {model && (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${colors.bg} ${colors.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
          {model}
        </span>
      )}
    </div>
  );
}
