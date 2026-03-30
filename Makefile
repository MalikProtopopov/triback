.PHONY: dev dev-down dev-logs prod prod-down prod-logs migrate migration deploy restart-backend ssl-init ssl-renew backup worker

# ── Dev ──────────────────────────────────────────────────────────
dev:
	docker compose up -d --build

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f backend worker

# ── Prod ─────────────────────────────────────────────────────────
prod:
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f backend worker

# ── Database ─────────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

migrate-prod:
	docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# ── Deploy ───────────────────────────────────────────────────────
deploy:
	./scripts/deploy.sh

# Prod: только перезапуск контейнеров (на сервере, с .env.prod в корне)
restart-backend:
	./scripts/restart-backend.sh

# ── SSL ──────────────────────────────────────────────────────────
ssl-init:
	./scripts/init-ssl.sh

ssl-renew:
	docker compose -f docker-compose.prod.yml run --rm certbot renew --quiet
	docker compose -f docker-compose.prod.yml restart nginx

# ── Backup ───────────────────────────────────────────────────────
backup:
	./scripts/backup.sh

# ── Worker (standalone) ──────────────────────────────────────────
worker:
	docker compose exec worker taskiq worker app.tasks:broker

# ── Logs (individual) ────────────────────────────────────────────
logs:
	docker compose logs -f $(svc)
