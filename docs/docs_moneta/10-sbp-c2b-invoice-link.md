Для начала работы с Кассовой ссылкой Получателю следует убедиться, что:

- Счёт Получателя настроен для работы с СБП: этот способ должен быть активен для счёта в личном кабинете moneta.ru или payanyway.ru. Проверить можно в личном кабинете moneta.ru: «Рабочий кабинет» → «Способы оплаты»; или в личном кабинете payanyway.ru: «Способы оплаты».
- Для счёта Получателя сформирована Кассовая ссылка: это можно сделать по API (метод "Регистрация Кассовой ссылки") или обратиться к сотруднику коммерческого отдела и попросить сформировать Кассовую ссылку для определенного счёта Получателя.


Чтобы провести оплату по Кассовой ссылке нужно её активировать. Кассовая ссылка становится активна, если выставить счёт (InvoiceRequest) с заполненными полями:

- `STATICQRID` - уникальный идентификатор Кассовой ссылки;
- `amount` - сумма;
- `description` - назначение платежа.


Особенности работы с Кассовой ссылкой:

- может быть только один неоплаченный и активный invoice для одного уникального значения `STATICQRID`;
- если нужно изменить сумму или назначение платежа для ранее активированной Кассовой ссылки, необходимо отменить текущий invoice, используя метод `CancelTransactionRequest`. Произойдёт деактивация Кассовой ссылки с определённым идентификатором, указанным в поле `STATICQRID`. Затем снова нужно выполнить `InvoiceRequest` с желаемыми данными.
- в поле `CUSTOMFIELD:QRTTL` можно передать период в минутах, в течение которого будет возможна оплата по Кассовой ссылке (QR-коду). Минимальное значение - одна минута, максимальное - 20 минут. Если поле `CUSTOMFIELD:QRTTL` не передано, за период использования Кассовой платёжной ссылки берётся значение 5 минут, после этого времени подготовленная операция отменяется;
- при активации Кассовой ссылки методом `InvoiceRequest` важно убедиться, что в качестве идентификатора `STATICQRID` используется именно идентификатор Кассовой ссылки, а не статического QR (QRS). Проверить доступный сценарий для уникального идентификатора qrcId (`STATICQRID`) можно методом "Получение информации по идентификатору многоразового QR (qrcId)"​. Cценарий для Кассовой ссылки — `C2B_CASH_REGISTER`.


Ответом на `InvoiceRequest` будет `InvoiceResponse`, в котором содержится:

- `transactionId` — номер операции;
- `customfield:paramsid` — идентификатор активных значений параметров Кассовой ссылки СБП. Этот атрибут показывает, что активация Кассовой ссылки прошла успешно.
- `STATICQRID` — идентификатор Кассовой ссылки (QR кода).


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


SOAP запрос:


```
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mes="http://moneta.ru/schemas/messages.xsd">
 <soapenv:Header>
 <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
 <wsse:UsernameToken wsu:Id="UsernameToken" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
 <wsse:Username>LOGIN</wsse:Username>
 <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">PASSWORD</wsse:Password>
 </wsse:UsernameToken>
 </wsse:Security>
 </soapenv:Header>
 <soapenv:Body>
 <mes:InvoiceRequest mes:version="VERSION_2">
 <mes:payer>364</mes:payer>
 <mes:payee>46209858</mes:payee>
 <mes:amount>10.01</mes:amount>
 <mes:clientTransaction>c2b_cashbox_310322_001</mes:clientTransaction>
 <mes:description>Кассовая ссылка C2B</mes:description>
 <mes:operationInfo>
 <mes:attribute>
 <mes:key>CUSTOMFIELD:QRTTL</mes:key>
 <mes:value>1</mes:value>
 </mes:attribute>
 <mes:attribute>
 <mes:key>STATICQRID</mes:key>
 <mes:value>AS1R001HJS5K8F0S956OLM9OF1NAKNC4</mes:value>
 </mes:attribute>
 </mes:operationInfo>
 </mes:InvoiceRequest>
 </soapenv:Body>
</soapenv:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:InvoiceResponse xmlns:ns2="http://moneta.ru/schemas/messages.xsd">
 <ns2:status>CREATED</ns2:status>
 <ns2:dateTime>2022-03-31T12:07:20.000+03:00</ns2:dateTime>
 <ns2:transaction>1002937425</ns2:transaction>
 <ns2:clientTransaction>c2b_cashbox_310322_001</ns2:clientTransaction>
 <ns2:operationInfo>
 <ns2:id>1002937425</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>Кассовая ссылка C2B</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>typeid</ns2:key>
 <ns2:value>3</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamount</ns2:key>
 <ns2:value>10.01</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetalias</ns2:key>
 <ns2:value>Система быстрых платежей</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:paramsid</ns2:key>
 <ns2:value>AP10000UQNSVMRS98RG8TKL916JFOH72</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>c2b_cashbox_310322_001</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:qrttl</ns2:key>
 <ns2:value>1</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>CREATED</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>staticqrid</ns2:key>
 <ns2:value>AS1R001HJS5K8F0S956OLM9OF1NAKNC4</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2022-03-31T12:07:20.000+03:00</ns2:value>
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
 <ns2:key>sourceamounttotal</ns2:key>
 <ns2:value>10.01</ns2:value>
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
 <ns2:key>invoicerequest</ns2:key>
 <ns2:value>1</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>10.01</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>46209858</ns2:value>
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
 "Username": "LOGIN",
 "Password": "PASSWORD"
 }
 }
 },
 "Body": {
 "InvoiceRequest": {
 "version": "VERSION_2",
 "payer": "364",
 "payee": "46209858",
 "amount": 10.01,
 "clientTransaction": "c2b_cashbox_310322_001",
 "description": "Кассовая ссылка C2B",
 "operationInfo": {
 "attribute": [
 {
 "key": "CUSTOMFIELD:QRTTL",
 "value": "1"
 },
 {
 "key": "STATICQRID",
 "value": "AS1R001HJS5K8F0S956OLM9OF1NAKNC4"
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
 "Envelope": {
 "Body": {
 "InvoiceResponse": {
 "dateTime": "2022-03-31T12:07:20.000+03:00",
 "operationInfo": {
 "id": 1002937425,
 "attribute": [
 {
 "value": "RUB",
 "key": "targetcurrencycode"
 },
 {
 "value": "Кассовая ссылка C2B",
 "key": "description"
 },
 {
 "value": "3",
 "key": "typeid"
 },
 {
 "value": "10.01",
 "key": "sourceamount"
 },
 {
 "value": "Система быстрых платежей",
 "key": "targetalias"
 },
 {
 "value": "AP10000UQNSVMRS98RG8TKL916JFOH72",
 "key": "customfield:paramsid"
 },
 {
 "value": "c2b_cashbox_310322_001",
 "key": "clienttransaction"
 },
 {
 "value": "1",
 "key": "customfield:qrttl"
 },
 {
 "value": "CREATED",
 "key": "statusid"
 },
 {
 "value": "AS1R001HJS5K8F0S956OLM9OF1NAKNC4",
 "key": "staticqrid"
 },
 {
 "value": "0",
 "key": "haschildren"
 },
 {
 "value": "2022-03-31T12:07:20.000+03:00",
 "key": "modified"
 },
 {
 "value": "364",
 "key": "targetaccountid"
 },
 {
 "value": "BUSINESS",
 "key": "category"
 },
 {
 "value": "10.01",
 "key": "sourceamounttotal"
 },
 {
 "value": "RUB",
 "key": "sourcecurrencycode"
 },
 {
 "value": "1",
 "key": "isinvoice"
 },
 {
 "value": "1",
 "key": "invoicerequest"
 },
 {
 "value": "10.01",
 "key": "sourceaccounttotal"
 },
 {
 "value": "46209858",
 "key": "sourceaccountid"
 },
 {
 "value": "true",
 "key": "isreversed"
 }
 ]
 },
 "clientTransaction": "c2b_cashbox_310322_001",
 "transaction": 1002937425,
 "status": "CREATED"
 }
 }
 }
```