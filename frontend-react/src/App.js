import React, { useState, useRef } from 'react';
import MapComponent from './components/MapComponent';
import Sidebar from './components/Sidebar';
import './App.css';

function App() {
  const [startPoint, setStartPoint] = useState(null);
  const [endPoint, setEndPoint] = useState(null);
  const [waypoints, setWaypoints] = useState([]);
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [focusPoint, setFocusPoint] = useState(null);
  const [heatmapSource, setHeatmapSource] = useState('retrospective');
  const abortControllerRef = useRef(null);

  const fetchRoute = async (params) => {
    if (!startPoint || !endPoint) {
      setError('Укажите точки старта и финиша на карте');
      return;
    }
    // Отменяем предыдущий запрос, если он есть
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setLoading(true);
    setError(null);
    setAnalysis(null);
    setRoute(null);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortController.signal,
        body: JSON.stringify({
          start: { lat: startPoint.lat, lon: startPoint.lng },
          end: { lat: endPoint.lat, lon: endPoint.lng },
          waypoints: waypoints.map(wp => ({ lat: wp.lat, lon: wp.lng })),
          vessel_type: params.vesselType,
          optimization: params.optimization,
          wind_speed: params.wind_speed,
          wave_height: params.wave_height,
          season: params.season
        })
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      if (data.segments) {
        setRoute(data);
        analyzeRoute(data.segments, params.vesselType);
      } else {
        setError('Маршрут не найден');
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Запрос отменён');
        setError('Построение маршрута отменено');
      } else {
        console.error('Ошибка fetch:', err);
        setError('Ошибка при запросе маршрута: ' + err.message);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const cancelRoute = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const analyzeRoute = async (segments, vesselType) => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/analyze_route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segments, vessel_type: vesselType })
      });
      const result = await response.json();
      setAnalysis(result);
    } catch (err) {
      console.error('Ошибка анализа маршрута:', err);
    }
  };

  const clearRoute = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setRoute(null);
    setStartPoint(null);
    setEndPoint(null);
    setWaypoints([]);
    setError(null);
    setAnalysis(null);
    setFocusPoint(null);
  };

  const showSituationOnMap = (lat, lon, description) => {
    setFocusPoint({ lat, lon, description });
  };

  return (
    <div className="app">
      <MapComponent
        startPoint={startPoint}
        endPoint={endPoint}
        waypoints={waypoints}
        setStartPoint={setStartPoint}
        setEndPoint={setEndPoint}
        setWaypoints={setWaypoints}
        route={route}
        focusPoint={focusPoint}
        onClearFocus={() => setFocusPoint(null)}
        heatmapSource={heatmapSource}
      />
      <Sidebar
        onRouteRequest={fetchRoute}
        onCancelRoute={cancelRoute}
        loading={loading}
        error={error}
        route={route}
        analysis={analysis}
        onClear={clearRoute}
        onShowSituation={showSituationOnMap}
        onHeatmapSourceChange={setHeatmapSource}
      />
    </div>
  );
}

export default App;
