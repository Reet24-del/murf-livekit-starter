import styles from './call-analytics-dashboard.module.css';

interface Point {
  date: string;
  successful: number;
  failed: number;
}

function pathFor(values: number[], width: number, height: number, maximum: number): string {
  return values
    .map((value, index) => {
      const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
      const y = height - (value / maximum) * height;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
}

export function CallAnalyticsChart({ trend }: { trend: Point[] }) {
  const width = 760;
  const height = 230;
  const maximum = Math.max(1, ...trend.flatMap((point) => [point.successful, point.failed]));
  const successPath = pathFor(
    trend.map((point) => point.successful),
    width,
    height,
    maximum
  );
  const failedPath = pathFor(
    trend.map((point) => point.failed),
    width,
    height,
    maximum
  );
  const areaPath = `${successPath} L ${width} ${height} L 0 ${height} Z`;

  return (
    <div className={styles.chartWrap}>
      <svg
        className={styles.chart}
        viewBox={`-22 -14 ${width + 44} ${height + 50}`}
        role="img"
        aria-labelledby="trend-title trend-description"
      >
        <title id="trend-title">Successful and failed calls over time</title>
        <desc id="trend-description">
          {trend
            .map(
              (point) =>
                `${point.date}: ${point.successful} successful and ${point.failed} failed calls`
            )
            .join('. ')}
        </desc>
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
          <line key={ratio} x1="0" y1={height * ratio} x2={width} y2={height * ratio} />
        ))}
        <path className={styles.successArea} d={areaPath} />
        <path className={styles.successLine} d={successPath} />
        <path className={styles.failedLine} d={failedPath} />
        {trend.map((point, index) => {
          const x = trend.length === 1 ? width / 2 : (index / (trend.length - 1)) * width;
          return (
            <text key={point.date} x={x} y={height + 28} textAnchor="middle">
              {new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' }).format(
                new Date(`${point.date}T00:00:00Z`)
              )}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
