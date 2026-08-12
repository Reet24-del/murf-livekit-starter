import { CloudRainIcon, SproutIcon } from './portal-icons';
import styles from './voice-portal.module.css';

interface WeatherPanelProps {
  temperature: string;
  condition: string;
  location: string;
  advisory: string;
}

export function WeatherPanel({ temperature, condition, location, advisory }: WeatherPanelProps) {
  return (
    <section className={`${styles.panel} ${styles.weatherPanel}`} aria-labelledby="weather-title">
      <div className={styles.panelHeading}>
        <CloudRainIcon aria-hidden="true" />
        <h2 id="weather-title">Live weather</h2>
      </div>
      <p className={styles.temperature}>{temperature}</p>
      <p className={styles.panelMeta} suppressHydrationWarning>
        {condition} · {location}
      </p>
      <div className={styles.panelDivider} />
      <p className={styles.advisory}>
        <span className={styles.advisoryIcon}>
          <SproutIcon aria-hidden="true" />
        </span>
        {advisory}
      </p>
    </section>
  );
}
