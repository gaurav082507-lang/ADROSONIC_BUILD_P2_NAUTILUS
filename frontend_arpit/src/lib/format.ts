export const pct = (n: number) => `${Math.round(n * 100)}%`;
export const inr = (n: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(n);
export const dateLabel = (d: string) => {
  const x = new Date(d);
  return Number.isNaN(x.getTime())
    ? d
    : x.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
};
