# MONETA.RU — Отраслевые решения: Маркетплейсы и площадки

> Источник: https://docs.moneta.ru/solutions/index.html  
> Раздел охватывает расширенную функциональность и специфические решения для бизнеса маркетплейсов и площадок.

---

## Содержание

1. [Обзор и типы схем подключения](#1-обзор-и-типы-схем-подключения)
2. [Регистрация ЮЛ и ИП](#2-регистрация-юл-и-ип)
   - [Личный кабинет маркетплейса](#личный-кабинет-маркетплейса)
   - [Email-уведомления](#email-уведомления)
   - [URL-уведомления при редактировании профиля продавца](#url-уведомления-при-редактировании-профиля-продавца)
3. [Регистрация самозанятых (MonetaNPD)](#3-регистрация-самозанятых-monetanpd)
4. [Платёжные запросы маркетплейса](#4-платёжные-запросы-маркетплейса)
   - [Безопасная сделка](#безопасная-сделка)

---

## 1. Обзор и типы схем подключения

Раздел «Маркетплейсам и площадкам» предоставляет API и инструменты для:
- Регистрации продавцов (ЮЛ/ИП и самозанятых) через API
- Приёма платежей от покупателей на транзитный счёт
- Распределения средств между продавцами (безопасная сделка, мультикорзина)
- Управления выплатами продавцам на банковские карты/реквизиты
- Получения уведомлений об изменениях профилей продавцов

### Проекты оферт и дополнительных соглашений

#### C2C без ЭСП с тарифом НКО

- **Проект дополнительного соглашения с Платформой по схеме C2C без ЭСП с тарифом НКО**
- Плательщик и Получатель — физические лица без электронных кошельков
- **Проект C2C оферты** — В Монете заводится один личный кабинет — Платформы

#### C2B без ЭСП с тарифом НКО

- **Проект дополнительного соглашения с Платформой по схеме C2B с тарифом НКО**
- Плательщики — физические лица без электронных кошельков. Получатели — Юридические лица или ИП
- **Проект C2B оферты** — В Монете заводится два личных кабинета Платформы: один для счёта Платформы, второй для Получателей Платформы

#### C2CB без ЭСП без тарифа НКО

- **Проект дополнительного соглашения с Платформой по схеме C2CB без ЭСП с тарифом НКО**
- Плательщики — физические лица без электронных кошельков. Получатели — Юридические лица, ИП и физические лица без электронных кошельков
- **Проект C2CB оферты** — В Монете заводится два личных кабинета Платформы: один для счёта Платформы, второй для Получателей Платформы

---

## 2. Регистрация ЮЛ и ИП

> Источник: https://docs.moneta.ru/solutions/marketplaces/registration/juridical-and-individual/

### Личный кабинет маркетплейса

> Источник: https://docs.moneta.ru/solutions/marketplaces/registration/juridical-and-individual/personal-account/

В личном кабинете (ЛК) находятся настройки и счета клиентов маркетплейсов.

Доступ к ЛК предоставляется после заключения [Договора об информационно-технологическом взаимодействии](https://docs.moneta.ru/_documents/marketplace-offer.pdf).

После регистрации на email маркетплейса направляется уведомление с описанием структуры личного кабинета.

В структуре ЛК маркетплейса 3 группы:

**Зарегистрированные клиенты** — группа, в которой Система МОНЕТА.РУ создает личный кабинет для клиентов маркетплейса — юридических лиц и индивидуальных предпринимателей (далее ЮЛ/ИП) при регистрации.

**Активные клиенты** — в этой группе находятся клиенты маркетплейса ЮЛ/ИП, для которых включен прием платежей.

Перевод в **Активные клиенты** из группы **Зарегистрированные клиенты** осуществляется после заполнения личного кабинета ЮЛ/ИП и выполнения требований по размещению информации о ЮЛ/ИП на сайте маркетплейса.

> Информация, обязательная для размещения на сайте и/или в мобильном приложении по каждому клиенту маркетплейса и примеры размещения: https://www.payanyway.ru/info/w/ru/public/w/partnership/howto/terms.html

После перевода в группу "Активные клиенты" для ЮЛ/ИП необходимо скачать заявление о присоединении к Договору и создать расширенный счёт, на котором будут учитываться платежи.

**Клиенты без заявления** — группа, в которой находятся ЮЛ/ИП, не приславшие заявление о присоединении к Договору в течение 30 дней с момента регистрации в Системе МОНЕТА.РУ, согласно п.2.5. [Договора о переводах без открытия счетов в системе МОНЕТА.РУ](https://docs.moneta.ru/_documents/b2b-offer.pdf).

После основных этапов подключения Система МОНЕТА.РУ направляет уведомления маркетплейсу: обязательные Email-уведомления и настраиваемые URL-уведомления.

Если маркетплейс обеспечивает **безопасную сделку или мультикорзину**, будет создан еще один личный кабинет, в котором будут находиться транзитный и комиссионный счета маркетплейса.

---

### Email-уведомления

> Источник: https://docs.moneta.ru/solutions/marketplaces/registration/juridical-and-individual/email-notifications/

Раздел в разработке.

---

### URL-уведомления при редактировании профиля продавца

> Источник: https://docs.moneta.ru/solutions/marketplaces/registration/juridical-and-individual/url-notifications/

Для настройки URL-уведомления необходимо отправить URL вашего обработчика на [mp@payanyway.ru](mailto:mp@payanyway.ru)

**URL-уведомления отправляются методом POST.**  
**Content-type:** `application/x-www-form-urlencoded`  
**Encoding:** `UTF-8`

На адрес вашего обработчика Система "МОНЕТА.РУ" будет направлять следующие уведомления:

#### `CREATE_UNIT` — Создание дочернего юнита

```
NOTIFICATION=CREATE_UNIT&ACTION=CREATE_UNIT&UNIT_ID=…&PARENT_ID=…&INN=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `EDIT_CONTRACT` — Изменение статуса договора

Статусы:
- `INACTIVE` — статус договора после регистрации в Системе "МОНЕТА.РУ"
- `ACTIVE` — статус договора после перевода юнита продавца из группы **Зарегистрированные клиенты** в **Рабочую группу**
- `RESTRICTED` — статус договора после перевода из **Рабочей группы** в **Клиенты без заявления**

```
NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_CONTRACT&UNIT_ID=…&CONTRACT_ID=…&OLD_STATUS=…&NEW_STATUS=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+CONTRACT_ID+OLD_STATUS+NEW_STATUS+ключ)
```

#### `CREATE_ACCOUNT` — Создание счетов

```
NOTIFICATION=PROFILE_UPDATE&ACTION=CREATE_ACCOUNT&UNIT_ID=…&ACCOUNT_ID=…&ACCOUNT_TYPE=…&ACCOUNT_CREDIT_EXTID=…&ACCOUNT_DEBIT_EXTID=…&ACCOUNT_NUMBER=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+ACCOUNT_ID+ACCOUNT_TYPE+ключ)
```

#### `SEND_AGREEMENT` — Продавцу сформировано Заявление о присоединении к Договору

```
NOTIFICATION=PROFILE_UPDATE&ACTION=SEND_AGREEMENT&UNIT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `EDIT_PROFILE` — Редактирование Основного профиля

```
NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_PROFILE&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `MOVE_UNIT` — Перенос юнита (PARENT_ID — новый родительский юнит)

```
NOTIFICATION=PROFILE_UPDATE&ACTION=MOVE_UNIT&UNIT_ID=…&PARENT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PARENT_ID+ключ)
```

#### `CREATE_BANK_ACCOUNT` — Создание банковских реквизитов

```
NOTIFICATION=PROFILE_UPDATE&ACTION=CREATE_BANK_ACCOUNT&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `EDIT_BANK_ACCOUNT` — Редактирование банковских реквизитов

```
NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_BANK_ACCOUNT&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `CREATE_LEGAL_INFO` — Создание юридических реквизитов

```
NOTIFICATION=PROFILE_UPDATE&ACTION=CREATE_LEGAL_INFO&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `EDIT_LEGAL_INFO` — Редактирование юридических реквизитов

```
NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_LEGAL_INFO&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `CREATE_DOCUMENT` — Создание документа

```
NOTIFICATION=PROFILE_UPDATE&ACTION=CREATE_DOCUMENT&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `EDIT_DOCUMENT` — Редактирование документа

```
NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_DOCUMENT&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `CREATE_FOUNDER` — Создание Учредителя (`PROFILE_ID` равен `OBJECT_ID`)

```
NOTIFICATION=PROFILE_UPDATE&ACTION=CREATE_FOUNDER&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `EDIT_FOUNDER` — Редактирование Учредителя (`PROFILE_ID` равен `OBJECT_ID`)

```
NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_FOUNDER&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)
```

#### `EDIT_PROFILE` — Обновление профиля

```
NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_PROFILE&UNIT_ID=…&UPDATE_DETAILS=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+UPDATE_DETAILS+ключ)
```

#### `CONDITION_REJECTED` — Продавец не прошёл проверку соответствия ПиУ

```
NOTIFICATION=PROFILE_UPDATE&ACTION=CONDITION_REJECTED&UNIT_ID=…&PAYEE_DETAILS=…&PAYER_DETAILS=…&SITE_DETAILS=…&PAYMENT_INFO_DETAILS=…&CORRECT_DATA_DETAILS=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+ключ)
```

#### `RECEIVED_AGREEMENT` — Получено заявление о присоединении к Договору

```
NOTIFICATION=PROFILE_UPDATE&ACTION=RECEIVED_AGREEMENT&UNIT_ID=…&PAYEE_DETAILS=…&PAYER_DETAILS=…&SITE_DETAILS=…&PAYMENT_INFO_DETAILS=…&CORRECT_DATA_DETAILS=…&MNT_SIGNATURE=…
```

#### Ответ на уведомление

На уведомление следует ответить `http-status=200` или строчкой: `SUCCESS`

Если адрес обработчика не может быть вызван по какой-либо причине, либо в ответе придёт не `SUCCESS`, то уведомление будет направлено повторно. Всего **8 раз в течении суток**, с увеличивающейся периодичностью: 12 минут, 24 минуты, 48 минут и т.д.

---

## 3. Регистрация самозанятых (MonetaNPD)

> Источник: https://docs.moneta.ru/solutions/marketplaces/registration/self-employed/

Если получатель платежа на сайте маркетплейса — физическое лицо в статусе **самозанятый**, маркетплейс может воспользоваться сервисом **MonetaNPD**.

Сервис позволяет:
- Принимать платежи в пользу самозанятого
- Регистрировать его доход в ФНС
- Отправлять чеки покупателям
- Выводить средства на банковские карты самозанятого

**Общий URL контроллера API:** https://my.payanyway.ru/backend/web/index.php?r=aisnalogapi

Все данные принимаются методом **POST**.

Для регистрации на сервисе MonetaNPD маркетплейсу необходимо направить заявку в произвольной форме на [marketplace@support.payanyway.ru](mailto:marketplace@support.payanyway.ru).

По итогам регистрации выдается:
- `security_key` — идентифицирует маркетплейс в контроллере API
- `secret_key` — для генерации подписи запроса

Маркетплейс регистрирует физическое лицо и создает ЭСП "МОНЕТА.РУ" на основе [Соглашения об использовании Электронного средства платежа "МОНЕТА.РУ"](https://moneta.ru/info/public/users/nko/monetaoffer.pdf).

> **Важно:** Маркетплейсу необходимо ознакомить своего клиента с текстом Соглашения **до регистрации** в Системе МОНЕТА.РУ.

---

## 4. Платёжные запросы маркетплейса

> Источник: https://docs.moneta.ru/solutions/marketplaces/payments/

В этом разделе представлены платежные запросы, которые помогут торговой площадке реализовать:

- **Безопасная сделка** — холдирование средств до получения товара
- **Мультикорзина** — оплата товаров разных продавцов одним платежом *(в разработке)*
- **Управление комиссией** — управление размером комиссии, взимаемой с продавца *(в разработке)*
- **Выплаты продавцу** — выплаты на банковскую карту продавца *(в разработке)*

---

### Безопасная сделка

> Источник: https://docs.moneta.ru/solutions/marketplaces/payments/secure/

Логику безопасной сделки, включая процедуру рассмотрения споров, маркетплейс реализует самостоятельно.

В Системе МОНЕТА.РУ безопасная сделка состоит из **двух этапов**, интервал между которыми обусловлен логикой безопасной сделки.

#### Этап 1 — Приём платежа

Первый этап — приём платежа, например, с банковской карты покупателя на **транзитный счёт маркетплейса** в Системе "МОНЕТА.РУ" (Создание базовой операции).

Принять платёж можно одним из способов, указанных в [документации платёжных запросов](https://docs.moneta.ru/payments/start/).

После проведения операции платежа Система "МОНЕТА.РУ" сообщит номер операции в параметре `MNT_OPERATION_ID` — этот номер операции маркетплейсу необходимо **запомнить и учитывать** у себя в системе.

#### Этап 2 — Перевод продавцу

Второй этап — перевод принятого платежа с транзитного счёта маркетплейса на **расширенный счёт продавца** в Системе "МОНЕТА.РУ".

> **Примечание:** Расширенный счёт в Системе "МОНЕТА.РУ" открывают только продавцы — индивидуальные предприниматели и юридические лица.

Для перевода используется запрос `PaymentRequest` через интерфейс [MONETA.MerchantAPI](https://moneta.ru/doc/MONETA.MerchantAPI.v2.ru.pdf):
- `payer` = НОМЕР_ТРАНЗИТНОГО_СЧЕТА_ПЛОЩАДКИ
- `payee` = НОМЕР_РАСШИРЕННОГО_СЧЕТА_ПРОДАВЦА

**Запрос (JSON/SOAP):**

```json
{
  "Envelope": {
    "Header": {
      "Security": {
        "UsernameToken": {
          "Username": "логин",
          "Password": "пароль"
        }
      }
    },
    "Body": {
      "PaymentRequest": {
        "payer": "НОМЕР ТРАНЗИТНОГО СЧЕТА ПЛОЩАДКИ",
        "payee": "НОМЕР РАСШИРЕННОГО СЧЕТА ПРОДАВЦА",
        "amount": "сумма",
        "clientTransaction": "внешний идентификатор транзакции",
        "operationInfo": {
          "attribute": [
            {
              "key": "PARENTID",
              "value": "12345678"
            }
          ]
        }
      }
    }
  }
}
```

> **Важно:** В атрибутах перевода необходимо указать номер базовой операции в поле `PARENTID` — это операция платежа на транзитный счёт торговой площадки.

**Ответ:**

```json
{
  "Envelope": {
    "Body": {
      "PaymentResponse": {
        "transaction": "номер операции в системе МОНЕТА.РУ",
        "dateTime": "2019-01-25T15:35:32.000+03:00",
        "status": "SUCCESS",
        "clientTransaction": "внешний идентификатор транзакции"
      }
    }
  }
}
```

**Пример на PHP (PHP SDK):**

```php
<?php
$sdkAppFileName = __DIR__ . "/../moneta-sdk-lib/autoload.php";
include_once($sdkAppFileName);

try {
    $monetaSdk = new \Moneta\MonetaSdk();
    $monetaSdk->checkMonetaServiceConnection();

    $request = new \Moneta\Types\PaymentRequest();
    $request->payer = '';           // номер транзитного счёта магазина/маркетплейса
    $request->payee = '';           // номер расширенного счёта организации/продавца
    $request->amount = '10.00';
    $request->clientTransaction = 'my-order-id-10_2';
    $request->paymentPassword = '*******************';

    $operation = new \Moneta\Types\OperationInfo();
    $attribute = new \Moneta\Types\KeyValueAttribute();
    $attribute->key = 'PARENTID';
    $attribute->value = '';         // номер базовой операции платежа
    $operation->addAttribute($attribute);
    $request->operationInfo = $operation;

    $result = $monetaSdk->monetaService->Payment($request);

    if (!$result['id']) {
        throw new Exception(print_r($result, true));
    }
    echo "Запрос обработан.";

} catch (Exception $e) {
    echo "Ошибка: " . $e->getMessage();
}
```

#### Перевод с расширенного счёта продавца на банковские реквизиты

Для вывода средств продавца на его банковские реквизиты используется запрос `PaymentRequest`:
- `payer` = НОМЕР_РАСШИРЕННОГО_СЧЕТА_ПРОДАВЦА
- `payee` = `5` (означает банковский перевод по реквизитам)

```json
{
  "Envelope": {
    "Header": {
      "Security": {
        "UsernameToken": {
          "Username": "Username",
          "Password": "Password"
        }
      }
    },
    "Body": {
      "PaymentRequest": {
        "payer": "НОМЕР РАСШИРЕННОГО СЧЕТА ПРОДАВЦА",
        "payee": 5,
        "amount": 10,
        "clientTransaction": "Внешний номер операции",
        "paymentPassword": 12345,
        "isPayerAmount": true,
        "operationInfo": {
          "attribute": [
            {
              "key": "WIREPAYMENTPURPOSE",
              "value": "Перечисление суммы переводов денежных средств по Договору № ___ от DD.MM.YYYY. НДС не облагается."
            }
          ]
        }
      }
    }
  }
}
```

**Пример на PHP:**

```php
<?php
$sdkAppFileName = __DIR__ . "/../moneta-sdk-lib/autoload.php";
include_once($sdkAppFileName);

try {
    $monetaSdk = new \Moneta\MonetaSdk();
    $monetaSdk->checkMonetaServiceConnection();

    $request = new \Moneta\Types\PaymentRequest();
    $request->payer = '';           // номер расширенного счёта организации/продавца
    $request->payee = '5';          // 5 — банковский перевод по реквизитам
    $request->amount = '10.00';
    $request->clientTransaction = 'my-order-id-10_3';
    $request->paymentPassword = '***********';
    $request->isPayerAmount = true;
    $request->description = 'Перечисление на банковские реквизиты организации(продавца)';

    $result = $monetaSdk->monetaService->Payment($request);

    if (!$result['id']) {
        throw new Exception(print_r($result, true));
    }
    echo "Запрос обработан.";

} catch (Exception $e) {
    echo "Ошибка: " . $e->getMessage();
}
```

> **Примечание:** Интерфейс MONETA.MerchantAPI представляет собой Web-сервис, описанный по спецификации WSDL, использующий протокол SOAP для передачи информации.

---

## Полезные ссылки

| Ресурс | URL |
|--------|-----|
| Документация маркетплейсов | https://docs.moneta.ru/solutions/marketplaces/ |
| Договор об IT-взаимодействии | https://docs.moneta.ru/_documents/marketplace-offer.pdf |
| Договор о переводах без открытия счетов (B2B оферта) | https://docs.moneta.ru/_documents/b2b-offer.pdf |
| Соглашение ЭСП МОНЕТА.РУ (для самозанятых) | https://moneta.ru/info/public/users/nko/monetaoffer.pdf |
| MONETA.MerchantAPI (SOAP/WSDL) | https://moneta.ru/doc/MONETA.MerchantAPI.v2.ru.pdf |
| API контроллер MonetaNPD | https://my.payanyway.ru/backend/web/index.php?r=aisnalogapi |
| Информация для сайта маркетплейса | https://www.payanyway.ru/info/w/ru/public/w/partnership/howto/terms.html |
| Контакт поддержки маркетплейсов | marketplace@support.payanyway.ru |
| Настройка URL-уведомлений | mp@payanyway.ru |
