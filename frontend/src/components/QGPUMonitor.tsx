interface QGPUMonitorProps {
  activeSlice: string | null;
}

export default function QGPUMonitor({ activeSlice }: QGPUMonitorProps) {
  const slice1Active = activeSlice?.includes('1');
  const slice2Active = activeSlice?.includes('2');

  return (
    <div className="shrink-0 border-t border-gray-800 bg-gray-900/50 px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">qGPU Status</h3>
        <span className="text-[10px] text-gray-600">NVIDIA L20 48GB</span>
      </div>

      <div className="space-y-2">
        {/* Slice 1 */}
        <div className="flex items-center gap-3">
          <div className="w-24 shrink-0">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${slice1Active ? 'bg-blue-400 animate-pulse-fast' : 'bg-blue-400/40'}`} />
              <span className="text-[10px] text-blue-300 font-medium">Slice 1</span>
            </div>
            <span className="text-[9px] text-gray-500 ml-3.5">Qwen3-VL-8B</span>
          </div>
          <div className="flex-1">
            <div className="h-2.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${slice1Active ? 'bg-blue-400' : 'bg-blue-400/60'}`}
                style={{ width: slice1Active ? '88%' : '75%' }}
              />
            </div>
          </div>
          <span className="text-[10px] text-gray-500 w-16 text-right">
            {slice1Active ? '14.1' : '12.0'}/16 GB
          </span>
        </div>

        {/* Slice 2 */}
        <div className="flex items-center gap-3">
          <div className="w-24 shrink-0">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${slice2Active ? 'bg-emerald-400 animate-pulse-fast' : 'bg-emerald-400/40'}`} />
              <span className="text-[10px] text-emerald-300 font-medium">Slice 2</span>
            </div>
            <span className="text-[9px] text-gray-500 ml-3.5">Qwen2.5-VL-7B</span>
          </div>
          <div className="flex-1">
            <div className="h-2.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${slice2Active ? 'bg-emerald-400' : 'bg-emerald-400/60'}`}
                style={{ width: slice2Active ? '81%' : '69%' }}
              />
            </div>
          </div>
          <span className="text-[10px] text-gray-500 w-16 text-right">
            {slice2Active ? '13.0' : '11.0'}/16 GB
          </span>
        </div>

        {/* Total GPU */}
        <div className="flex items-center gap-3 pt-1 border-t border-gray-800/50">
          <div className="w-24 shrink-0">
            <span className="text-[10px] text-gray-400 font-medium">Total GPU</span>
          </div>
          <div className="flex-1">
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-400 to-emerald-400 rounded-full transition-all duration-500"
                style={{ width: (slice1Active || slice2Active) ? '58%' : '48%' }}
              />
            </div>
          </div>
          <span className="text-[10px] text-gray-500 w-16 text-right">
            {(slice1Active || slice2Active) ? '27.1' : '23.0'}/48 GB
          </span>
        </div>
      </div>
    </div>
  );
}
