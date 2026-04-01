ТСП нужно сформировать `InvoiceRequest` со значением request в атрибуте `PAYMENTTOKEN`. По такому QR-коду Плательщику будет предложено перейти в приложение Банка Плательщика для оплаты и разрешить переводы без подтверждения. После успешной оплаты ТСП получит уведомление на pay url или url, указанный в «Действия при зачислении/списании» (в личном кабинете moneta.ru) или «Вызов url» (в личном кабинете payanyway.ru), после успешной привязки счёта - на url «Привязка счёта плательщика».


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


SOAP запрос:


```
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mes="http://moneta.ru/schemas/messages.xsd">
 <soapenv:Header>
 <wsse:Security soapenv:mustUnderstand="1"
 xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
 <wsse:UsernameToken wsu:Id="UsernameToken"
 xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
 <wsse:Username>username</wsse:Username>
 <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">password</wsse:Password>
 </wsse:UsernameToken>
 </wsse:Security>
 </soapenv:Header>
 <soapenv:Body>
 <mes:InvoiceRequest mes:version="VERSION_2">
 <mes:payer>364</mes:payer>
 <mes:payee>34561043</mes:payee>
 <mes:amount>11.12</mes:amount>
 <mes:clientTransaction>ctid123456789</mes:clientTransaction>
 <mes:description>Оплата с последующей привязкой</mes:description>
 <mes:operationInfo>
 <mes:attribute>
 <mes:key>PAYMENTTOKEN</mes:key>
 <mes:value>REQUEST</mes:value>
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
 <ns2:dateTime>2023-05-10T14:58:32.000+03:00</ns2:dateTime>
 <ns2:transaction>1003637109</ns2:transaction>
 <ns2:clientTransaction>ctid123456789</ns2:clientTransaction>
 <ns2:operationInfo>
 <ns2:id>1003637109</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>Оплата с последующей привязкой</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>typeid</ns2:key>
 <ns2:value>3</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamount</ns2:key>
 <ns2:value>11.12</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetalias</ns2:key>
 <ns2:value>Система быстрых платежей</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>ctid123456789</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>qrpayload</ns2:key>
<ns2:value>https://qr.nspk.ru/BD1P002RS4PJ6HNM82HQSADEC1DBIGQK?type=02&amp;bank=100000000061&amp;sum=1112&amp;cur=RUB&amp;crc=BDD5</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>CREATED</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>qrlink</ns2:key>
<ns2:value>https://demo.sbp.payanyway.ru/admin/mnt/demo/imageqrc?qrcId=BD1P002RS4PJ6HNM82HQSADEC1DBIGQK&amp;height=330&amp;width=330</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>protectioncodeexpirationdate</ns2:key>
 <ns2:value>2023-05-13T14:58:31.000+03:00</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2023-05-10T14:58:32.000+03:00</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>paymenttoken</ns2:key>
 <ns2:value>REQUEST</ns2:value>
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
 <ns2:value>BD1P002RS4PJ6HNM82HQSADEC1DBIGQK</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamounttotal</ns2:key>
 <ns2:value>11.12</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourcecurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>11.12</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>34561043</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>isreversed</ns2:key>
 <ns2:value>true</ns2:value>
 </ns2:attribute>
 <ns2:operationInfo>
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
 "payee": "34561043",
 "amount": 10.12,
 "clientTransaction": "ctid1234566789",
 "description": "Оплата с последующей привязкой",
 "operationInfo": {
 "attribute": [
 {
 "key": "PAYMENTTOKEN",
 "value": "request"
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
 "dateTime": "2023-05-10T14:41:45.000+03:00",
 "operationInfo": {
 "id": 1003637096,
 "attribute": [
 {
 "value": "RUB",
 "key": "targetcurrencycode"
 },
 {
 "value": "Оплата с последующей привязкой",
 "key": "description"
 },
 {
 "value": "3",
 "key": "typeid"
 },
 {
 "value": "10.12",
 "key": "sourceamount"
 },
 {
 "value": "Система быстрых платежей",
 "key": "targetalias"
 },
 {
 "value": "ctid1234566789",
 "key": "clienttransaction"
 },
 {
 "value": "https:\/\/qr.nspk.ru\/BD1P007LLFJGS8VT8EOBLUFHG8BMHTH9?type=02&bank=100000000061&sum=1012&cur=RUB&crc=0EBF",
 "key": "qrpayload"
 },
 {
 "value": "CREATED",
 "key": "statusid"
 },
 {
 "value": "https:\/\/demo.sbp.payanyway.ru\/admin\/mnt\/demo\/imageqrc?qrcId=BD1P007LLFJGS8VT8EOBLUFHG8BMHTH9&height=330&width=330",
 "key": "qrlink"
 },
 {
 "value": "2023-05-13T14:41:44.000+03:00",
 "key": "protectioncodeexpirationdate"
 },
 {
 "value": "0",
 "key": "haschildren"
 },
 {
 "value": "2023-05-10T14:41:46.000+03:00",
 "key": "modified"
 },
 {
 "value": "request",
 "key": "paymenttoken"
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
 "value": "BD1P007LLFJGS8VT8EOBLUFHG8BMHTH9",
 "key": "externaltransaction"
 },
 {
 "value": "10.12",
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
 "value": "10.12",
 "key": "sourceaccounttotal"
 },
 {
 "value": "34561043",
 "key": "sourceaccountid"
 },
 {
 "value": "true",
 "key": "isreversed"
 }
 ]
 },
 "clientTransaction": "ctid1234566789",
 "transaction": 1003637096,
 "status": "CREATED"
 }
 }
 }
}
```


Пример уведомления методом POST для ТСП на url «Привязка счёта плательщика» об успешной привязке счёта:


```
NOTIFICATION=RECURRING_PAYMENT_SUBSCRIPTION&ACCOUNT_ID=34561043&OPERATION_ID=1003637109&TRANSACTION_ID=ctid12345678&CORRACCOUNT_ID=364&PAYMENTTOKEN=01003637109&ADDITIONAL_ATTRIBUTES=FIOPLAT%3D%D0%98%D0%92%D0%90%D0%9D%2B%D0%98%D0%92%D0%90%D0%9D%D0%9E%D0%92%D0%98%D0%A7%2B%D0%98%26SBPPHONE%3D0079371234567%26SBPBANK%3D%D0%9D%D0%9A%D0%9E+%D0%9C%D0%BE%D0%BD%D0%B5%D1%82%D0%B0
```


Значение атрибутов `FIOPLAT`, `SBPPHONE`, `SBPBANK` передается в url-кодировке. ТСП требуется ответить на уведомление кодом `http-status`=`200` и текстом `SUCCESS`. Если от ТСП не получен ответ с первого раза, будут повторяться попытки доставки уведомления.