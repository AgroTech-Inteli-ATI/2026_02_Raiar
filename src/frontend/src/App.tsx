import React, {useEffect, useMemo, useRef, useState} from 'react';
import {
  AlertRecord,
  listAlerts,
} from './services/alertsRepository';
import styles from './styles/dashboard.module.css';

type TabName = 'alerts' | 'configuration' | 'map';

const tabs: {id: TabName; label: string}[] = [
  {id: 'alerts', label: 'Alertas'},
  {id: 'configuration', label: 'Configuração'},
  {id: 'map', label: 'Mapa do aviário'},
];

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M4 7.5h3l1.4-2h7.2l1.4 2h3A1.5 1.5 0 0 1 21.5 9v9a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 18V9A1.5 1.5 0 0 1 4 7.5Z" />
      <circle cx="12" cy="13.5" r="3.5" />
    </svg>
  );
}

function AlertImage({alert}: {alert: AlertRecord}) {
  if (!alert.image) return null;
  const {url, alt, box} = alert.image;

  return (
    <figure className={styles.alertImage}>
      <div className={styles.imageFrame}>
        <img src={url} alt={alt} />
        <span
          className={styles.boundingBox}
          aria-label="Região identificada pelo modelo"
          style={{
            left: `${box.x * 100}%`,
            top: `${box.y * 100}%`,
            width: `${box.width * 100}%`,
            height: `${box.height * 100}%`,
          }}
        />
      </div>
      <figcaption>Imagem associada ao alerta</figcaption>
    </figure>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabName>('alerts');
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [isDemoData, setIsDemoData] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [cameraFilter, setCameraFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('');
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    let mounted = true;
    listAlerts()
      .then((result) => {
        if (mounted) {
          setAlerts(result.alerts);
          setIsDemoData(result.source === 'demo');
        }
      })
      .catch(() => {
        if (mounted) setError(true);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const cameras = useMemo(
    () => [...new Set(alerts.map((alert) => alert.camera_id))].sort((a, b) => a - b),
    [alerts],
  );

  const visibleAlerts = useMemo(
    () =>
      alerts.filter((alert) => {
        const matchesCamera = cameraFilter === 'all' || String(alert.camera_id) === cameraFilter;
        const matchesDate = !dateFilter || alert.datetime.slice(0, 10) === dateFilter;
        return matchesCamera && matchesDate;
      }),
    [alerts, cameraFilter, dateFilter],
  );

  function moveTab(event: React.KeyboardEvent<HTMLButtonElement>, currentIndex: number) {
    let nextIndex: number | undefined;
    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length;
    if (event.key === 'ArrowLeft') nextIndex = (currentIndex + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') nextIndex = 0;
    if (event.key === 'End') nextIndex = tabs.length - 1;
    if (nextIndex !== undefined) {
      event.preventDefault();
      const nextTab = tabs[nextIndex];
      setActiveTab(nextTab.id);
      tabRefs.current[nextIndex]?.focus();
    }
  }

  return (
    <main className={styles.dashboard}>
        <header className={styles.topbar}>
          <a className={styles.wordmark} href="#inicio" aria-label="Raiar Orgânicos, início">
            <span>raiar</span> <small>orgânicos</small>
          </a>
          <span className={styles.topbarLabel}>Monitoramento do aviário</span>
        </header>

        <section className={styles.content} id="inicio">
          <div className={styles.pageIntro}>
            <div>
              <p className={styles.eyebrow}>Acompanhamento diário</p>
              <h1>Olá, vamos acompanhar o aviário?</h1>
              <p className={styles.introCopy}>
                Aqui você encontra os avisos registrados pelas câmeras.
              </p>
            </div>
            <div className={styles.cameraMark} aria-hidden="true">
              <CameraIcon />
            </div>
          </div>

          <div className={styles.tabs} role="tablist" aria-label="Seções do painel">
            {tabs.map((tab, index) => (
              <button
                key={tab.id}
                ref={(element) => {
                  tabRefs.current[index] = element;
                }}
                id={`tab-${tab.id}`}
                className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`panel-${tab.id}`}
                tabIndex={activeTab === tab.id ? 0 : -1}
                onClick={() => setActiveTab(tab.id)}
                onKeyDown={(event) => moveTab(event, index)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'alerts' && (
            <section
              className={styles.panel}
              role="tabpanel"
              id="panel-alerts"
              aria-labelledby="tab-alerts"
              tabIndex={0}
            >
              <div className={styles.panelHeading}>
                <div>
                  <h2>Alertas</h2>
                  <p>Registros recebidos do monitoramento.</p>
                </div>
                {!loading && !error && (
                  <span className={styles.resultCount}>
                    {visibleAlerts.length} {visibleAlerts.length === 1 ? 'registro' : 'registros'}
                  </span>
                )}
              </div>

              {isDemoData && (
                <div className={styles.demoNotice} role="note">
                  <span className={styles.noticeDot} aria-hidden="true" />
                  <span>Visualização demonstrativa. Os registros abaixo são exemplos.</span>
                </div>
              )}

              <div className={styles.filters}>
                <label>
                  <span>Câmera</span>
                  <select
                    value={cameraFilter}
                    onChange={(event) => setCameraFilter(event.target.value)}
                    aria-label="Filtrar alertas por câmera"
                  >
                    <option value="all">Todas as câmeras</option>
                    {cameras.map((camera) => (
                      <option key={camera} value={camera}>
                        Câmera {camera}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Data</span>
                  <input
                    type="date"
                    value={dateFilter}
                    onChange={(event) => setDateFilter(event.target.value)}
                    aria-label="Filtrar alertas por data"
                  />
                </label>
                {(cameraFilter !== 'all' || dateFilter) && (
                  <button
                    className={styles.clearFilters}
                    type="button"
                    onClick={() => {
                      setCameraFilter('all');
                      setDateFilter('');
                    }}
                  >
                    Limpar filtros
                  </button>
                )}
              </div>

              {loading ? (
                <div className={styles.stateCard} role="status" aria-live="polite">
                  <span className={styles.spinner} aria-hidden="true" />
                  <p>Carregando os registros…</p>
                </div>
              ) : error ? (
                <div className={styles.stateCard} role="alert">
                  <h3>Não foi possível carregar os registros</h3>
                  <p>Tente novamente em instantes.</p>
                  <button
                    className={styles.secondaryButton}
                    type="button"
                    onClick={() => {
                      setLoading(true);
                      setError(false);
                      listAlerts()
                        .then((result) => {
                          setAlerts(result.alerts);
                          setIsDemoData(result.source === 'demo');
                        })
                        .catch(() => setError(true))
                        .finally(() => setLoading(false));
                    }}
                  >
                    Tentar novamente
                  </button>
                </div>
              ) : visibleAlerts.length === 0 ? (
                <div className={styles.stateCard}>
                  <div className={styles.emptyIcon} aria-hidden="true">
                    <CameraIcon />
                  </div>
                  <h3>Nenhum alerta encontrado</h3>
                  <p>Não há registros para os filtros escolhidos.</p>
                </div>
              ) : (
                <ul className={styles.alertList} aria-label="Lista de alertas">
                  {visibleAlerts.map((alert) => (
                    <li className={styles.alertCard} key={alert.id}>
                      <div className={styles.alertMarker} aria-hidden="true">
                        <CameraIcon />
                      </div>
                      <div className={styles.alertDetails}>
                        <div className={styles.alertTitleRow}>
                          <h3>{alert.alarm_type}</h3>
                          <time dateTime={alert.datetime}>{formatDate(alert.datetime)}</time>
                        </div>
                        <p>
                          <span>Câmera {alert.camera_id}</span>
                          <span className={styles.detailSeparator} aria-hidden="true">·</span>
                          <span>Aviário {alert.aviary_id}</span>
                        </p>
                        <AlertImage alert={alert} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {activeTab === 'configuration' && (
            <section
              className={styles.reservedPanel}
              role="tabpanel"
              id="panel-configuration"
              aria-labelledby="tab-configuration"
              tabIndex={0}
            >
              <span className={styles.reservedMark} aria-hidden="true"><CameraIcon /></span>
              <h2>Configuração</h2>
              <p>Esta área será preenchida em uma próxima etapa.</p>
            </section>
          )}

          {activeTab === 'map' && (
            <section
              className={styles.reservedPanel}
              role="tabpanel"
              id="panel-map"
              aria-labelledby="tab-map"
              tabIndex={0}
            >
              <span className={styles.reservedMark} aria-hidden="true"><CameraIcon /></span>
              <h2>Mapa do aviário</h2>
              <p>Esta área será preenchida em uma próxima etapa.</p>
            </section>
          )}

          <footer className={styles.pageFooter}>
            <span>Raiar Orgânicos</span>
            <span>Informação para acompanhar o cuidado com as aves.</span>
          </footer>
        </section>
    </main>
  );
}
