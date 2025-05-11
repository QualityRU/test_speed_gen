# FastAPI + SSE + ChatGPT для обработки изображений

Этот проект использует FastAPI для создания API, который принимает изображение блюда, обрабатывает его с помощью ChatGPT с заданным промптом и возвращает информацию о количестве калорий в блюде. Также в процессе работы замеряется время, которое уходит на обработку изображения через ChatGPT, и выводится результат в виде таблицы.

### Требования
- Python >= 3.7
- FastAPI
- Uvicorn
- OpenAI 
- aiohttp 
- PIL 

## Установка

1. Клонируйте репозиторий:
```
git clone https://github.com/QualityRU/test_speed_gen.git
cd test_speed_gen
```
2. Создайте виртуальное окружение:
```
python -m venv venv
source venv/bin/activate
```
3. Установите зависимости:
```
pip install -r req.txt
```
4. Запуск сервера
```
uvicorn main:app --reload
```
5. Запуск фронта
```
python3 -m http.server 8001
```