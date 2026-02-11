interface Customer {
  customer_id: string;
  name: string;
  language: string;
  is_premium: boolean;
}

interface CustomerSelectorProps {
  customers: Customer[];
  selected: string;
  onChange: (id: string) => void;
}

export default function CustomerSelector({ customers, selected, onChange }: CustomerSelectorProps) {
  const current = customers.find(c => c.customer_id === selected);

  return (
    <div className="flex items-center gap-3">
      <select
        value={selected}
        onChange={(e) => onChange(e.target.value)}
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 outline-none focus:border-tencent-blue transition-colors cursor-pointer"
      >
        {customers.map((c) => (
          <option key={c.customer_id} value={c.customer_id}>
            {c.name} ({c.customer_id})
          </option>
        ))}
        {customers.length === 0 && (
          <option value="C-1001">Maria Ionescu (C-1001)</option>
        )}
      </select>
      {current && (
        <div className="flex items-center gap-2">
          {current.is_premium && (
            <span className="text-[10px] bg-amber-900/50 text-amber-300 px-2 py-0.5 rounded-full font-medium">
              ★ Premium
            </span>
          )}
          <span className="text-[10px] text-gray-500 uppercase">{current.language}</span>
        </div>
      )}
    </div>
  );
}
