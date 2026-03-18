Для выставления счёта на оплату используется метод `InvoiceRequest`. Счет (Invoice) выставляется Получателем (ЮЛ/ИП) для оплаты за товары или услуги.

Чтобы сформировать invoice для оплаты по QR, счёт получателя обязательно должен быть настроен для работы с СБП: этот способ должен быть активен для счёта в личном кабинете moneta.ru или payanyway.ru. Проверить это можно в личном кабинете moneta.ru: «Рабочий кабинет» → «Способы оплаты»; или в личном кабинете payanyway.ru: «Способы оплаты».

В поле `CUSTOMFIELD:QRTTL` можно передать период в минутах, в течение которого будет возможна оплата по платёжной ссылке (QR-коду). Минимальное значение — одна минута, максимальное значение – 129600 (90 дней в минутах). Если поле `CUSTOMFIELD:QRTTL` не передано, за период использования динамической платёжной ссылки берётся значение 4320 минут (три дня).

Ответом на `InvoiceRequest` будет `InvoiceResponse`, в котором содержится:

- `transactionId` - номер операции;
- `qrlink` - ссылка на графическое отображение QR;
- `qrpayload` - платёжная ссылка СБП, закодированная в QR. Если разместить её в мобильном приложении или мобильной версии сайта, при нажатии откроется установленное на телефоне приложение банка-участника СБП C2B с возможностью оплатить по данному коду.
- `externaltransaction` - идентификатор динамического QR-кода.


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV ="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:InvoiceRequest xmlns:ns2="http://moneta.ru/schemas/messages.xsd" ns2:version="VERSION_2">
 <ns2:payer>364</ns2:payer>
 <ns2:payee>10481430</ns2:payee>
 <ns2:amount>100</ns2:amount>
 <ns2:clientTransaction>12229</ns2:clientTransaction>
 <ns2:description>Test</ns2:description>
 <ns2:operationInfo>
 <ns2:attribute>
 <ns2:key>CUSTOMFIELD:QRTTL</ns2:key>
 <ns2:value>11</ns2:value>
 </ns2:attribute>
 </ns2:operationInfo>
 </ns2:InvoiceRequest>
 </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:InvoiceResponse xmlns:ns2="http://moneta.ru/schemas/messages.xsd">
 <ns2:status>CREATED</ns2:status>
 <ns2:dateTime>2021-03-30T11:38:45.000+03:00</ns2:dateTime>
 <ns2:transaction>1001657743</ns2:transaction>
 <ns2:clientTransaction>12229</ns2:clientTransaction>
 <ns2:operationInfo>
 <ns2:id>1001657743</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>Test</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>typeid</ns2:key>
 <ns2:value>3</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamount</ns2:key>
 <ns2:value>100</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetalias</ns2:key>
 <ns2:value>Система Быстрых Платежей C2B (СБП)</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>12229</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:qrttl</ns2:key>
 <ns2:value>11</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>qrpayload</ns2:key>
<ns2:value>https://qr.nspk.ru/AD100023V96ORJUR98CRVT2RR91R3UNA?type=02&amp;bank=100000000061&amp;sum=10000&amp;cur=RUB&amp;crc=D2E1</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>CREATED</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>qrlink</ns2:key>
<ns2:value>https://payanyway.ru/qrcode.htm?value=https%3A%2F%2Fqr.nspk.ru%2FAD100023V96ORJUR98CRVT2RR91R3UNA%3Ftype%3D02%26bank%3D100000000061%26sum%3D10000%26cur%3DRUB%26crc%3DD2E1&amp;w=256&amp;h=256</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2021-03-30T11:38:45.000+03:00</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetaccountid</ns2:key>
 <ns2:value>364</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>category</ns2:key>
 <ns2:value>BUSINESS</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>externaltransaction</ns2:key>
 <ns2:value>AD100023V96ORJUR98CRVT2RR91R3UNA</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamounttotal</ns2:key>
 <ns2:value>100</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourcecurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>isinvoice</ns2:key>
 <ns2:value>1</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>100</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>10481430</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>isreversed</ns2:key>
 <ns2:value>true</ns2:value>
 </ns2:attribute>
 </ns2:operationInfo>
 </ns2:InvoiceResponse>
 </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


JSON запрос:


```
{
 "Envelope": {
 "Header": {
 "Security": {
 "UsernameToken": {
 "Username": "username",
 "Password": "password"
 }
 }
 },
 "Body": {
 "InvoiceRequest": {
 "version": "VERSION_2",
 "payer": "364",
 "payee": "10481430",
 "amount": "100",
 "clientTransaction": "12229",
 "description": "Test",
 "operationInfo": {
 "attribute": [
 {
 "key": "CUSTOMFIELD:QRTTL",
 "value": "11"
 }
 ]
 }
 }
 }
 }
}
```


JSON ответ:


```
{
 "Envelope":{
 "Body":{
 "InvoiceResponse":{
 "dateTime":"2021-03-30T11:38:45.000+03:00",
 "operationInfo":{
 "id":1001657743,
 "attribute":[
 {
 "value":"RUB",
 "key":"targetcurrencycode"
 },
 {
 "value":"Test",
 "key":"description"
 },
 {
 "value":"3",
 "key":"typeid"
 },
 {
 "value":"100",
 "key":"sourceamount"
 },
 {
 "value":"Система Быстрых Платежей C2B (СБП)",
 "key":"targetalias"
 },
 {
 "value":"12229",
 "key":"clienttransaction"
 },
 {
 "value": "11",
 "key": "customfield:qrttl"
 },
 {
 "value":"https:\/\/qr.nspk.ru\/AD100023V96ORJUR98CRVT2RR91R3UNA?type=02&bank=100000000061&sum=10000&acur=RUB&crc=D2E1",
 "key":"qrpayload"
 },
 {
 "value":"CREATED",
 "key":"statusid"
 },
 {
 "value":"https:\/\/payanyway.ru\/qrcode.htm?value=https%3A%2F%2Fqr.nspk.ru%2FAD100023V96ORJUR98CRVT2RR91R3UNA%3Ftype%3D02%26bank%3D100000000061%26sum%3D10000%26cur%3DRUB%26crc%3DD2E1&w=256&h=256",
 "key":"qrlink"
 },
 {
 "value":"0",
 "key":"haschildren"
 },
 {
 "value":"2021-03-30T11:38:45.000+03:00",
 "key":"modified"
 },
 {
 "value":"364",
 "key":"targetaccountid"
 },
 {
 "value":"BUSINESS",
 "key":"category"
 },
 {
 "value":"AD100023V96ORJUR98CRVT2RR91R3UNA",
 "key":"externaltransaction"
 },
 {
 "value":"100",
 "key":"sourceamounttotal"
 },
 {
 "value":"RUB",
 "key":"sourcecurrencycode"
 },
 {
 "value":"1",
 "key":"isinvoice"
 },
 {
 "value":"100",
 "key":"sourceaccounttotal"
 },
 {
 "value":"10481430",
 "key":"sourceaccountid"
 },
 {
 "value":"true",
 "key":"isreversed"
 }
 ]
 },
 "clientTransaction":"12229",
 "transaction":1001657743,
 "status":"CREATED"
 }
 }
 }
}
```


Для оплаты Invoice можно:

- Использовать `transactionId` и переход на платёжную форму Assistant в виде: [https://moneta.ru/assistant.htm?operationId=](https://moneta.ru/assistant.htm?operationId=)полученный_номер_операции&paymentSystem.unitId=12299232&paymentSystem.limitIds=12299232&followup=true;
- Использовать `qrlink` для графического отображения QR — кода Плательщику, например, на сайте получателя, и последующего сканирования устройством Плательщика;
- Использовать `qrpayload`, например, в мобильной версии сайта или мобильном приложении Получателя, чтобы Плательщик мог проводить оплату с одного устройства (смартфона). На некоторых устройствах Плательщики могут сталкиваться с проблемой выбора банка для оплаты по QR-коду, поэтому Получатели могут интегрировать в свои приложения/сайты виджет выбора банков СБП. Найти SDK для применению виджета выбора банков СБП можно здесь https://sbp.nspk.ru/ "Бизнесу"-> "Онлайн" (подробнее) -> "Виджет СБП".