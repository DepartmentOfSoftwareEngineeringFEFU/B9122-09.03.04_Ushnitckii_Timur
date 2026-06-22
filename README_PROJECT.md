# Проект интеллектуальной морской маршрутизации

## Быстрый запуск

1. Установите зависимости: `pip install -r requirements.txt`
2. Сгенерируйте данные и обучите модели: `python train.py`
3. Запустите API: `uvicorn app.main:app --reload`
4. Откройте `frontend/index.html` в браузере (или через live-server)

## Эндпоинты API

- `POST /api/route` – построить маршрут (start/end, vessel_type, optimization)
- `POST /api/similar` – поиск похожих ситуаций (risk_score, wind, wave, vessel_type, season)
- `GET /api/risk_zones` – получить зоны риска (JSON)

## Структура

- `app/synthetic_ais.py` – генерация 200k записей
- `app/meteo.py` – синтез погоды
- `app/risk_calculator.py` – вычисление risk_score
- `app/ml/` – DBSCAN и k-NN
- `app/router.py` – граф и A* (шаг сетки 10 км)
- `train.py` – полный пайплайн обучения
- `frontend/index.html` – карта Leaflet

## Примечания

- Для проверки суши требуется скачать Natural Earth coastline (опционально). Пока заглушка.
- Все данные синтетические, но архитектура готова к реальным CSV.