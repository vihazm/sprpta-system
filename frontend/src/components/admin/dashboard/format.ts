export const sum = (counts: { count: number }[]) =>
  counts.reduce((total, item) => total + item.count, 0);

export const plural = (count: number, word: string) => `${count} ${count === 1 ? word : `${word}s`}`;

// A fixed locale keeps the server and the browser rendering the same text.
export const formatNumber = (value: number) => value.toLocaleString("en-US");
