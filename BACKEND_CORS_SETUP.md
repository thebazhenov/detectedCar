# Backend CORS Configuration

Ваш FastAPI бэкенд должен быть настроен для обработки CORS запросов от фронтенда.

## Решение 1: Правильная настройка CORS в FastAPI

### КРИТИЧЕСКИ ВАЖНО: Порядок имеет значение!

CORS middleware должен быть добавлен **ПЕРЕД** определением всех маршрутов. Вот правильный порядок:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Создаем приложение
app = FastAPI()

# ⚠️ ВАЖНО: CORS middleware ДОЛЖЕН быть добавлен ПЕРЕД маршрутами
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",  # На случай если используется другой порт
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["*"],
)

# Теперь определяем маршруты ПОСЛЕ middleware
@app.post("/auth", response_model=UserRead)
async def auth_user(payload: AuthRequest):
    async with UnitOfWork()() as uow:
        user = await uow.users.check_credentials(payload.email, payload.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return user
```

### Проверка что все правильно:

1. **Порядок**: CORS middleware добавлен ПЕРЕД маршрутами
2. **Origins**: Явно указаны origins (не используется `["*"]` с `allow_credentials=True`)
3. **Methods**: OPTIONS явно указан в списке методов
4. **Headers**: Content-Type явно указан в списке заголовков
5. **Перезапуск**: Сервер полностью перезапущен после изменений

### Отладка:

Добавьте логирование для проверки:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

@app.middleware("http")
async def log_requests(request, call_next):
    logging.info(f"{request.method} {request.url}")
    logging.info(f"Headers: {dict(request.headers)}")
    response = await call_next(request)
    logging.info(f"Response status: {response.status_code}")
    return response
```

## Решение 2: Использование Vite Proxy (Рекомендуется для разработки)

Если проблема с CORS сохраняется, можно использовать Vite proxy. Это обойдет проблему CORS, так как запросы будут идти через тот же порт.

### Шаг 1: Настройте Vite proxy

Обновите `vite.config.ts`:

```typescript
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  // ... остальная конфигурация
}));
```

### Шаг 2: Обновите API клиент

Измените базовый URL в `src/integrations/api/client.ts`:

```typescript
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
```

Теперь все запросы будут идти через `/api`, который проксируется на `http://localhost:8000`, и CORS не будет проблемой.

## Решение 3: Явная обработка OPTIONS запросов

Если ничего не помогает, добавьте явный обработчик OPTIONS:

```python
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:8080",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
        },
    )
```

Но это должно быть не нужно, если CORSMiddleware настроен правильно.

## Проверка

После применения изменений:

1. Полностью перезапустите FastAPI сервер
2. Попробуйте войти снова
3. OPTIONS запрос должен вернуть 200 OK, а не 400 Bad Request
4. Проверьте логи сервера - там должны быть запросы OPTIONS и POST

