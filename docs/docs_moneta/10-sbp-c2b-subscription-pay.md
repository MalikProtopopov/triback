Запрос на оплату с привязанного счёта возможен, если ТСП известно, что Плательщик ранее привязал счёт для оплаты и у ТСП есть сохранённое для данного Плательщика значение `PAYMENTTOKEN`. ТСП нужно сформировать `PaymentRequest` со значением `PAYMENTTOKEN`, полученным при оформлении привязки счёта. После успешной оплаты ТСП получит уведомление на pay url или url, указанный в «Действия при зачислении/списании» (в личном кабинете moneta.ru) или «Вызов url» (в личном кабинете payanyway.ru).


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
 <mes:PaymentRequest mes:version="VERSION_2">
 <mes:payer>364</mes:payer>
 <mes:payee>34561043</mes:payee>
 <mes:amount>11.12</mes:amount>
 <mes:isPayerAmount>false</mes:isPayerAmount>
 <mes:paymentPassword>12345</mes:paymentPassword>
 <mes:clientTransaction>SBSCR_100523-002</mes:clientTransaction>
 <mes:description>Платеж по подписке</mes:description>
 <mes:operationInfo>
 <mes:attribute>
 <mes:key>PAYMENTTOKEN</mes:key>
 <mes:value>03056694</mes:value>
 </mes:attribute>
 </mes:operationInfo>
 </mes:PaymentRequest>
 </soapenv:Body>
</soapenv:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:PaymentResponse xmlns:ns2="http://moneta.ru/schemas/messages.xsd">
 <ns2:id>3179452</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>Платеж по подписке</ns2:value>
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
 <ns2:value>СБП QR</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>SBSCR_100523-002</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>CREATED</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2023-05-10T15:51:14.000+03:00</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>paymenttoken</ns2:key>
 <ns2:value>03056694</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetaccountid</ns2:key>
 <ns2:value>364</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>initby</ns2:key>
 <ns2:value>services</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>category</ns2:key>
 <ns2:value>BUSINESS</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>externaltransaction</ns2:key>
 <ns2:value>BD100011PHDVBJ9N8QGQLTO5VADPJUEU</ns2:value>
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
 </ns2:PaymentResponse>
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
 "PaymentRequest": {
 "version": "VERSION_2",
 "payer": "364",
 "payee": "34561043",
 "amount": 13.12,
 "isPayerAmount": false,
 "clientTransaction": "1234567735_12",
 "description": "Оплата по токену",
 "operationInfo": {
 "attribute": [
 {
 "key": "PAYMENTTOKEN",
 "value": "03056694"
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
 "PaymentResponse": {
 "id": 3179467,
 "attribute": [
 {
 "value": "RUB",
 "key": "targetcurrencycode"
 },
 {
 "value": "Оплата по токену",
 "key": "description"
 },
 {
 "value": "3",
 "key": "typeid"
 },
 {
 "value": "13.12",
 "key": "sourceamount"
 },
 {
 "value": "СБП QR",
 "key": "targetalias"
 },
 {
 "value": "1234567735_12",
 "key": "clienttransaction"
 },
 {
 "value": "CREATED",
 "key": "statusid"
 },
 {
 "value": "0",
 "key": "haschildren"
 },
 {
 "value": "2023-05-10T15:56:52.000+03:00",
 "key": "modified"
 },
 {
 "value": "03056694",
 "key": "paymenttoken"
 },
 {
 "value": "364",
 "key": "targetaccountid"
 },
 {
 "value": "services",
 "key": "initby"
 },
 {
 "value": "BUSINESS",
 "key": "category"
 },
 {
 "value": "BD10000FCRFB830492GRHQ1B05NOII2I",
 "key": "externaltransaction"
 },
 {
 "value": "13.12",
 "key": "sourceamounttotal"
 },
 {
 "value": "RUB",
 "key": "sourcecurrencycode"
 },
 {
 "value": "13.12",
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
 }
 }
 }
}
```