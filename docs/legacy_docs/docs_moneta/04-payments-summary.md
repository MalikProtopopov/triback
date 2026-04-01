# Платёжные запросы — документация для backend‑разработчика

> Собрано на основе [документации docs.moneta.ru](https://docs.moneta.ru/payments/)

---

## Обзор

Раздел охватывает: приём платежей, уведомление об оплате, **холдирование**, **сохранение карты**, **рекуррентные платежи**.

---

## Холдирование (двухстадийная оплата)

Сумма резервируется на карте, затем — подтверждение или отмена.

### Схема

1. Создать инвойс (`InvoiceRequest`) с параметром `AUTHORIZEONLY = "1"`.
2. Сохранить `transaction` (номер операции) из ответа.
3. Перенаправить покупателя на платёжную форму по ссылке с `operationId`.
4. После 3D-Secure покупатель попадает на InProgressURL.
5. Монета отправляет URL-уведомление на адрес из «Вызвать URL при авторизации средств».
6. Деньги авторизованы на карте (до 7 дней).

### Подтверждение

- Вручную в ЛК или через API `ConfirmTransactionRequest`.
- Сумма подтверждения — не больше суммы холда.
- После подтверждения — уведомление на PayURL.

### Отмена

Вручную в ЛК или через API `CancelTransactionRequest`.

---

## Сохранение карты

Сохранение токена, чтобы покупатель не вводил карту повторно.

**Способы:**
- Параметр `MNT_SUBSCRIBER_ID` платёжной формы.
- Атрибут `PAYMENTTOKEN` в MerchantAPI.

Способы взаимоисключающие, зависят от настроек счёта. По умолчанию — MNT_SUBSCRIBER_ID.

---

## Рекуррентные платежи

Списания с карты по токену, созданному при привязке карты через `PAYMENTTOKEN`.

**Оплата:** метод `PaymentRequest` с атрибутом `PAYMENTTOKEN` (значение — рекуррентный токен). Карточные данные не передаются.

---

## Локальные файлы

- [scraped_docs/payments/payments.md](scraped_docs/payments/payments.md)
- [scraped_docs/payments/start.md](scraped_docs/payments/start.md)
- [scraped_docs/payments/payment-notification.md](scraped_docs/payments/payment-notification.md)
- [scraped_docs/payments/with-hold.md](scraped_docs/payments/with-hold.md)
- [scraped_docs/payments/card-saving.md](scraped_docs/payments/card-saving.md)
- [scraped_docs/payments/recurrent.md](scraped_docs/payments/recurrent.md)
