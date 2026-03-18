## Добавление платёжной формы на сайт магазина


**Примечание: **Если вы уже используете интерфейс MONETA.Assistant, то подключение новой платёжной формы займёт совсем немного времени, если нет – изучите документацию, чтобы реализовать обработчики Check и Pay URL.


## Подключим скрипт

После того, как ваш магазин готов обрабатывать запросы от нашей системы, добавьте следующий скрипт на страницу, где будете принимать платежи от клиентов:


```
<script type="text/javascript" src="https://payanyway.ru/assistant-builder"></script>
```


**Примечание: **Исходники скрипта доступны на Github.


## Определим параметры платежа

Теперь на этой же странице нужно подготовить параметры для платёжной формы:


```
<script type="text/javascript">
 let options = {
 account: 32691195,
 amount: 12.34,
 transactionId: '1234567890-abcdef'
 };

 // ...

</script>
```


В этом примере параметров всего три, но может быть и больше – вот они все:
accountНомер вашего бизнес-счёта.amountСумма платежа.transactionIdНомер заказа в магазине.operationIdID операции в Монете.descriptionОписание заказа.signatureПодпись запроса.subscriberIdID клиента в магазине.testModeПризнак тестового платежа.
Значения:
- `0` – платёж настоящий *(по умолчанию)*
- `1` – платёж тестовый

amountЯзык интерфейса. Значения:
- `ru` – русский *(по умолчанию)*
- `en` – английский

themeЦветовая тема интерфейса. Значения:
- `light` – светлая *(по умолчанию)*
- `dark` – тёмная

customParamsУкажите любые другие параметры, если необходимо. Например:

```
customParams: {
 param1: "value1",
 param2: "value2"
}
```


Все параметры из блока `customParams` будут присутствовать в запросах на Check и Pay URL.

## Отрисуем платёжную форму

После того, как все параметры платёжной формы определены – отрисуем её:


```
let assistant = new Assistant.Builder();
assistant.build(options, 'payment-form');
```


Обратите внимание на второй параметр в функции `build`. Это `id` контейнера, в котором будет отрисована платёжная форма. В данном примере нам предварительно нужно было создать следующий html-элемент и разместить его на странице:


```
<div id="payment-form"></div>
```


Если не указывать второй параметр в функции `build` – платёжная форма будет отрисована в модальном окне поверх всей страницы.


**Примечание: **Платёжная форма в модальном окне всегда имеет светлую цветовую тему. Наши дизайнеры небезосновательно считают, что так лучше.


## Добавим обработчики

И ещё один момент – после успешной оплаты или в случае ошибки (а иногда – во время обработки платежа) бывает необходимо совершить какие-либо действия: уйти на другую страницу и так далее. Для этого можно добавить обработчики:


```
// платёж прошёл успешно
assistant.setOnSuccessCallback(function(operationId, transactionId) {
 // здесь можно сделать что угодно – например,
 // перенаправить на другую страницу
 location.replace("https://domain.domain");
});

// платёж не прошёл
assistant.setOnFailCallback(function(operationId, transactionId) {
 // действия по обработке ошибок
});

// платёж обрабатывается
assistant.setOnInProgressCallback(function(operationId, transactionId) {
 // действия по обработке промежуточного статуса операции
});
```


Здесь:

- `operationId` – номер операции в Монете
- `transactionId` – номер заказа в магазине


**Примечание: **Если в настройках счёта задан `InProgress URL` – переход по нему произойдёт автоматически.


## Код целиком


```
<div id="payment-form"></div>

<script type="text/javascript" src="https://payanyway.ru/assistant-builder"></script>

<script type="text/javascript">
 let options = {
 account: 32691195,
 amount: 12.34,
 transactionId: '1234567890-abcdef'
 };

 let assistant = new Assistant.Builder();

 // платёж прошёл успешно
 assistant.setOnSuccessCallback(function(operationId, transactionId) {
 // здесь можно сделать что угодно – например,
 // перенаправить на другую страницу
 location.replace("https://domain.domain");
 });

 // платёж не прошёл
 assistant.setOnFailCallback(function(operationId, transactionId) {
 // действия по обработке ошибок
 });

 // платёж обрабатывается
 assistant.setOnInProgressCallback(function(operationId, transactionId) {
 // действия по обработке промежуточного статуса операции
 });

 assistant.build(options, 'payment-form');
</script>
```