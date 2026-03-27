# Сервис kassa.payanyway.ru — описание взаимодействия

> Конвертация из `kassaspecification.pdf` (Manual kassa.payanyway.ru).  
> Связка с [MONETA.Assistant](https://www.moneta.ru/doc/MONETA.Assistant.ru.pdf) и Pay URL.

## Версии документа

| Версия | Дата       | Изменения |
|--------|------------|-----------|
| 2.1    | 22.05.2024 | — |
| 2.2    | 20.12.2024 | Работа с маркированным товаром |
| 2.3    | 25.12.2024 | Ввод кодов маркировки вручную через ЛК |
| 2.4    | 27.12.2024 | Ставки НДС 5% и 7% |
| 2.5    | 15.12.2025 | Ставка НДС 22% |

## Оглавление

1. [Подключение кассы](#1-подключение-кассы)
2. [Способы отправки данных в сервис](#2-способы-отправки-данных-в-сервис)
   - 2.1. [Адрес Pay URL](#21-адрес-pay-url)
   - 2.2. [API](#22-api)
3. [Отображение чеков](#3-отображение-чеков)
4. [Автоматизация чеков возврата](#4-автоматизация-чеков-возврата)
5. [Схема работы с двумя чеками](#5-схема-работы-с-двумя-чеками)
   - 5.1. [Передача марок вручную через ЛК](#51-передача-марок-вручную-через-лк)

---

## 1. Подключение кассы

- Зарегистрировать интернет-магазин для приёма платежей: [payanyway.ru](https://payanyway.ru).
- Приобрести ККМ (например МодульКасса) или арендовать кассу АТОЛ онлайн.
- Зарегистрировать ККМ в ФНС, заключить договор с ОФД.
- Авторизоваться в ЛК [kassa.payanyway.ru](https://kassa.payanyway.ru): логин и пароль PayAnyWay, номер бизнес-счёта; внести данные доступа к ККТ.

---

## 2. Способы отправки данных в сервис

### 2.1. Адрес Pay URL

**Условие:** интеграция с MONETA.RU через интерфейс **MONETA.Assistant** ([документ](https://www.moneta.ru/doc/MONETA.Assistant.ru.pdf)).

**Настройка:**

1. В **kassa.payanyway.ru** (основные настройки) в поле **«Pay URL интернет-магазина»** вставить значение поля **«Pay URL»** из ЛК PayAnyWay (настройки бизнес-счёта).
2. В **PayAnyWay** в поле **«Pay URL»** установить:  
   `https://kassa.payanyway.ru/index.php?do=invoicepayurl`

После этого данные о результате платежа сначала приходят в kassa.payanyway.ru; сервис **перенаправляет** запрос на Pay URL магазина. **Номенклатуру** для фискализации магазин возвращает **в ответе** на этот запрос.

**Бэкенд trihoback:** в поле «Pay URL интернет-магазина» в ЛК kassa укажите полный URL эндпоинта фискализации, например  
`https://<api-host>/api/v1/webhooks/moneta/kassa`  
(тот же публичный хост, что и у API; при необходимости см. `PUBLIC_API_URL`). Эндпоинт отдаёт XML с `INVENTORY`/`CLIENT` только если включено **`MONETA_KASSA_FISCAL_ENABLED=true`** и заданы **`MONETA_FISCAL_SELLER_INN`**, **`MONETA_FISCAL_SELLER_NAME`**, **`MONETA_FISCAL_SELLER_PHONE`**, **`MONETA_FISCAL_SELLER_ACCOUNT`** (опционально **`MONETA_FISCAL_SNO`**). Уведомление об оплате Moneta без фискального XML по-прежнему обрабатывается отдельно: **`/api/v1/webhooks/moneta`** (plain text `SUCCESS`/`FAIL`).

**Кастомные поля, зарезервированные kassa.payanyway.ru (на своём сайте не использовать):**

- `MNT_CUSTOM1`, `MNT_CUSTOM2`, `MNT_CUSTOM3`
- `MNT_CUSTOM10` … `MNT_CUSTOM19`

Если без них нельзя — фискализацию передавать через **API** (п. 2.2).

#### Ответ магазина

- Заголовок: **`Content-Type: application/xml`**
- Тело: XML с корнем `MNT_RESPONSE`.

Пример структуры:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<MNT_RESPONSE>
  <MNT_ID>********</MNT_ID>
  <MNT_TRANSACTION_ID>********</MNT_TRANSACTION_ID>
  <MNT_RESULT_CODE>200</MNT_RESULT_CODE>
  <MNT_SIGNATURE>********</MNT_SIGNATURE>
  <MNT_ATTRIBUTES>
    <ATTRIBUTE>
      <KEY>INVENTORY</KEY>
      <VALUE>[... JSON позиций ...]</VALUE>
    </ATTRIBUTE>
    <ATTRIBUTE>
      <KEY>CLIENT</KEY>
      <VALUE>[... JSON покупателя ...]</VALUE>
    </ATTRIBUTE>
    <ATTRIBUTE>
      <KEY>SNO</KEY>
      <VALUE>1</VALUE>
    </ATTRIBUTE>
    <ATTRIBUTE>
      <KEY>DELIVERY</KEY>
      <VALUE>12.52</VALUE>
    </ATTRIBUTE>
  </MNT_ATTRIBUTES>
</MNT_RESPONSE>
```

**Имена товаров/услуг в `INVENTORY`:** не должны содержать кавычки и прочие спецсимволы. Пример нормализации (PHP из документа):

```php
$positionName = trim(preg_replace("/&?[a-z0-9]+;/i", "", htmlspecialchars($positionName)));
```

#### Атрибуты XML-ответа

| Поле | Обяз. | Описание |
|------|-------|----------|
| `MNT_ID` | да | Номер расширенного счёта магазина; из входящего запроса на Pay URL |
| `MNT_TRANSACTION_ID` | да | Идентификатор заказа в магазине (до 255 символов); из запроса. Для **возврата** — префикс **`RETURN_`** (пример: `RETURN_52972360059455248073`) |
| `MNT_RESULT_CODE` | да | Успех: **`200`** |
| `MNT_SIGNATURE` | да | `md5(MNT_RESULT_CODE + MNT_ID + MNT_TRANSACTION_ID + код_проверки_целостности)` — код из параметров расширенного счёта в ЛК MONETA.RU |
| `INVENTORY` | да | JSON позиций (см. объект `inventPositions` в API) |
| `CLIENT` | да | JSON сведений о покупателе |
| `SNO` | нет | СНО: 1 ОСНО, 2 УСН доход, 3 УСН доход минус расход, 4 ЕНВД, 5 ЕСХН, 6 ПСН |
| `DELIVERY` | нет | Сумма доставки в рублях; не дублировать, если доставка уже в `INVENTORY` |

---

### 2.2. API

**Когда:** не используется MONETA.Assistant или своя учётная система для чеков.

- **Метод:** `POST`
- **URL:** `https://kassa.payanyway.ru/api/api.php?accountid=<MNT_ID>&group=receipt`
- **Заголовок:** `Content-Type: application/json; charset=utf-8`
- **Тело:** JSON

В документе приведён пример на PHP: очистка имён, массив позиций, клиент, при несовпадении суммы позиций с `MNT_AMOUNT` — пересчёт цен через коэффициент, формирование JSON:

- `operationId`, `checkoutDateTime`, `docNum`, `docType` (`SALE` / `SALE_RETURN`), `sno`, `inventPositions`, `moneyPositions`, `client`
- `signature` = `md5(docNum + checkoutDateTime + код_проверки_целостности)`

#### Поля чека (JSON)

| Поле | Тип | Обяз. | Описание |
|------|-----|-------|----------|
| `operationId` | string | да | `MNT_OPERATION_ID` |
| `checkoutDateTime` | string | да | `yyyy-mm-ddTHH:MM:SSP` (смещение пояса, напр. `+03:00` для Europe/Moscow) |
| `docNum` | string | да | = `MNT_TRANSACTION_ID` |
| `docType` | string | да | `SALE` или `SALE_RETURN` |
| `sno` | number | нет | 1–6 — система налогообложения |
| `inventPositions` | array | да | Позиции |
| `moneyPositions` | array | да | 1–10 записей оплаты |
| `client` | object | да | Покупатель |
| `signature` | string | да | см. выше |

#### Позиция (`inventPositions`)

Обязательные поля включают: `name` (до 128 символов), `price`, `quantity`, `vatTag`, `pm`, `po`, при необходимости `measure`, `idInternal`, `agent_info`, `supplier_info`, `markCode` (для маркировки — `gs1m` в Base64).

**`vatTag` (неполный перечень):** 1105 без НДС; 1104 — 0%; 1103 — 10%; 1107 — 10/110; 1102 — 20%; 1106 — 20/120; 1108 — 5%; 1109 — 7%; 1110 — 5/105; 1111 — 7/107; 1113 — 22%; 1114 — 22/122.

**`pm`:** full_prepayment, prepayment, advance, full_payment, partial_payment, credit, credit_payment и др.; авто по подстрокам в названии («аванс», «услуг», «рабо»).

**`po`:** commodity, excise, job, service, gambling_*, lottery_*, payment, agent_commission, award, another, property_right, non_operating, insurance_premium, sales_tax, resort_fee (ФФД) и др.

**`measure`:** unit, gram, kilogram, ton, centimeter, meter, литры, кубометры, кВт·ч, сутки, часы и др. (полный список в PDF).

**`moneyPositions`:** `paymentType` (card, prepaid, counter_provisioning, cash), `sum`.

**`client`:** обязательно заполнить хотя бы одно из `email` или `phone`; при обоих — электронный чек на email.

---

## 3. Отображение чеков

Чеки, статусы, взаимодействие с онлайн-кассой — в ЛК [kassa.payanyway.ru](https://kassa.payanyway.ru).

---

## 4. Автоматизация чеков возврата

Для автоматического чека при возврате в настройках счёта: действие **«Вызвать URL после списания средств»** =

`https://kassa.payanyway.ru/index.php?do=notifyrefund`

---

## 5. Схема работы с двумя чеками

ФНС рекомендует отдельно чек **предоплаты** и чек **отгрузки**.

- Если номенклатура передаётся **в ответе на Pay URL** при успешной оплате — взаимодействие с kassa одноразовое; на предоплату **коды маркировки не передаются** (товары ещё не определены).
- Второй чек (отгрузка), если не автоматизирован — создаётся в ЛК kassa.payanyway.ru.

Включить опцию **«Включить схему с двумя чеками (для CMS)»** в основных настройках; задать **«Примерное время до отгрузки товара, дней»** — по истечении автоматически формируется второй чек отгрузки.

Для маркированных товаров можно выставить время **«вручную»** и формировать чек отгрузки кнопкой в списке чеков.

Товары с маркировкой заносятся в справочник **«Номенклатура»** (раздел «Чеки»); наименования должны совпадать с чеком отгрузки; уникальные коды Data Matrix на единицу товара.

### 5.1. Передача марок вручную через ЛК

Наследование чека от первого; в строках ввод кода GS1 Data Matrix. Если количество > 1 — разбить на несколько строк с отдельными кодами. Сохранить и отправить на фискализацию.

---

## Все требования (чеклист)

### Организационные и учётные

| ID | Требование |
|----|------------|
| R1 | Зарегистрирован ИМ в PayAnyWay и принимаются платежи через payanyway.ru |
| R2 | Есть ККТ, регистрация в ФНС, договор с ОФД |
| R3 | Выполнен вход в kassa.payanyway.ru и привязаны данные ККТ |

### Pay URL + MONETA.Assistant

| ID | Требование |
|----|------------|
| R4 | В kassa в поле «Pay URL интернет-магазина» скопирован актуальный Pay URL из ЛК PayAnyWay |
| R5 | В PayAnyWay поле «Pay URL» заменено на `https://kassa.payanyway.ru/index.php?do=invoicepayurl` |
| R6 | Ответ на входящий запрос — только **XML**, заголовок **`Content-Type: application/xml`** |
| R7 | В XML: `MNT_RESULT_CODE = 200` при успехе |
| R8 | Подпись `MNT_SIGNATURE` вычисляется как `md5(MNT_RESULT_CODE + MNT_ID + MNT_TRANSACTION_ID + код_целостности)` |
| R9 | В `MNT_ATTRIBUTES` переданы **INVENTORY** и **CLIENT** (JSON в VALUE) |
| R10 | Для возврата к идентификатору транзакции добавлен префикс **`RETURN_`** |
| R11 | Наименования позиций в INVENTORY без кавычек и недопустимых спецсимволов (нормализация строк) |
| R12 | Поля **MNT_CUSTOM1, MNT_CUSTOM2, MNT_CUSTOM3, MNT_CUSTOM10–MNT_CUSTOM19** не используются под стороннюю логику; иначе — только API kassa |

### JSON API (альтернатива XML на Pay URL)

| ID | Требование |
|----|------------|
| R13 | Запрос `POST` на `https://kassa.payanyway.ru/api/api.php?accountid=<MNT_ID>&group=receipt` |
| R14 | Заголовок `Content-Type: application/json; charset=utf-8` |
| R15 | Подпись `signature = md5(docNum + checkoutDateTime + код_целостности)` |
| R16 | Заполнены обязательные поля чека: `operationId`, `checkoutDateTime`, `docNum`, `docType`, `inventPositions`, `moneyPositions`, `client`, `signature` |
| R17 | Суммы и количества в позициях соответствуют ограничениям документа (цена, quantity, сумма оплат) |

### Возвраты

| ID | Требование |
|----|------------|
| R18 | Для автоматических чеков возврата настроен URL `https://kassa.payanyway.ru/index.php?do=notifyrefund` как «вызов после списания» |

### Два чека и маркировка

| ID | Требование |
|----|------------|
| R19 | Учтена схема предоплата / отгрузка; КМ во втором чеке или через справочник ЛК / API |
| R20 | При необходимости включена опция двух чеков для CMS и заданы сроки или режим «вручную» для маркированных товаров |
| R21 | Номенклатура с КМ синхронизирована со справочником в ЛК (совпадение наименований) |

### НДС и ФФД

| ID | Требование |
|----|------------|
| R22 | Используются актуальные коды `vatTag`, включая ставки **5%, 7%, 22%** и расчётные ставки по документу версии 2.4–2.5 |
| R23 | Значения `po`, `measure`, агентские реквизиты соответствуют версии ФФД на кассе |

---

*Детальные таблицы enum и полные примеры PHP — в исходном файле `kassaspecification.pdf`.*
