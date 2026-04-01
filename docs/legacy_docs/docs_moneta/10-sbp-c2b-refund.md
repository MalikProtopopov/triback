Возврат по операции QR-платежа (C2B refund) производится по номеру мобильного телефона, с которого выполнялась оплата, и в тот же банк, с которого был первоначальный QR-платеж.

Для протокола С2В refund используется метод `RefundRequest`.​

В этом запросе, кроме прочих, требуется передать параметры `transactionId` (операция QR-платежа, по которой выполняется возврат) и `SECUREDFIELD:unsBo_79`=`0`.


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:RefundRequest xmlns:ns2="http://moneta.ru/schemas/messages.xsd">
 <ns2:transactionId>1234567</ns2:transactionId>
 <ns2:amount>10.01</ns2:amount>
 <ns2:paymentPassword>paymentpassword</ns2:paymentPassword>
 <ns2:clientTransaction>abc123</ns2:clientTransaction>
 <ns2:description>ВОЗВРАТ</ns2:description>
 <ns2:operationInfo>
 <ns2:attribute>
 <ns2:key>SECUREDFIELD:unsBo_79</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 </ns2:operationInfo>
 </ns2:RefundRequest>
 </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:RefundResponse xmlns:ns2="http://moneta.ru/schemas/messages.xsd">
 <ns2:id>1234568</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:idpo_20</ns2:key>
 <ns2:value>0079370000000</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>ВОЗВРАТ</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>typeid</ns2:key>
 <ns2:value>18</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamount</ns2:key>
 <ns2:value>-10.01</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetalias</ns2:key>
 <ns2:value>сбп QR</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:ioopkcsbp_27</ns2:key>
 <ns2:value>00000000000000000000000000000000</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>abc123</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>isrefund</ns2:key>
 <ns2:value>1</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetamount</ns2:key>
 <ns2:value>10.01</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>TAKENIN_NOTSENT</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2020-11-20T13:28:22.000+03:00</ns2:value>
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
 <ns2:key>parentid</ns2:key>
 <ns2:value>1234567</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:idbp_24_name</ns2:key>
 <ns2:value>РќРљРћ РњРѕРЅРµС‚Р°</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamounttotal</ns2:key>
 <ns2:value>-10.01</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourcecurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>-10.01</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>112233</ns2:value>
 </ns2:attribute>
 </ns2:RefundResponse>
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
 "Username": "login",
 "Password": "password"
 }
 }
 },
 "Body": {
 "RefundRequest": {
 "transactionId": "1234567",
 "amount": "10.01",
 "paymentPassword": "paymentpassword",
 "clientTransaction": "abc123",
 "description": "Возврат",
 "operationInfo": {
 "attribute": [
 {
 "key": "SECUREDFIELD:unsBo_79",
 "value": "0"
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
 "RefundResponse":{
 "id":1234568,
 "attribute":[
 {
 "value":"RUB",
 "key":"targetcurrencycode"
 },
 {
 "value":"0079370000000",
 "key":"customfield:idpo_20"
 },
 {
 "value":"Возврат",
 "key":"description"
 },
 {
 "value":"18",
 "key":"typeid"
 },
 {
 "value":"-10.01",
 "key":"sourceamount"
 },
 {
 "value":"СБП QR",
 "key":"targetalias"
 },
 {
 "value":"00000000000000000000000000000000",
 "key":"customfield:ioopkcsbp_27"
 },
 {
 "value":"abc123",
 "key":"clienttransaction"
 },
 {
 "value":"1",
 "key":"isrefund"
 },
 {
 "value":"10.01",
 "key":"targetamount"
 },
 {
 "value":"TAKENIN_NOTSENT",
 "key":"statusid"
 },
 {
 "value":"0",
 "key":"haschildren"
 },
 {
 "value":"2020-11-20T13:16:46.000+03:00",
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
 "value":"1234567",
 "key":"parentid"
 },
 {
 "value":"НКО Монета",
 "key":"customfield:idbp_24_name"
 },
 {
 "value":"-10.01",
 "key":"sourceamounttotal"
 },
 {
 "value":"RUB",
 "key":"sourcecurrencycode"
 },
 {
 "value":"-10.01",
 "key":"sourceaccounttotal"
 },
 {
 "value":"112233",
 "key":"sourceaccountid"
 }
 ]
 }
 }
 }
}
```