import React, { useState } from 'react';
import './Sidebar.css';

const Sidebar = ({ onRouteRequest, onCancelRoute, loading, error, route, analysis, onClear, onShowSituation, onHeatmapSourceChange }) => {
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
      <div className="form-group">
        <label>Скорость ветра (м/с)</label>
        <input type="number" step="1" value={routeParams.wind_speed} onChange={(e) => setRouteParams({...routeParams, wind_speed: parseFloat(e.target.value)})} />
      </div>
      <div className="form-group">
        <label>Высота волны (м)</label>
        <input type="number" step="0.5" value={routeParams.wave_height} onChange={(e) => setRouteParams({...routeParams, wave_height: parseFloat(e.target.value)})} />
      </div>
      <div className="form-group">
        <label>Сезон</label>
        <select value={routeParams.season} onChange={(e) => setRouteParams({...routeParams, season: parseInt(e.target.value)})}>
          <option value="0">Весна</option>
          <option value="1">Лето</option>
          <option value="2">Осень</option>
          <option value="3">Зима</option>
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
    </div>
  );
};

export default Sidebar;
