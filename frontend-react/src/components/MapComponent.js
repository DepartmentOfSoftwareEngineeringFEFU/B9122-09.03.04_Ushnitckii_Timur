import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const MapComponent = ({ 
  startPoint, endPoint, waypoints, 
  setStartPoint, setEndPoint, setWaypoints, 
  route, focusPoint, onClearFocus,
  heatmapSource, 
}) => {
  const mapRef = useRef(null);
  const markersRef = useRef({ start: null, end: null, waypoints: [], currentVessels: [] });
  const routeLayerRef = useRef(null);
  const heatLayerRef = useRef(null);
  const landLayerRef = useRef(null);
  const focusMarkerRef = useRef(null);
  const [heatmapData, setHeatmapData] = useState({ points: [] });

  const loadHeatmap = async () => {
    const url = heatmapSource === 'retrospective' 
      ? 'http://127.0.0.1:8000/api/heatmap_data' 
      : 'http://127.0.0.1:8000/api/current_heatmap_data';
    try {
      const response = await fetch(url);
      const data = await response.json();
      setHeatmapData(data);
    } catch (err) {
      console.error('Ошибка загрузки тепловой карты:', err);
    }
  };

  useEffect(() => {
    if (!mapRef.current) return;
    if (heatLayerRef.current) mapRef.current.removeLayer(heatLayerRef.current);
    if (heatmapData.points && heatmapData.points.length) {
      const points = heatmapData.points.map(p => [p[0], p[1], p[2]]);
      heatLayerRef.current = L.heatLayer(points, {
        radius: 15,
        blur: 10,
        maxZoom: 10,
        minOpacity: 0.3,
        gradient: { 0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1: 'red' }
      }).addTo(mapRef.current);
    }
  }, [heatmapData]);

  useEffect(() => {
    if (!mapRef.current) {
      mapRef.current = L.map('map', { attributionControl: false }).setView([55.0, 150.0], 5);
      L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: ''
      }).addTo(mapRef.current);
    }

    fetch('http://127.0.0.1:8000/api/land.geojson')
      .then(response => response.json())
      .then(data => {
        if (landLayerRef.current) mapRef.current.removeLayer(landLayerRef.current);
        landLayerRef.current = L.geoJSON(data, {
          style: { color: '#555', weight: 1, fillColor: '#8B5A2B', fillOpacity: 0.5 },
          onEachFeature: (feature, layer) => layer.bindPopup('Суша')
        }).addTo(mapRef.current);
      })
      .catch(err => console.error('Ошибка загрузки береговой линии:', err));

    const loadCurrentVessels = () => {
      fetch('http://127.0.0.1:8000/api/current_vessels')
        .then(response => response.json())
        .then(data => {
          markersRef.current.currentVessels.forEach(m => mapRef.current.removeLayer(m));
          markersRef.current.currentVessels = [];
          data.vessels.forEach(vessel => {
            const popup = `<b>${vessel.name}</b><br/>Тип: ${vessel.vessel_type}<br/>Скорость: ${vessel.sog} узлов<br/>Курс: ${vessel.cog.toFixed(0)}°<br/>Время: ${new Date(vessel.timestamp).toLocaleString()}`;
            const marker = L.marker([vessel.latitude, vessel.longitude], {
              icon: L.divIcon({ className: 'vessel-marker', html: '🚢', iconSize: [20, 20] })
            }).addTo(mapRef.current).bindPopup(popup);
            markersRef.current.currentVessels.push(marker);
          });
        })
        .catch(err => console.error('Ошибка загрузки текущих судов:', err));
    };
    loadCurrentVessels();
    const interval = setInterval(loadCurrentVessels, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    loadHeatmap();
  }, [heatmapSource]);

  useEffect(() => {
    if (!mapRef.current) return;
    const handleMapClick = (e) => {
      if (!startPoint) setStartPoint(e.latlng);
      else if (!endPoint) setEndPoint(e.latlng);
      else setWaypoints(prev => [...prev, e.latlng]);
    };
    mapRef.current.on('click', handleMapClick);
    return () => mapRef.current?.off('click', handleMapClick);
  }, [startPoint, endPoint, setStartPoint, setEndPoint, setWaypoints]);

  useEffect(() => {
    if (!mapRef.current) return;
    if (focusPoint) {
      if (focusMarkerRef.current) mapRef.current.removeLayer(focusMarkerRef.current);
      focusMarkerRef.current = L.marker([focusPoint.lat, focusPoint.lon], {
        icon: L.divIcon({ className: 'focus-marker', html: '📍', iconSize: [20, 20] })
      }).addTo(mapRef.current).bindPopup(focusPoint.description || 'Историческая ситуация').openPopup();
      mapRef.current.setView([focusPoint.lat, focusPoint.lon], 10);
    } else {
      if (focusMarkerRef.current) mapRef.current.removeLayer(focusMarkerRef.current);
      focusMarkerRef.current = null;
    }
  }, [focusPoint]);

  useEffect(() => {
    if (!mapRef.current) return;
    if (markersRef.current.start) mapRef.current.removeLayer(markersRef.current.start);
    if (startPoint) {
      markersRef.current.start = L.marker(startPoint, { draggable: true }).addTo(mapRef.current).bindPopup('Старт').openPopup();
      markersRef.current.start.on('dragend', (e) => setStartPoint(e.target.getLatLng()));
    } else markersRef.current.start = null;
    if (markersRef.current.end) mapRef.current.removeLayer(markersRef.current.end);
    if (endPoint) {
      markersRef.current.end = L.marker(endPoint, { draggable: true }).addTo(mapRef.current).bindPopup('Финиш');
      markersRef.current.end.on('dragend', (e) => setEndPoint(e.target.getLatLng()));
    } else markersRef.current.end = null;
    markersRef.current.waypoints.forEach(m => mapRef.current.removeLayer(m));
    markersRef.current.waypoints = [];
    waypoints.forEach((wp, idx) => {
      const m = L.marker(wp, { draggable: true, color: 'orange' }).addTo(mapRef.current).bindPopup(`Точка ${idx+1}`);
      m.on('dragend', (e) => {
        const newPos = e.target.getLatLng();
        setWaypoints(prev => prev.map((p, i) => i === idx ? newPos : p));
      });
      markersRef.current.waypoints.push(m);
    });
  }, [startPoint, endPoint, waypoints, setStartPoint, setEndPoint, setWaypoints]);

  // Отрисовка маршрута с отдельными тултипами для каждого сегмента
  useEffect(() => {
    if (!mapRef.current) return;
    if (routeLayerRef.current) {
      mapRef.current.removeLayer(routeLayerRef.current);
      routeLayerRef.current = null;
    }
    if (route && route.segments && route.segments.length) {
      const group = L.layerGroup();
      for (let i = 0; i < route.segments.length; i++) {
        const seg = route.segments[i];
        const startLatLng = [seg.start.lat, seg.start.lon];
        const endLatLng = [seg.end.lat, seg.end.lon];
        const line = L.polyline([startLatLng, endLatLng], { color: '#1e3a8a', weight: 5 });
        const midLat = (seg.start.lat + seg.end.lat) / 2;
        const midLon = (seg.start.lon + seg.end.lon) / 2;
        const tooltipContent = `
          Скорость: ${seg.recommended_speed_knots?.toFixed(1)} узлов<br/>
          Курс: ${seg.course_deg?.toFixed(0)}°<br/>
          Риск: ${seg.risk_level?.toFixed(2) || '0.00'}<br/>
          Расстояние: ${seg.distance_km?.toFixed(1)} км
        `;
        const tooltip = L.tooltip({ permanent: false, direction: 'center', offset: [0, -10] })
          .setContent(tooltipContent)
          .setLatLng([midLat, midLon]);
        line.bindTooltip(tooltip);
        group.addLayer(line);
      }
      group.addTo(mapRef.current);
      routeLayerRef.current = group;
      // Фокусируем карту на маршруте
      const bounds = L.latLngBounds(route.segments.flatMap(s => [[s.start.lat, s.start.lon], [s.end.lat, s.end.lon]]));
      mapRef.current.fitBounds(bounds);
    }
  }, [route]);

  return <div id="map" style={{ height: '100%', width: '100%' }} />;
};

export default MapComponent;
