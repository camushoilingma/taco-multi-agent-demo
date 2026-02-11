interface CostTrackerProps {
  inputTokens: number;
  outputTokens: number;
  model: string;
  costUsd: number;
}

export default function CostTracker({ inputTokens, outputTokens, model, costUsd }: CostTrackerProps) {
  return (
    <div className="flex items-center gap-3 text-[10px] text-gray-500 px-3 py-1.5 bg-gray-900/30 rounded-lg">
      <span>{inputTokens + outputTokens} tokens</span>
      <span className="text-gray-700">|</span>
      <span>{inputTokens} in / {outputTokens} out</span>
      <span className="text-gray-700">|</span>
      <span className="text-green-500">${costUsd.toFixed(4)}</span>
      <span className="text-gray-700">|</span>
      <span>{model}</span>
    </div>
  );
}
