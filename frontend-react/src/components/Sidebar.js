import React, { useState, useEffect } from 'react';
import './Sidebar.css';

const Sidebar = ({
  onRouteRequest, onCancelRoute, loading, error, route, analysis,
  onClear, onShowSituation, onHeatmapSourceChange,
  showRiskZones, setShowRiskZones,
  showCorridors, setShowCorridors,
  showTraffic, setShowTraffic,
  dateFilter, setDateFilter,
  hourFilter, setHourFilter,
  currentUser,
}) => {
  const [vesselType, setVesselType] = useState('cargo');
  const [optimization, setOptimization] = useState('time');
  const [heatmapSource, setHeatmapSource] = useState('retrospective');
  const [similarParams, setSimilarParams] = useState({
    risk_score: 0.6,
    wind_speed: 12,
    wave_height: 2.5
  });
  const [similarResults, setSimilarResults] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [routeParams, setRouteParams] = useState({
    wind_speed: 12,
    wave_height: 2.5,
    season: 1
  });

  const [availableDates, setAvailableDates] = useState([]);
  const [loadingDates, setLoadingDates] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminMessage, setAdminMessage] = useState('');
  const [systemStats, setSystemStats] = useState(null);

  useEffect(() => {
    loadAvailableDates();
  }, []);

  const loadAvailableDates = async () => {
    setLoadingDates(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/available_dates');
      const data = await response.json();
      setAvailableDates(data.dates || []);
    } catch (err) {
      console.error('Ошибка загрузки дат:', err);
    } finally {
      setLoadingDates(false);
    }
  };

  const handleHeatmapChange = (e) => {
    const newSource = e.target.value;
    setHeatmapSource(newSource);
    if (onHeatmapSourceChange) onHeatmapSourceChange(newSource);
  };

  const handleRoute = () => {
    onRouteRequest({
      vesselType,
      optimization,
      wind_speed: routeParams.wind_speed,
      wave_height: routeParams.wave_height,
      season: routeParams.season
    });
  };

  const handleSimilar = async () => {
    setSimilarLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/similar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...similarParams, vessel_type: vesselType, season: 1, k: 5 })
      });
      const data = await response.json();
      setSimilarResults(data.similar_situations || []);
    } catch (err) {
      console.error('Ошибка поиска:', err);
    } finally {
      setSimilarLoading(false);
    }
  };

  const handleSituationClick = (lat, lon, description) => {
    if (onShowSituation) onShowSituation(lat, lon, description);
  };

  const handleResetFilter = () => {
    setDateFilter({ startDate: '', endDate: '' });
    setHourFilter(null);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Нет даты';
    try {
      const parts = dateStr.split('-');
      if (parts.length === 3) {
        return `${parts[2]}.${parts[1]}`;
      }
      return dateStr;
    } catch {
      return dateStr;
    }
  };

  const authFetch = async (url, options = {}) => {
    const token = localStorage.getItem('token');
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };
    return fetch(url, { ...options, headers });
  };

  const handleRecalculateRiskZones = async () => {
    if (!window.confirm('Пересчитать зоны риска? Это может занять до 5 минут.')) return;
    setAdminLoading('risk');
    setAdminMessage('');
    try {
      const res = await authFetch('http://127.0.0.1:8000/api/admin/recalculate_risk_zones', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setAdminMessage('Успешно: ' + data.message);
      } else {
        setAdminMessage('Ошибка: ' + data.detail);
      }
    } catch (err) {
      setAdminMessage('Ошибка: ' + err.message);
    } finally {
      setAdminLoading(false);
    }
  };

  const handleRecalculateCorridors = async () => {
    if (!window.confirm('Пересчитать морские коридоры? Это может занять до 5 минут.')) return;
    setAdminLoading('corridors');
    setAdminMessage('');
    try {
      const res = await authFetch('http://127.0.0.1:8000/api/admin/recalculate_corridors', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setAdminMessage('Успешно: ' + data.message);
      } else {
        setAdminMessage('Ошибка: ' + data.detail);
      }
    } catch (err) {
      setAdminMessage('Ошибка: ' + err.message);
    } finally {
      setAdminLoading(false);
    }
  };

  const handleRecalculateTraffic = async () => {
    if (!window.confirm('Пересчитать плотность трафика? Это может занять до 5 минут.')) return;
    setAdminLoading('traffic');
    setAdminMessage('');
    try {
      const res = await authFetch('http://127.0.0.1:8000/api/admin/recalculate_traffic', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setAdminMessage('Успешно: ' + data.message);
      } else {
        setAdminMessage('Ошибка: ' + data.detail);
      }
    } catch (err) {
      setAdminMessage('Ошибка: ' + err.message);
    } finally {
      setAdminLoading(false);
    }
  };

  const handleLoadStatistics = async () => {
    setAdminLoading('stats');
    setAdminMessage('');
    try {
      const res = await authFetch('http://127.0.0.1:8000/api/admin/statistics');
      const data = await res.json();
      if (res.ok) {
        setSystemStats(data);
      } else {
        setAdminMessage('Ошибка: ' + data.detail);
      }
    } catch (err) {
      setAdminMessage('Ошибка: ' + err.message);
    } finally {
      setAdminLoading(false);
    }
  };

  const handleExportRoute = async () => {
    if (!route) {
      alert('Сначала постройте маршрут');
      return;
    }
    try {
      const res = await authFetch('http://127.0.0.1:8000/api/route/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(route)
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `route_export_${new Date().toISOString().slice(0,10)}.json`;
      a.click();
      window.URL.revokeObjectURL(url);
      setAdminMessage('Маршрут экспортирован');
    } catch (err) {
      setAdminMessage('Ошибка экспорта: ' + err.message);
    }
  };

  const isSpecialist = currentUser && currentUser.role === 'specialist';

  return (
    <div className="sidebar">
      <h2>Построение маршрута</h2>
      <div className="form-group">
        <label>Тип судна</label>
        <select value={vesselType} onChange={(e) => setVesselType(e.target.value)}>
          <option value="cargo">Грузовое</option>
          <option value="tanker">Танкер</option>
          <option value="passenger">Пассажирское</option>
          <option value="fishing">Рыболовное</option>
          <option value="tug">Буксир</option>
        </select>
      </div>
      <div className="form-group">
        <label>Оптимизация</label>
        <select value={optimization} onChange={(e) => setOptimization(e.target.value)}>
          <option value="time">Минимум времени</option>
          <option value="safety">Минимум риска</option>
        </select>
      </div>

      <button onClick={handleRoute} disabled={loading}>
        {loading ? 'Загрузка...' : 'Построить маршрут'}
      </button>
      {loading && (
        <>
          <button onClick={onCancelRoute} className="secondary" style={{ marginTop: '8px', backgroundColor: '#dc2626' }}>
            Отменить
          </button>
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${Math.random() * 90}%` }}></div>
            <div className="progress-text">Построение маршрута...</div>
          </div>
        </>
      )}
      <button onClick={onClear} className="secondary">Очистить маркеры</button>
      {error && <div className="error">{error}</div>}
      {route && (
        <div className="result">
          <div className="stat">Расстояние: {route.total_distance_km?.toFixed(1)} км</div>
          <div className="stat">Оптимизация: {route.optimization}</div>
          <div className="stat">Сегментов: {route.segments?.length}</div>
        </div>
      )}
      {analysis && analysis.best_match && (
        <div className="result" style={{ marginTop: '12px', borderColor: '#1e3a8a' }}>
          <div className="stat" style={{ fontWeight: 'bold' }}>Лучший исторический аналог</div>
          <div className="stat">Риск: {analysis.best_match.risk_score?.toFixed(2)}</div>
          <div className="stat">Ветер: {analysis.best_match.wind_speed?.toFixed(1)} м/с</div>
          <div className="stat">Волны: {analysis.best_match.wave_height?.toFixed(1)} м</div>
          <div className="stat">Координаты: {analysis.best_match.latitude?.toFixed(2)}, {analysis.best_match.longitude?.toFixed(2)}</div>
          <button onClick={() => handleSituationClick(analysis.best_match.latitude, analysis.best_match.longitude, `Риск ${analysis.best_match.risk_score?.toFixed(2)}`)} style={{ marginTop: '8px', fontSize: '12px', padding: '6px' }}>
            Показать на карте
          </button>
        </div>
      )}

      <hr />

      <h2>Поиск похожих ситуаций</h2>
      <div className="form-group">
        <label>Уровень риска (0-1)</label>
        <input type="number" step="0.1" value={similarParams.risk_score} onChange={(e) => setSimilarParams({...similarParams, risk_score: parseFloat(e.target.value)})} />
      </div>
      <div className="form-group">
        <label>Скорость ветра (м/с)</label>
        <input type="number" step="1" value={similarParams.wind_speed} onChange={(e) => setSimilarParams({...similarParams, wind_speed: parseFloat(e.target.value)})} />
      </div>
      <div className="form-group">
        <label>Высота волны (м)</label>
        <input type="number" step="0.5" value={similarParams.wave_height} onChange={(e) => setSimilarParams({...similarParams, wave_height: parseFloat(e.target.value)})} />
      </div>
      <button onClick={handleSimilar} disabled={similarLoading}>
        {similarLoading ? 'Поиск...' : 'Найти похожие'}
      </button>
      {similarResults.length > 0 && (
        <div className="result">
          <div className="stat">Найдено {similarResults.length} ситуаций:</div>
          {similarResults.slice(0, 5).map((sit, idx) => (
            <div key={idx} className="stat-item" style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => handleSituationClick(sit.latitude, sit.longitude, `Риск ${sit.risk_score?.toFixed(2)}`)}>
              Риск {sit.risk_score?.toFixed(2)}, ветер {sit.wind_speed} м/с, волны {sit.wave_height} м
            </div>
          ))}
        </div>
      )}

      <hr />

      <h2>Источник тепловой карты</h2>
      <div className="form-group">
        <label>
          <input type="radio" value="retrospective" checked={heatmapSource === 'retrospective'} onChange={handleHeatmapChange} />
          Ретроспективные данные (история)
        </label>
        <label>
          <input type="radio" value="current" checked={heatmapSource === 'current'} onChange={handleHeatmapChange} />
          Текущие суда
        </label>
      </div>

      <hr />
      <h2>Слои карты</h2>
      <div className="form-group">
        <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
          <input type="checkbox" checked={showRiskZones} onChange={(e) => setShowRiskZones(e.target.checked)} style={{ marginRight: '8px' }} />
          Зоны риска
        </label>
        <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
          <input type="checkbox" checked={showCorridors} onChange={(e) => setShowCorridors(e.target.checked)} style={{ marginRight: '8px' }} />
          Морские коридоры
        </label>
        <label style={{ display: 'block', marginBottom: '8px', cursor: 'pointer' }}>
          <input type="checkbox" checked={showTraffic} onChange={(e) => setShowTraffic(e.target.checked)} style={{ marginRight: '8px' }} />
          Плотность трафика
        </label>
      </div>

      <hr />
      <h2>Фильтр по времени</h2>
      <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f9fafb', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
        <div style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '8px', color: '#374151' }}>
          Доступные даты ({availableDates.length}):
        </div>
        {loadingDates ? (
          <div style={{ fontSize: '12px', color: '#6b7280', fontStyle: 'italic' }}>Загрузка...</div>
        ) : availableDates.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxHeight: '140px', overflowY: 'auto', padding: '4px' }}>
            {availableDates.slice(0, 40).map((item, idx) => {
              const dateStr = item && item.date ? item.date : (item || '');
              const isSelected = dateFilter.startDate === dateStr && dateFilter.endDate === dateStr;
              const displayDate = formatDate(dateStr);
              return (
                <button
                  key={idx}
                  onClick={() => setDateFilter({ startDate: dateStr, endDate: dateStr })}
                  style={{
                    padding: '4px 8px',
                    backgroundColor: isSelected ? '#1e3a8a' : '#e5e7eb',
                    color: isSelected ? 'white' : '#374151',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: isSelected ? 'bold' : 'normal',
                    minWidth: '60px'
                  }}
                  title={item && item.count ? `${item.count} записей` : 'Нет данных'}
                >
                  {displayDate}
                </button>
              );
            })}
          </div>
        ) : (
          <div style={{ fontSize: '12px', color: '#6b7280', fontStyle: 'italic' }}>Нет доступных дат</div>
        )}
      </div>

      <div className="form-group">
        <label>Дата начала:</label>
        <input type="date" value={dateFilter.startDate} onChange={(e) => setDateFilter({...dateFilter, startDate: e.target.value})} style={{ width: '100%', padding: '6px' }} />
      </div>
      <div className="form-group">
        <label>Дата окончания:</label>
        <input type="date" value={dateFilter.endDate} onChange={(e) => setDateFilter({...dateFilter, endDate: e.target.value})} style={{ width: '100%', padding: '6px' }} />
      </div>
      <div className="form-group">
        <label>Час суток:</label>
        <select value={hourFilter === null ? 'any' : hourFilter} onChange={(e) => setHourFilter(e.target.value === 'any' ? null : parseInt(e.target.value))} style={{ width: '100%', padding: '6px' }}>
          <option value="any">Любой час</option>
          {Array.from({length: 24}, (_, i) => (
            <option key={i} value={i}>{String(i).padStart(2, '0')}:00 - {String(i).padStart(2, '0')}:59</option>
          ))}
        </select>
      </div>

      <button onClick={handleResetFilter} className="secondary" style={{ marginTop: '8px' }}>
        Сбросить фильтр
      </button>

      {(dateFilter.startDate || dateFilter.endDate || hourFilter !== null) && (
        <div style={{ marginTop: '10px', padding: '8px', backgroundColor: '#d1fae5', borderRadius: '4px', fontSize: '12px', border: '1px solid #10b981' }}>
          <strong style={{ color: '#065f46' }}>Фильтр активен:</strong>
          {dateFilter.startDate && <div style={{ color: '#065f46' }}>С: {dateFilter.startDate}</div>}
          {dateFilter.endDate && <div style={{ color: '#065f46' }}>По: {dateFilter.endDate}</div>}
          {hourFilter !== null && <div style={{ color: '#065f46' }}>Час: {String(hourFilter).padStart(2, '0')}:00</div>}
        </div>
      )}

      {isSpecialist && (
        <>
          <hr />
          <h2 style={{ color: '#d97706' }}>Панель специалиста</h2>

          <div style={{
            padding: '10px',
            backgroundColor: '#fef3c7',
            borderRadius: '6px',
            marginBottom: '10px',
            fontSize: '12px',
            color: '#92400e',
            border: '1px solid #fcd34d'
          }}>
            Эти функции доступны только специалистам и позволяют пересчитывать модели на основе актуальных данных.
          </div>

          {adminMessage && (
            <div style={{
              padding: '8px',
              backgroundColor: adminMessage.includes('Успешно') ? '#d1fae5' : '#fee2e2',
              color: adminMessage.includes('Успешно') ? '#065f46' : '#991b1b',
              borderRadius: '4px',
              fontSize: '12px',
              marginBottom: '10px',
              border: `1px solid ${adminMessage.includes('Успешно') ? '#10b981' : '#fca5a5'}`
            }}>
              {adminMessage}
            </div>
          )}

          <button
            onClick={handleRecalculateRiskZones}
            disabled={adminLoading === 'risk'}
            style={{ backgroundColor: '#d97706' }}
          >
            {adminLoading === 'risk' ? 'Пересчёт...' : 'Пересчитать зоны риска'}
          </button>

          <button
            onClick={handleRecalculateCorridors}
            disabled={adminLoading === 'corridors'}
            style={{ backgroundColor: '#d97706' }}
          >
            {adminLoading === 'corridors' ? 'Пересчёт...' : 'Пересчитать коридоры'}
          </button>

          <button
            onClick={handleRecalculateTraffic}
            disabled={adminLoading === 'traffic'}
            style={{ backgroundColor: '#d97706' }}
          >
            {adminLoading === 'traffic' ? 'Пересчёт...' : 'Пересчитать трафик'}
          </button>

          <button
            onClick={handleLoadStatistics}
            disabled={adminLoading === 'stats'}
            style={{ backgroundColor: '#059669' }}
          >
            {adminLoading === 'stats' ? 'Загрузка...' : 'Статистика системы'}
          </button>

          {route && (
            <button
              onClick={handleExportRoute}
              style={{ backgroundColor: '#7c3aed' }}
            >
              Экспорт маршрута (JSON)
            </button>
          )}

          {systemStats && (
            <div className="result" style={{ marginTop: '10px', borderColor: '#059669' }}>
              <div className="stat" style={{ fontWeight: 'bold', color: '#059669' }}>Статистика системы:</div>
              <div className="stat">AIS-записей: <b>{systemStats.ais_records?.toLocaleString()}</b></div>
              <div className="stat">Зон риска: <b>{systemStats.risk_zones}</b></div>
              <div className="stat">Коридоров: <b>{systemStats.corridors}</b></div>
              <div className="stat">Точек трафика: <b>{systemStats.traffic_points}</b></div>
              <div className="stat">Пользователей: <b>{systemStats.users}</b></div>
              <div className="stat">Период: <b>{systemStats.date_range?.min}</b> — <b>{systemStats.date_range?.max}</b></div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Sidebar;