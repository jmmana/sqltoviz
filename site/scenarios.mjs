export const scenarios = {
  bar: {
    labels: { en: 'Category comparison', es: 'Comparación por categoría' },
    sql: 'SELECT category, SUM(amount) AS value FROM sales GROUP BY category ORDER BY value DESC;',
    rows: [
      { category: 'Operations', value: 181 },
      { category: 'Technology', value: 42 },
      { category: 'Services', value: 31 },
      { category: 'Retail', value: 24 },
    ],
    chartType: 'bar',
    warningCount: 0,
  },
  line: {
    labels: { en: 'Monthly trend', es: 'Tendencia mensual' },
    sql: 'SELECT month, SUM(amount) AS value FROM sales GROUP BY month ORDER BY month;',
    rows: [
      { month: '2026-01', value: 25 },
      { month: '2026-02', value: 45 },
      { month: '2026-03', value: 39 },
      { month: '2026-04', value: 47 },
      { month: '2026-05', value: 58 },
      { month: '2026-06', value: 64 },
    ],
    chartType: 'line',
    warningCount: 0,
  },
  average: {
    labels: { en: 'Non-additive averages', es: 'Promedios no aditivos' },
    sql: 'SELECT segment, AVG(amount) AS value FROM sales GROUP BY segment ORDER BY segment;',
    rows: [{ segment: 'A', value: 20.8 }, { segment: 'B', value: 29 }],
    chartType: 'bar',
    warningCount: 1,
  },
  kpi: {
    labels: { en: 'Scalar KPI', es: 'KPI de valor único' },
    sql: 'SELECT SUM(amount) AS value FROM sales;',
    rows: [{ value: 278 }],
    chartType: 'kpi',
    warningCount: 0,
  },
};
