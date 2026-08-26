# MyMoney — учёт доходов и расходов

Flet-клиент (Desktop) для управления личными финансами: доходы, расходы,
переводы между счетами, запланированные транзакции. Подключается к
[MySpaceServer](../MySpaceServer/) через REST API или работает автономно
с локальными JSON-файлами.

```
┌──────────────┐     REST (JWT)     ┌─────────────┐
│   MyMoney    │ ◄────────────────► │ MySpaceServer│
│  Flet-клиент │                    │  Django API  │
└──────────────┘                    └─────────────┘
        │
        │  fallback (офлайн)
        ▼
   JSON-файлы (resource.json, storage.json, ...)
```

## Возможности

- Управление счетами (кошельки, карты, вкладки) в разных валютах
- Транзакции: доходы, расходы, переводы между счетами
- Запланированные транзакции
- Конвертация валют через внутренний банк
- Два режима работы: серверный (REST API) и автономный (JSON-файлы)
- Авторизация по JWT-токену

## Структура

```
MyMoney/
├── main.py                  # Точка входа
├── core/                    # Доменная логика
│   ├── account.py           # Account (счёт с балансом)
│   ├── storage.py           # Storage (абстракция хранилища)
│   ├── transaction.py       # Transaction, Income, Expense, Transfer
│   ├── planned_transaction.py  # Запланированные транзакции
│   ├── resource.py          # Resource (валюта/ресурс)
│   ├── money.py             # Money (сумма + валюта)
│   └── exchange.py          # Bank (обмен валют)
├── database/                # Абстрактный слой БД
│   ├── abstract_base.py     # ABC: load/add/update/delete
│   ├── server_base.py       # REST-клиент (requests + JWT)
│   ├── json_base.py         # Локальные JSON-файлы
│   ├── sql_base.py          # SQLite
│   └── none_base.py         # Заглушка (офлайн)
├── dataview/                # Представления данных (DatabaseView)
├── pc_application/          # Flet Desktop UI
│   ├── application.py       # Главный оркестратор
│   ├── authorization_screen.py  # Экран логина
│   ├── storages_view.py     # Просмотр счетов
│   ├── transactions_view.py # Просмотр транзакций
│   ├── planned_transactions_screen.py  # Запланированные транзакции
│   └── navigation_bar.py    # Навигация
├── console_view/            # Консольный интерфейс
├── storage/                 # Локальное хранилище данных
├── tests/                   # Тесты (pytest)
├── requirements.txt
└── pyproject.toml           # Конфигурация ruff
```

## Доменная модель

- **Account** — счёт (кошелёк, карта) с балансом в определённой валюте
- **Resource** — тип ресурса (валюта): BTC, USD, RUB и др.
- **Transaction** — транзакция (доход/расход/перевод), привязана к счёту
- **PlannedTransaction** — запланированная транзакция
- **Money** — сумма + валюта (值对象)
- **Bank** — обменник валют

## Запуск (разработка)

```bash
cd MyMoney
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python main.py
```

### Режимы работы

Приложение автоматически определяет доступность сервера в локальной сети
(порт 8000). Если сервер найден — используется REST API с JWT-авторизацией.
Если сервер недоступен — данные берутся из локальных JSON-файлов.

## Тесты

```bash
python -m pytest
```

## Линтинг

```bash
ruff check .
ruff format .
```

## Зависимости

- Python 3.12+
- Flet 0.28.3
- requests (REST-клиент)
- pytest, mock (тесты)
- ruff (линтинг)

## Интеграция с MySpaceServer

При подключении к бэкенду приложение использует эндпоинты:

| Эндпоинт | Назначение |
|----------|-----------|
| `POST /api/token/` | Получение JWT-токена |
| `GET /api/resource_types` | Список типов ресурсов (валют) |
| `GET /api/storages` | Список счетов |
| `GET/POST /api/transactions` | Транзакции |
| `GET/POST /api/planned_transactions` | Запланированные транзакции |

> **Примечание**: API-маршруты MyMoney могут отличаться от текущей версии
> MySpaceServer (`/api/v1/...`). Планируется унификация API.
