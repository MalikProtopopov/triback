В обычном режиме работы MONETA.Assistant пользователь может:

- Выбрать платежную систему для оплаты заказа.
- Указать необходимые параметры этой платежной системы.
- Увидеть страницу с деталями операции.
- После этого он попадает непосредственно на страницу выбранной платежной системы.


Например, пользователь выбирает платежную систему WebMoney, затем выбирает в качестве источника оплаты WebMoney WMR, затем видит детали операции, и только после этого попадает на сайт «WebMoney».

MONETA.Assistant позволяет в автоматическом режиме выбрать необходимую платежную систему, заполнить параметры этой платежной системы и перейти на сайт выбранной платежной системы.

Для этого необходимо заполнить дополнительные параметры запроса на оплату заказа.

## Дополнительные параметры запроса на оплату
followupПройти весь MONETA.Assistant с предустановленными значениями. Для этого необходимо выбрать платежную систему и заполнить параметры платежной системы (если они есть).
Возможные значения:

- `true` - Использовать дополнительные параметры, чтобы пропустить шаги MONETA.Assistant.
- `false` - Пользователь сам заполняет формы MONETA.Assistant.


Значение по умолчанию: `false`.
javascriptEnabledПризнак возможности использовать javascript для автоматической обработки форм (`true` или `false`). Если будет передано значение `true`, а на самом деле у пользователя javascript выключен, то пользователь увидит пустую страницу.
Важно передавать действительное значение – «включен» или «выключен» javascript в браузере пользователя. Используется совместно с параметром `followup`.paymentSystem.accountIdНомер счета платежной системы. Например, тип кошелька WebMoney, 2 – WMR, 3 – WMZ, 4 – WME.
## Примеры запросов на оплату

### Пример 1

Пример формы для оплаты заказа «FF790ABCD» в магазине «MAGAZIN.RU» (номер счета 00000001) на сумму 120.25 рублей с автоматической обработкой диалогов. Оплата будет производиться через систему WebMoney, средства будут списаны с WMR кошелька. Пользователь будет перенаправлен на страницу оплаты системы WebMoney.


```
<form method="post" action="https://moneta.ru/assistant.htm">
 <input type="hidden" name="MNT_ID" value="00000001">
 <input type="hidden" name="MNT_TRANSACTION_ID" value="FF790ABCD">
 <input type="hidden" name="MNT_CURRENCY_CODE" value="RUB">
 <input type="hidden" name="MNT_AMOUNT" value="120.25">
 <input type="hidden" name="paymentSystem.accountId" value="2">
 <input type="hidden" name="javascriptEnabled" value="true">
 <input type="hidden" name="followup" value="true">
 <input type="submit" value="Pay with Webmoney WMR">
</form>
```


Если в браузере пользователя выключен javascript и в MONETA.Assistant придет параметр `javascriptEnabled = false`, то пользователь попадет на последний шаг MONETA.Assistant – просмотр деталей операции. Для перехода на сайт системы WebMoney пользователь должен нажать кнопку `Продолжить`.

### Пример 2

Пример формы для оплаты заказа «FF790ABCD» в магазине «MAGAZIN.RU» (номер счета 00000001) на сумму 120.25 рублей с автоматической обработкой диалогов. Оплата будет производиться через систему Яндекс.Деньги.


```
<form method="post" action="https://moneta.ru/assistant.htm">
 <input type="hidden" name="MNT_ID" value="00000001">
 <input type="hidden" name="MNT_TRANSACTION_ID" value="FF790ABCD">
 <input type="hidden" name="MNT_CURRENCY_CODE" value="RUB">
 <input type="hidden" name="MNT_AMOUNT" value="120.25">
 <input type="hidden" name="followup" value="true">
 <input type="submit" value="Pay with Yandex.Money">
</form>
```