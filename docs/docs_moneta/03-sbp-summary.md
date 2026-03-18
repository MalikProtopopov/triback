# СБП (Система быстрых платежей) — документация для backend‑разработчика

> Собрано на основе [документации docs.moneta.ru](https://docs.moneta.ru/sbp/)

---

## Обзор

СБП — переводы по номеру телефона, QR-коды, кассовые ссылки, выплаты B2C.

---

## Endpoints

| Среда | URL |
|-------|-----|
| Продакшн | https://service.moneta.ru/services |
| Продакшн (x509) | https://service.moneta.ru:8443/services/x509 |
| Demo | https://demo.moneta.ru/services |

**Запросы:** POST, `Content-type: application/json;charset=UTF-8`

---

## Протоколы

| Протокол | Описание |
|----------|----------|
| C2C Push / Me2Me Push | Переводы самому себе по инициативе отправителя |
| Me2Me Pull | Переводы самому себе по инициативе получателя |
| C2B QR | Оплата по статическому или динамическому QR (физлица → ЮЛ/ИП) |
| C2B многоразовые QR | Регистрация и использование многоразовых ссылок/QR |
| C2B InvoiceRequest | Счёт по кассовой ссылке или динамическому QR |
| C2B привязка счёта | Подписка, привязка без оплаты, оплата с привязкой |
| C2B refund | Возврат QR-платежей |
| B2C | Выплаты ЮЛ/ИП физлицам |

---

## WSDL

- https://moneta.ru/services-providers.wsdl
- https://service.moneta.ru/services.wsdl
- https://service.moneta.ru/services-frontend.wsdl

---

## Сервис Widget SBP/FPS

Схема взаимодействия, регистрация маркетплейса, установление доверия, аутентификация, встраивание в iframe, уведомления, пример PaymentRequest, история транзакций.

---

## Локальные файлы

- [scraped_docs/sbp/sbp.md](scraped_docs/sbp/sbp.md)
- [scraped_docs/sbp/fields.md](scraped_docs/sbp/fields.md)
- [scraped_docs/sbp/get-participants.md](scraped_docs/sbp/get-participants.md)
- [scraped_docs/sbp/c2c-me2me-push.md](scraped_docs/sbp/c2c-me2me-push.md)
- [scraped_docs/sbp/c2c-me2me-pull.md](scraped_docs/sbp/c2c-me2me-pull.md)
- [scraped_docs/sbp/c2b-qr.md](scraped_docs/sbp/c2b-qr.md)
- [scraped_docs/sbp/c2b-reusable-qr.md](scraped_docs/sbp/c2b-reusable-qr.md)
- [scraped_docs/sbp/c2b-invoice-for-link.md](scraped_docs/sbp/c2b-invoice-for-link.md)
- [scraped_docs/sbp/c2b-invoice-for-qr.md](scraped_docs/sbp/c2b-invoice-for-qr.md)
- [scraped_docs/sbp/c2b-subscription*.md](scraped_docs/sbp/)
- [scraped_docs/sbp/c2b-refund.md](scraped_docs/sbp/c2b-refund.md)
- [scraped_docs/sbp/b2c.md](scraped_docs/sbp/b2c.md)
- [scraped_docs/sbp/get-status.md](scraped_docs/sbp/get-status.md)
- [scraped_docs/sbp/sbp-fps_*.md](scraped_docs/sbp/)
