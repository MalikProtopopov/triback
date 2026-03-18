# Решения 54-ФЗ — документация для backend‑разработчика

> Собрано на основе [документации docs.moneta.ru](https://docs.moneta.ru/54-fz/)

---

## Обзор

Согласно 54-ФЗ при оплате товаров, работ или услуг необходимо формировать фискальный документ и отправлять его в ФНС через онлайн-кассу.

**Варианты формирования чека:**
- В ККТ платежного агрегатора ООО «ПЭЙ ЭНИ ВЭЙ»
- В ККТ маркетплейса
- В ККТ продавца (клиента маркетплейса)

---

## Интеграционный модуль

Сервис формирует запросы в онлайн-кассу. Данные о покупателе и номенклатуре получает от интернет-магазина в формате из документации Assistant54FZ.pdf.

### Настройки счёта

В Pay URL расширенного счёта указать:
```
https://kassa.payanyway.ru/index.php?do=invoicepayurl
```

В настройках kassa.payanyway.ru — Pay URL вашего магазина.

### Авторизация

Логин и пароль PayAnyWay, номер расширенного счёта — на [странице входа](https://kassa.payanyway.ru/index.php?show=userlogin).

### Поддерживаемые онлайн-кассы

Модуль Касса, АТОЛ онлайн (API v4), Бизнес.ру (API v4), Чек-онлайн, Бухсофт, Orange data, КОМТЕТ Касса, Дримкас, Счётмаш, Kit Online, E-COM Kassa, Nanokassa, Ferma, 1С-Рарус, ИнитПро касса, CloudKassir, Эвотор. i-Retail — без ФФД 1.05.

---

## ККТ PayAnyWay — API

### Создание инвойса

**Endpoint:** `https://bpa.payanyway.ru/api/invoice?key=***` (POST, JSON)

**Параметры:**
- `signature` — подпись
- `paymentAmount` — сумма
- `debitMntAccount`, `creditMntAccount` — счета списания/пополнения
- `sourceTariffMultiplier` — комиссия с продавца
- `mntTransactionId` — ID транзакции
- `customerEmail`, `mntSubscriberId` — данные покупателя
- `storeCard` — сохранять карту (true/false)
- `inventory` — массив позиций

**Позиция (inventory):**
- `sellerAccount`, `sellerInn`, `sellerName`, `sellerPhone`
- `productName`, `productQuantity`, `productPrice`
- `productVatCode` — код НДС (например 1105)
- `po`, `pm` — тип объекта/способа оплаты (опц.)

**Ответ:** `{"operation": "***"}` — ID созданной операции.

### Оплата инвойса

Покупатель перенаправляется на платёжную форму по ссылке с `operationId`.

### Возврат средств

Метод возврата через API ККТ PayAnyWay — см. [документацию](https://docs.moneta.ru/54-fz/paw-receipt/refund/).

---

## Локальные файлы

- [scraped_docs/54-fz/54-fz.md](scraped_docs/54-fz/54-fz.md)
- [scraped_docs/54-fz/module.md](scraped_docs/54-fz/module.md)
- [scraped_docs/54-fz/paw-receipt_create-invoice.md](scraped_docs/54-fz/paw-receipt_create-invoice.md)
- [scraped_docs/54-fz/paw-receipt_pay-invoice.md](scraped_docs/54-fz/paw-receipt_pay-invoice.md)
- [scraped_docs/54-fz/paw-receipt_refund.md](scraped_docs/54-fz/paw-receipt_refund.md)
