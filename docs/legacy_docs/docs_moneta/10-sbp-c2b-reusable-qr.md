При работе с многоразовыми QR Получателю/ТСП критически важно контролировать их на своей стороне, вести их учет, чтобы иметь возможность идентифицировать переводы.


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


## Регистрация статического QR-кода (QRS)

Статический QR или QR-наклейка может применяться в онлайн и офлайн-магазинах.
Особенности работы со статическим QR (QRS):

- сумма операции СБП может быть не задана Получателем. В этом случае при переводе покупатель по договоренности с продавцом указывает сумму.


SOAP запрос:


```
 <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mes="http://moneta.ru/schemas/messages-frontend.xsd">
 <soapenv:Header>
 <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
 <wsse:UsernameToken wsu:Id="UsernameToken" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
 <wsse:Username>LOGIN</wsse:Username>
 <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">PASSWORD</wsse:Password>
 </wsse:UsernameToken>
 </wsse:Security>
 </soapenv:Header>
 <soapenv:Body>
 <mes:AccountSetupActionRequest>
 <mes:accountId>46209858</mes:accountId>
 <mes:sbp>
 <mes:staticQrRegistration>
 <mes:amount>10.00</mes:amount>
 <mes:paymentPurpose>Журнал</mes:paymentPurpose>
 <mes:redirectUrl>https://shop.domain.ru?id=12</mes:redirectUrl>
 </mes:staticQrRegistration>
 </mes:sbp>
 </mes:AccountSetupActionRequest>
 </soapenv:Body>
</soapenv:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:AccountSetupActionResponse xmlns:ns2="http://moneta.ru/schemas/messages-frontend.xsd">
 <ns2:accountId>46209858</ns2:accountId>
 <ns2:sbp>
 <ns2:staticQrRegistrationResult>
 <ns2:qrcId>AS100074QCPTCVTO8JM9NO8IDAIQPHPB</ns2:qrcId>
 <ns2:imageLink>
 https://sbp.payanyway.ru/admin/mnt/demo/imageqrc?qrcId=AS100074QCPTCVTO8JM9NO8IDAIQPHPB&amp;height=300&amp;width=300
 </ns2:imageLink>
 <ns2:payload>https://qr.nspk.ru/AS100074QCPTCVTO8JM9NO8IDAIQPHPB?type=01&amp;bank=100000000061&amp;sum=1000&amp;cur=RUB&amp;crc=2FF3</ns2:payload>
 <ns2:amount>10.00</ns2:amount>
 <ns2:paymentPurpose>Журнал</ns2:paymentPurpose>
 <ns2:redirectUrl>https://shop.domain.ru?id=12</ns2:redirectUrl>
 <ns2:type>01 - QR-Static (Многоразовая Платежная ссылка СБП). Может использоваться для выполнения
 множества Операций СБП C2B
 </ns2:type>
 <ns2:scenario>C2B - Одноразовая Платежная ссылка СБП или многоразовая Платежная ссылка СБП с
 фиксированной суммой
 </ns2:scenario>
 </ns2:staticQrRegistrationResult>
 </ns2:sbp>
 </ns2:AccountSetupActionResponse>
 </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


JSON запрос:


```
{
 "Envelope": {
 "Header": {
 "PayloadNamespace": "http://moneta.ru/schemas/messages-frontend.xsd",
 "Security": {
 "UsernameToken": {
 "Username": "LOGIN",
 "Password": "PASSWORD"
 }
 }
 },
 "Body": {
 "AccountSetupActionRequest": {
 "accountId": "46209858",
 "sbp": {
 "staticQrRegistration": {
 "amount": "10.00",
 "paymentPurpose": "Журнал",
 "redirectUrl": "https://shop.domain.ru?id=12"
 }
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
 "AccountSetupActionResponse": {
 "sbp": {
 "staticQrRegistrationResult": {
 "qrcId": "AS100074QCPTCVTO8JM9NO8IDAIQPHPB",
 "imageLink": "https:\/\/sbp.payanyway.ru\/admin\/mnt\/demo\/imageqrc?qrcId=AS100074QCPTCVTO8JM9NO8IDAIQPHPB&height=300&width=300",
 "amount": 10.00,
 "redirectUrl": "https:\/\/shop.domain.ru?id=12",
 "payload": "https:\/\/qr.nspk.ru\/AS100074QCPTCVTO8JM9NO8IDAIQPHPB?type=01&bank=100000000061&sum=1000&cur=RUB&crc=2FF3",
 "scenario": "C2B - Одноразовая Платежная ссылка СБП или многоразовая Платежная ссылка СБП с фиксированной суммой",
 "paymentPurpose": "Журнал",
 "type": "01 - QR-Static (Многоразовая Платежная ссылка СБП). Может использоваться для выполнения множества Операций СБП C2B"
 }
 },
 "accountId": 46209858
 }
 }
 }
}
```


## Регистрация Кассовой ссылки

Кассовая ссылка — подтип статического QR. Для оплаты нужна активация путем формирования InvoiceRequest. Подходит для оплаты в офлайн-магазинах, когда нет возможности показать QR на экране с достаточным разрешением. Графическое изображение Кассовой ссылки можно разместить на листе бумаге, например, флаере, воблере.

В Системе МОНЕТА.РУ есть ограничение на создание Кассовых ссылок - по умолчанию 10 ссылок для одного счёта. Если Получателю/ТСП требуется сформировать больше Кассовых ссылок, нужно обратиться к сотруднику коммерческого отдела.

Рекомендуем использовать одну Кассовую ссылку для одной кассы или устройства (например, вендингового аппарата) и вести их учёт. Это позволит эффективно администрировать и идентифицировать переводы.

SOAP запрос:


```
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mes="http://moneta.ru/schemas/messages-frontend.xsd">
 <soapenv:Header>
 <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
 <wsse:UsernameToken wsu:Id="UsernameToken" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
 <wsse:Username>LOGIN</wsse:Username>
 <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">PASSWORD</wsse:Password>
 </wsse:UsernameToken>
 </wsse:Security>
 </soapenv:Header>
 <soapenv:Body>
 <mes:AccountSetupActionRequest>
 <mes:accountId>46209858</mes:accountId>
 <mes:sbp>
 <mes:cashLinkRegistration>
 <mes:clientId>Кассовый аппарат №2</mes:clientId>
 </mes:cashLinkRegistration>
 </mes:sbp>
 </mes:AccountSetupActionRequest>
 </soapenv:Body>
</soapenv:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:AccountSetupActionResponse xmlns:ns2="http://moneta.ru/schemas/messages-frontend.xsd">
 <ns2:accountId>46209858</ns2:accountId>
 <ns2:sbp>
 <ns2:cashLinkRegistrationResult>
 <ns2:qrcId>AS1R004PRL5RNGBA9ARPLJLTDO94S3J9</ns2:qrcId>
 <ns2:payload>https://qr.nspk.ru/AS1R004PRL5RNGBA9ARPLJLTDO94S3J9?type=01&amp;bank=100000000061&amp;crc=5D90</ns2:payload>
 <ns2:imageLink>https://sbp.payanyway.ru/admin/mnt/demo/imageqrc?qrcId=AS1R004PRL5RNGBA9ARPLJLTDO94S3J9&amp;height=300&amp;width=300
 </ns2:imageLink>
 <ns2:type>01 - QR-Static (Многоразовая Платежная ссылка СБП). Может использоваться для выполнения множества Операций СБП C2B
 </ns2:type>
 <ns2:scenario>C2B_CASH_REGISTER - Кассовая Платежная ссылка СБП</ns2:scenario>
 <ns2:clientId>Кассовый аппарат №2</ns2:clientId>
 </ns2:cashLinkRegistrationResult>
 </ns2:sbp>
 </ns2:AccountSetupActionResponse>
 </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


JSON запрос:


```
{
 "Envelope": {
 "Header": {
 "PayloadNamespace": "http://moneta.ru/schemas/messages-frontend.xsd",
 "Security": {
 "UsernameToken": {
 "Username": "LOGIN",
 "Password": "PASSWORD"
 }
 }
 },
 "Body": {
 "AccountSetupActionRequest": {
 "accountId": "46209858",
 "sbp": {
 "cashLinkRegistration": {
 "clientId": "Кассовый аппарат №2"
 }
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
 "AccountSetupActionResponse": {
 "sbp": {
 "cashLinkRegistrationResult ": {
 "qrcId": "AS1R004PRL5RNGBA9ARPLJLTDO94S3J9",
 "imageLink": "https:\/\/sbp.payanyway.ru\/admin\/mnt\/demo\/imageqrc?qrcId=AS1R004PRL5RNGBA9ARPLJLTDO94S3J9&height=300&width=300",
 "clientId": "Кассовый аппарат №2",
 "payload": "https:\/\/qr.nspk.ru\/AS1R004PRL5RNGBA9ARPLJLTDO94S3J9?type=01&bank=100000000061&crc=5D90",
 "scenario": "C2B_CASH_REGISTER - Кассовая Платежная ссылка СБП",
 "type": "01 - QR-Static (Многоразовая Платежная ссылка СБП). Может использоваться для выполнения множества Операций СБП C2B"
 }
 },
 "accountId": 46209858
 }
 }
 }
}
```


## Редактирование описания Кассовой ссылки

Для ранее зарегистрированной Кассовой ссылки можно поменять описание (clientId). Это поможет контролировать Кассовые ссылки и избежать регистрации дополнительных, например, в случае изменений данных устройства, для которого была сформирована текущая ссылка.

SOAP запрос:


```
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mes="http://moneta.ru/schemas/messages-frontend.xsd">
 <soapenv:Header>
 <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
 <wsse:UsernameToken wsu:Id="UsernameToken" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
 <wsse:Username>LOGIN</wsse:Username>
 <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">PASSWORD</wsse:Password>
 </wsse:UsernameToken>
 </wsse:Security>
 </soapenv:Header>
 <soapenv:Body>
 <mes:AccountSetupActionRequest>
 <mes:accountId>46209858</mes:accountId>
 <mes:sbp>
 <mes:cashLinkUpdate>
 <mes:qrcId>AS1R0075L7OST2UB8QHOO0NA9HP68JRG</mes:qrcId>
 <mes:clientId>Новое значение rus3103</mes:clientId>
 </mes:cashLinkUpdate>
 </mes:sbp>
 </mes:AccountSetupActionRequest>
 </soapenv:Body>
</soapenv:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:AccountSetupActionResponse xmlns:ns2="http://moneta.ru/schemas/messages-frontend.xsd">
 <ns2:accountId>46209858</ns2:accountId>
 <ns2:sbp>
 <ns2:cashLinkUpdateResult>
 <ns2:qrcId>AS1R0075L7OST2UB8QHOO0NA9HP68JRG</ns2:qrcId>
 <ns2:imageLink>
https://sbp.payanyway.ru/admin/mnt/demo/imageqrc?qrcId=AS1R0075L7OST2UB8QHOO0NA9HP68JRG&amp;height=300&amp;width=300
 </ns2:imageLink>
 <ns2:clientId>Новое значение rus3103</ns2:clientId>
 </ns2:cashLinkUpdateResult>
 </ns2:sbp>
 </ns2:AccountSetupActionResponse>
 </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


JSON запрос:


```
{
 "Envelope": {
 "Header": {
 "PayloadNamespace": "http://moneta.ru/schemas/messages-frontend.xsd",
 "Security": {
 "UsernameToken": {
 "Username": "LOGIN",
 "Password": "PASSWORD"
 }
 }
 },
 "Body": {
 "AccountSetupActionRequest": {
 "accountId": "46209858",
 "sbp": {
 "cashLinkUpdate": {
 "qrcId": "AS1R0075L7OST2UB8QHOO0NA9HP68JRG",
 "clientId": "Новое значение rus3103"
 }
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
 "AccountSetupActionResponse": {
 "sbp": {
 "cashLinkUpdateResult": {
 "qrcId": "AS1R0075L7OST2UB8QHOO0NA9HP68JRG",
 "imageLink": "https:\/\/sbp.payanyway.ru\/admin\/mnt\/demo\/imageqrc?qrcId=AS1R0075L7OST2UB8QHOO0NA9HP68JRG&height=300&width=300",
 "clientId": "Новое значение rus3103"
 }
 },
 "accountId": 46209858
 }
 }
 }
}
```


## Получение списка зарегистрированных Кассовых ссылок

В Системе МОНЕТА.РУ доступен метод получения списка зарегистрированных Кассовых ссылок для определенного счета Получателя.

SOAP запрос:


```
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mes="http://moneta.ru/schemas/messages-frontend.xsd">
 <soapenv:Header>
 <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
 <wsse:UsernameToken wsu:Id="UsernameToken" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
 <wsse:Username>LOGIN</wsse:Username>
 <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">PASSWORD</wsse:Password>
 </wsse:UsernameToken>
 </wsse:Security>
 </soapenv:Header>
 <soapenv:Body>
 <mes:AccountSetupActionRequest>
 <mes:accountId>46209858</mes:accountId>
 <mes:sbp>
 <mes:cashLinkList/>
 </mes:sbp>
 </mes:AccountSetupActionRequest>
 </soapenv:Body>
</soapenv:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:AccountSetupActionResponse xmlns:ns2="http://moneta.ru/schemas/messages-frontend.xsd">
 <ns2:accountId>46209858</ns2:accountId>
 <ns2:sbp>
 <ns2:cashLinkListResult>
 <ns2:qrcId>AS1R004PRL5RNGBA9ARPLJLTDO94S3J9</ns2:qrcId>
 <ns2:imageLink>
https://sbp.payanyway.ru/admin/mnt/demo/imageqrc?qrcId=AS1R004PRL5RNGBA9ARPLJLTDO94S3J9&amp;height=300&amp;width=300
 </ns2:imageLink>
 <ns2:clientId>Кассовый аппарат №2</ns2:clientId>
 </ns2:cashLinkListResult>
 <ns2:cashLinkListResult>
 <ns2:qrcId>AS1R001AHKO38PKM9VPO9HME2TRVEK24</ns2:qrcId>
 <ns2:imageLink>
https://sbp.payanyway.ru/admin/mnt/demo/imageqrc?qrcId=AS1R001AHKO38PKM9VPO9HME2TRVEK24&amp;height=300&amp;width=300
 </ns2:imageLink>
 <ns2:clientId>Кассовая ссылка 12_2_2</ns2:clientId>
 </ns2:cashLinkListResult>
 </ns2:sbp>
 </ns2:AccountSetupActionResponse>
 </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


JSON запрос:


```
{
 "Envelope": {
 "Header": {
 "PayloadNamespace": "http://moneta.ru/schemas/messages-frontend.xsd",
 "Security": {
 "UsernameToken": {
 "Username": "LOGIN",
 "Password": "PASSWORD"
 }
 }
 },
 "Body": {
 "AccountSetupActionRequest": {
 "accountId": "46209858",
 "sbp": {
 "cashLinkList": ""
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
 "AccountSetupActionResponse": {
 "sbp": {
 "cashLinkListResult": [
 {
 "qrcId": "AS1R004PRL5RNGBA9ARPLJLTDO94S3J9",
 "imageLink": "https:\/\/sbp.payanyway.ru\/admin\/mnt\/demo\/imageqrc?qrcId=AS1R004PRL5RNGBA9ARPLJLTDO94S3J9&height=300&width=300",
 "clientId": "Кассовый аппарат №2"
 },
 {
 "qrcId": "AS1R001AHKO38PKM9VPO9HME2TRVEK24",
 "imageLink": "https:\/\/sbp.payanyway.ru\/admin\/mnt\/demo\/imageqrc?qrcId=AS1R001AHKO38PKM9VPO9HME2TRVEK24&height=300&width=300",
 "clientId": "Кассовая ссылка 12_2_2"
 },
 ]
 },
 "accountId": 46209858
 }
 }
 }
}
```


## Получение информации по идентификатору многоразового QR (qrcId)

В Системе МОНЕТА.РУ доступен метод получения информации по уникальному идентификатору многоразового QR (qrcId). Это поможет для определения сценария (scenario), доступного для многоразовой платёжной ссылки (статический QR или Кассовая ссылка).

SOAP запрос:


```
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:mes="http://moneta.ru/schemas/messages-frontend.xsd">
 <soapenv:Header>
 <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
 <wsse:UsernameToken wsu:Id="UsernameToken" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
 <wsse:Username>LOGIN</wsse:Username>
 <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">PASSWORD</wsse:Password>
 </wsse:UsernameToken>
 </wsse:Security>
 </soapenv:Header>
 <soapenv:Body>
 <mes:AccountSetupActionRequest>
 <mes:accountId>46209858</mes:accountId>
 <mes:sbp>
 <mes:qrInfo>
 <mes:qrcId>AS10003K7NTKC0NS809Q3VROGRE493G4</mes:qrcId>
 </mes:qrInfo>
 </mes:sbp>
 </mes:AccountSetupActionRequest>
 </soapenv:Body>
</soapenv:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:AccountSetupActionResponse xmlns:ns2="http://moneta.ru/schemas/messages-frontend.xsd">
 <ns2:accountId>46209858</ns2:accountId>
 <ns2:sbp>
 <ns2:qrInfoResult>
 <ns2:qrcId>AS10003K7NTKC0NS809Q3VROGRE493G4</ns2:qrcId>
 <ns2:imageLink>
https://sbp.payanyway.ru/admin/mnt/demo/imageqrc?qrcId=AS10003K7NTKC0NS809Q3VROGRE493G4&amp;height=300&amp;width=300
 </ns2:imageLink>
 <ns2:brandName>SBP_TEST_23</ns2:brandName>
 <ns2:amount>10.20</ns2:amount>
 <ns2:paymentPurpose>Новая ссылка</ns2:paymentPurpose>
 <ns2:redirectUrl>https://shop.domain.ru?id=12</ns2:redirectUrl>
 <ns2:type>01 – QR-Static (Многоразовая Платежная ссылка СБП). Может использоваться для выполнения
 множества Операций СБП C2B
 </ns2:type>
 <ns2:scenario>C2B – Одноразовая Платежная ссылка СБП или многоразовая Платежная ссылка СБП с
 фиксированной суммой
 </ns2:scenario>
 </ns2:qrInfoResult>
 </ns2:sbp>
 </ns2:AccountSetupActionResponse>
 </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


JSON запрос:


```
{
 "Envelope": {
 "Header": {
 "PayloadNamespace": "http://moneta.ru/schemas/messages-frontend.xsd",
 "Security": {
 "UsernameToken": {
 "Username": "LOGIN",
 "Password": "PASSWORD"
 }
 }
 },
 "Body": {
 "AccountSetupActionRequest": {
 "accountId": "46209858",
 "sbp": {
 "qrInfo": {
 "qrcId": "AS10003K7NTKC0NS809Q3VROGRE493G4"
 }
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
 "AccountSetupActionResponse": {
 "sbp": {
 "qrInfoResult": {
 "qrcId": "AS10003K7NTKC0NS809Q3VROGRE493G4",
 "imageLink": "https:\/\/sbp.payanyway.ru\/admin\/mnt\/demo\/imageqrc?qrcId=AS10003K7NTKC0NS809Q3VROGRE493G4&height=300&width=300",
 "brandName": "SBP_TEST_23",
 "amount": 10.2,
 "redirectUrl": "https:\/\/shop.domain.ru?id=12",
 "scenario": "C2B – Одноразовая Платежная ссылка СБП или многоразовая Платежная ссылка СБП с фиксированной суммой",
 "paymentPurpose": "Новая ссылка_34",
 "type": "01 – QR-Static (Многоразовая Платежная ссылка СБП). Может использоваться для выполнения множества Операций СБП C2B"
 }
 },
 "accountId": 46209858
 }
 }
 }
}
```