# Документация проекта Trihoback

> Бэкенд платформы «Профессиональное общество трихологов».
> Стек: FastAPI + PostgreSQL + Redis + MinIO + Docker Compose.

---

## Для разработчика — начни здесь

| Документ | Что внутри |
|----------|------------|
| [DATABASE.md](DATABASE.md) | Все таблицы, поля, связи, constraints, жизненные циклы |
| [API.md](API.md) | Все эндпоинты (method, path, роль, описание) |
| [BUSINESS_LOGIC.md](BUSINESS_LOGIC.md) | Бизнес-процессы, FSM, ценообразование, задолженности, RBAC |
| [ENVIRONMENT.md](ENVIRONMENT.md) | Все переменные окружения с описанием |
| [FRONTEND_SERVER_DEPLOY.md](FRONTEND_SERVER_DEPLOY.md) | Деплой фронтенда (nginx, SSL, pm2) |

## Правила и стандарты кода

| Документ | Описание |
|----------|----------|
| [rules/BACKEND_RULES.md](rules/BACKEND_RULES.md) | Стек, структура, паттерны бэкенда |
| [rules/FRONTEND_RULES.md](rules/FRONTEND_RULES.md) | Стек, компоненты, паттерны фронтенда |
| [rules/CLAUDE_FRONTEND.md](rules/CLAUDE_FRONTEND.md) | Frontend: FSD, TailwindCSS v4, CSS variables |
| [rules/DEPLOY_RULES.md](rules/DEPLOY_RULES.md) | Docker Compose, nginx, SSL, Makefile |
| [rules/VIBECODING_WORKFLOW.md](rules/VIBECODING_WORKFLOW.md) | AI-assisted development workflow |

## Env-шаблон для production

| Документ | Описание |
|----------|----------|
| [env-production-trichologia.ru.template.md](env-production-trichologia.ru.template.md) | Полный шаблон .env.prod с пояснениями |

## Документы организации

| Документ | Описание |
|----------|----------|
| [company_docs/](company_docs/) | Устав, реквизиты, оферта, способы оплаты |

## Архив

| Папка | Описание |
|-------|----------|
| [legacy_docs/](legacy_docs/) | Устаревшие спецификации, changelogs, moneta docs, старые handoff'ы |

---

## Быстрый старт

```bash
# Dev
cp backend/.env.example backend/.env
make dev

# Prod
cp env.prod.example .env.prod
# заполнить секреты
make deploy
```

## Серверы

| Сервер | IP | Назначение |
|--------|-----|------------|
| Backend | 31.130.149.62 | API: api.trichologia.ru |
| Frontend | 147.45.146.38 | dev.trichologia.ru + admin.trichologia.ru |

## Тесты

```bash
cd backend
python -m pytest tests/ -v
```

Покрытие тестами: подписки, платежи, задолженности, сертификаты, RBAC, регистрация на мероприятия.
