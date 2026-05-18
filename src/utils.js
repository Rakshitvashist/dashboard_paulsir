export const formatNum = (num) => {
  return parseFloat(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export const sumPL = (positions) => {
  return positions.reduce((acc, p) => acc + (p.MTM || 0), 0);
};
