// Em: src/components/MetricCard.jsx

export default function MetricCard({ title, value, colorClass = 'text-blue-600 dark:text-blue-400' }) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-md dark:bg-gray-800">
      <h6 className="mb-1 text-sm font-medium text-gray-500 dark:text-gray-400">
        {title}
      </h6>
      <h4 className={`text-3xl font-bold ${colorClass}`}>
        {value}
      </h4>
    </div>
  );
}