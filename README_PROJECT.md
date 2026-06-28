# Проект интеллектуальной морской маршрутизации

Система для планирования маршрутов морских судов с учётом ретроспективных AIS-данных, погодных условий и зон риска.

## Быстрый запуск (без PostgreSQL-урезанная версия)

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   cd frontend-react
   npm install

2. Сгенерируйте синтетические данные и обучите ML-модели:
   ```bash
   *в отдельной консольке*
   cd backend
   python train.py
   python generate_current_vessels.py  # текущие суда (50 шт.)
   python generate_traffic.py          # плотность трафика (traffic_density.json)
   python generate_corridors.py        # морские коридоры (maritime_corridors.json)
ы
3. Запустите бэкенд:
   ```bash
   python -m uvicorn app.main:app --reload

4. Запустите фронтенд (в отдельном терминале):
   ```bash
   cd frontend-react
   npm start

5. Откройте http://localhost:3000 в браузере.




