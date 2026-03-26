# Задолженности: бэклог фазы 3 (автоматика, исключение, эскалация)

Следующие пункты из продуктового ТЗ **не реализованы** в бэкенде (или только заглушки). Использовать как отдельные задачи при готовности продуктовых правил.

## Автонакопление

- Реализация `arrears_auto_accrual_job`: создание `MembershipArrear` с `source=automatic` после дедлайна года `Y` (настройка `membership_payment_deadline_rule`).
- Идемпотентность: не дублировать открытый долг за тот же `year`; приоритет ручной записи за тот же год.
- Опционально поле `auto_rule_version` в модели для отладки.

## Эскалация и уведомления

- Telegram (и при необходимости email) при создании автодолга, втором пропуске, пороге исключения — см. план §12.
- Задачи в `email_tasks` / `telegram_tasks`, вызовы из job или `NotificationService`.

## Исключение и возврат

- Автоматическая установка `membership_excluded_at` после N последовательных неоплаченных лет (порог N — продукт).
- Снятие из Telegram канала по аналогии с `deactivate_expired_subscriptions`.
- Сценарий «возврат после исключения»: жёсткая очередь оплаты (вступительный + год + открытые arrears) в `determine_product_type` / `POST /subscriptions/pay` — согласовать с продуктом.

## API / UX (опционально)

- `consecutive_missed_years` в `GET /subscriptions/status`, если появится канонический счётчик в БД.

## Код-ориентиры

- Заглушка: `backend/app/tasks/scheduler.py` — `arrears_auto_accrual_job`.
- Поле профиля: `DoctorProfile.membership_excluded_at`.
