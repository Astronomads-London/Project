// Draws a seven-day bar chart into every .metric-chart element on the page.
// charts is the list built by app/utils/charts.py; each element is matched to
// its chart through its data-chart attribute.
window.renderMetricCharts = (charts) => {
  const chartByField = Object.fromEntries(charts.map((chart) => [chart.field, chart]));
  const svgElement = (name, attributes = {}) => {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    return element;
  };
  document.querySelectorAll(".metric-chart").forEach((container) => {
    const chart = chartByField[container.dataset.chart];
    if (!chart) return;
    const readings = chart.points.map((point) => {
      if (point.value === null || point.value === undefined || point.value === "") return null;
      if (chart.field === "blood_pressure") {
        const match = String(point.value).match(/^\s*(\d{2,3})\s*\/\s*(\d{2,3})\s*$/);
        return match ? Number(match[1]) : null;
      }
      const numeric = Number(point.value);
      return Number.isFinite(numeric) ? numeric : null;
    });
    const svg = svgElement("svg", {
      viewBox: "0 0 700 220",
      role: "img",
      "aria-label": `${chart.title} over the last seven days`
    });
    const plot = { left: 80, right: 670, top: 40, bottom: 175 };
    const dataMax = Math.max(0, Number(chart.target) || 0, ...readings.filter((value) => value !== null));
    const max = chart.field === "o2_level"
      ? 100
      : dataMax > 0 ? Math.ceil(dataMax * 1.15 / 5) * 5 : 1;
    [0, 0.5, 1].forEach((fraction) => {
      const y = plot.bottom - fraction * (plot.bottom - plot.top);
      const tick = svgElement("text", {
        x: plot.left - 10, y: y + 4, class: "metric-chart__axis-label", "text-anchor": "end"
      });
      tick.textContent = Number((fraction * max).toPrecision(3)).toString();
      svg.appendChild(tick);
      svg.appendChild(svgElement("line", {
        x1: plot.left, x2: plot.right, y1: y, y2: y, class: "metric-chart__gridline"
      }));
    });
    const axisUnit = svgElement("text", {
      x: 15, y: (plot.top + plot.bottom) / 2,
      class: "metric-chart__axis-unit",
      "text-anchor": "middle",
      transform: `rotate(-90 15 ${(plot.top + plot.bottom) / 2})`
    });
    axisUnit.textContent = chart.unit;
    svg.appendChild(axisUnit);

    chart.points.forEach((point, index) => {
      const x = plot.left + 8 + index * 84;
      const reading = readings[index];
      const label = svgElement("text", {
        x: x + 26, y: 205, class: "metric-chart__label", "text-anchor": "middle"
      });
      label.textContent = point.label;
      svg.appendChild(label);
      if (reading === null) return;

      const height = Math.max(4, (reading / max) * (plot.bottom - plot.top));
      const rect = svgElement("rect", {
        x, y: plot.bottom, width: 52, height: 0, rx: 7,
        class: `metric-chart__bar metric-chart__bar--${chart.field}`,
        tabindex: 0,
        role: "img"
      });
      const valueLabel = `${point.value} ${chart.unit}`;
      rect.setAttribute("aria-label", `${point.label}: ${valueLabel}`);
      const title = svgElement("title");
      title.textContent = `${point.label}: ${valueLabel}`;
      rect.appendChild(title);
      svg.appendChild(rect);
      requestAnimationFrame(() => {
        rect.setAttribute("y", plot.bottom - height);
        rect.setAttribute("height", height);
      });
    });
    container.appendChild(svg);
    if (!readings.some((value) => value !== null)) {
      const empty = document.createElement("p");
      empty.className = "metric-chart__empty";
      empty.textContent = "No readings logged for the last seven days.";
      container.appendChild(empty);
    }
  });
};
