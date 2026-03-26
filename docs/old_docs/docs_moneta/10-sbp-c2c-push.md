Денежные переводы для физических лиц через СБП (C2C) — это переводы по номеру телефона между счетами клиентов в разных банках.

Далее описан процесс денежных переводов через Систему быстрых платежей (СБП) с электронного кошелька «МОНЕТА.РУ» на счёт любого банка-участника СБП по номеру телефона с помощью запросов `GetNextStepRequest` и ​`PaymentRequest`.


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


## Шаг 1. Передать номер телефона клиента-получателя перевода

Смотри шаг 1 в разделе «Получение списка участников СБП»

## Шаг 2. Получить список всех банков-участников СБП и «банк по умолчанию»

Смотри шаг 2 в разделе «Получение списка участников СБП»

## Шаг 3 (С2С Push). Запросить PAM-фразу (ФИО) Получателя перевода

На этом шаге требуется запросить PAM-фразу (ФИО) Получателя перевода, дополнительно передать идентификатор Id Банка Получателя из SECUREDFIELD:idBp_24, сумму перевода и назначение платежа (если необходимо).

SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns11:providerId>354</ns11:providerId>
 <ns11:fieldsInfo>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:payment_stage</ns11:name>
 <ns11:value>3</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:unsBo_79</ns11:name>
 <ns11:value>20200420100006166507724683403</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:sumOpSbp_44</ns11:name>
 <ns11:value>10.12</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:idBp_24</ns11:name>
 <ns11:value>100000000061</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:np_32</ns11:name>
 <ns11:value>DESC_TIV53_1587204346866_20200420100006166507724683403</ns11:value>
 </ns11:attribute>
 </ns11:fieldsInfo>
 </ns11:GetNextStepRequest>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:GetNextStepResponse xmlns:ns2="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns2:providerId>354</ns2:providerId>
 <ns2:nextStep>PRE</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="241" maxlength="120" orderBy="2" pattern="^.+$" readonly="false"
 required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:idBp_24_name</ns2:attribute-name>
 <ns2:label>Банк получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="true" id="20" maxlength="12" orderBy="0" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:idPo_20</ns2:attribute-name>
 <ns2:label>Телефон получателя</ns2:label>
 <ns2:comment>Введите номер телефона получателя</ns2:comment>
 <ns2:dependency>{79}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="995" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sourceAmount </ns2:attribute-name>
 <ns2:value>10.33</ns2:value>
 <ns2:label>Сумма списания с исходного счета на шаге 5ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-04-20T20:04:37.037Z</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false"
 temporary="true" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-04-20T20:07:31.037Z</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="998" maxlength="1" orderBy="9" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:payment_stage</ns2:attribute-name>
 <ns2:value>4</ns2:value>
 <ns2:label>Стадия выполнения оплаты</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="false"
 temporary="false" type="ENUM">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
 <ns2:value>100000000061</ns2:value>
 <ns2:label>Идентификатор банка получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="74" maxlength="128" orderBy="5" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:label>ФИО получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="27" maxlength="32" orderBy="6" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:ioOpkcSbp_27</ns2:attribute-name>
 <ns2:label>Номер операции СБП</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="44" maxlength="9" orderBy="4" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sumOpSbp_44</ns2:attribute-name>
 <ns2:value>10.12</ns2:value>
 <ns2:label>Сумма операции</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="30" maxlength="10" orderBy="3" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:nbsOt_30</ns2:attribute-name>
 <ns2:label>Номер Счета Отправителя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="true" id="79" maxlength="29" orderBy="1" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>20200420100006166507724683403</ns2:value>
 <ns2:label>Уникальный Номер Сообщения от Банка Отправителя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 </ns2:fields>
 </ns2:GetNextStepResponse>
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
 "Username": "Username",
 "Password": "Password"
 }
 }
 },
 "Body": {
 "GetNextStepRequest": {
 "providerId": "354",
 "fieldsInfo": {
 "attribute": [
 {
 "name": "SECUREDFIELD:payment_stage",
 "value": "3"
 },
 {
 "name": "SECUREDFIELD:unsBo_79",
 "value": "20200420100006166507724683403"
 },
 {
 "name": "SECUREDFIELD:sumOpSbp_44",
 "value": "10.12"
 },
 {
 "name": "SECUREDFIELD:idBp_24",
 "value": "100000000061"
 },
 {
 "name": "SECUREDFIELD:np_32",
 "value": "DESC_TIV53_1587204346866_20200420100006166507724683403"
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
 "GetNextStepResponse": {
 "providerId": "354",
 "nextStep": "PRE",
 "fields": {
 "field": [
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 120,
 "attribute-name": "CUSTOMFIELD:idBp_24_name",
 "pattern": "^.+$",
 "orderBy": 2,
 "label": "Банк получателя",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 241
 },
 {
 "temporary": false,
 "hidden": true,
 "dependency": "{79}==\"\"",
 "maxlength": 12,
 "attribute-name": "CUSTOMFIELD:idPo_20",
 "orderBy": 0,
 "label": "Телефон получателя",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "Введите номер телефона получателя",
 "id": 20
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:sourceAmount",
 "orderBy": 7,
 "label": "Сумма списания с исходного счета на шаге 5",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 995,
 "value": "10.33"
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:minTime",
 "orderBy": 7,
 "label": "Минимальное время следующего шага.",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 996,
 "value": "2020-05-07T12:01:55.770Z"
 },
 {
 "temporary": true,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:expirationTime",
 "orderBy": 8,
 "label": "Время истечения ожидания следующего шага.",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 997,
 "value": "2020-05-07T12:04:49.770Z"
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 1,
 "attribute-name": "SECUREDFIELD:payment_stage",
 "orderBy": 9,
 "label": "Стадия выполнения оплаты",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 998,
 "value": "4"
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 12,
 "attribute-name": "SECUREDFIELD:idBp_24",
 "orderBy": 2,
 "label": "Идентификатор банка получателя",
 "type": "ENUM",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 24,
 "value": "100000000061"
 },
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 128,
 "attribute-name": "CUSTOMFIELD:pamPo_74",
 "orderBy": 5,
 "comment": "",
 "label": "ФИО получателя",
 "id": 74,
 "type": "TEXT",
 "steps": [
 "PRE",
 "PAY"
 ],
 "required": false
 },
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "CUSTOMFIELD:ioOpkcSbp_27",
 "orderBy": 6,
 "comment": "",
 "label": "Номер операции СБП",
 "id": 27,
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 9,
 "attribute-name": "SECUREDFIELD:sumOpSbp_44",
 "orderBy": 4,
 "label": "Сумма операции",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 44,
 "value": "10.12"
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 10,
 "attribute-name": "SECUREDFIELD:nbsOt_30",
 "orderBy": 3,
 "label": "Номер Счета Отправителя",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 30,
 "value": "11111111"
 },
 {
 "temporary": false,
 "hidden": true,
 "maxlength": 29,
 "attribute-name": "SECUREDFIELD:unsBo_79",
 "orderBy": 1,
 "label": "Уникальный Номер Сообщения от Банка Отправителя",
 "type": "TEXT",
 "steps": [
 "PRE",
 "PAY"
 ],
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 79,
 "value": "20200420100006166507724683403"
 }
 ]
 }
 }
 }
 }
}
```


## Шаг 4 (С2С Push). Отобразить PAM-фразу (ФИО) Получателя перевода

На этом шаге нужно:

- получить PAM-фразу (ФИО) Получателя перевода для отображения пользователю;
- установить для пользователя ограничение по времени завершения перевода, которое указано в полях 996 и 997 ответа на запрос. Если перевод не завершён в указанное время — пользователю требуется отобразить в интерфейсе ошибку «Превышено время ожидания, повторите операцию» и позволить перейти на первую, стартовую, форму перевода СБП.


SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns11:providerId>354</ns11:providerId>
 <ns11:fieldsInfo>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:unsBo_79</ns11:name>
 <ns11:value>20200420100006166507724683403</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:payment_stage</ns11:name>
 <ns11:value>4</ns11:value>
 </ns11:attribute>
 </ns11:fieldsInfo>
 </ns11:GetNextStepRequest>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:GetNextStepResponse xmlns:ns2="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns2:providerId>354</ns2:providerId>
 <ns2:nextStep>PAY</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="74" maxlength="128" orderBy="5" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:value>Иван Иванович И</ns2:value>
 <ns2:label>ФИО получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="79" maxlength="29" orderBy="1" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>20200420100006166507724683403</ns2:value>
 <ns2:label>Уникальный Номер Сообщения от Банка Отправителя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-04-20T20:04:37.037+03:00</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false"
 temporary="true" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-04-20T20:07:31.037+03:00</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 </ns2:fields>
 </ns2:GetNextStepResponse>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```


JSON запрос:


```
{
 "Envelope":{
 "Header":{
 "Security":{
 "UsernameToken":{
 "Username":"Username",
 "Password":"Password"
 }
 }
 },
 "Body":{
 "GetNextStepRequest":{
 "providerId":"354",
 "fieldsInfo":{
 "attribute":[
 {
 "name":"SECUREDFIELD:payment_stage",
 "value":"4"
 },
 {
 "name":"SECUREDFIELD:unsBo_79",
 "value":"20200420100006166507724683403"
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
 "GetNextStepResponse":{
 "providerId":"354",
 "nextStep":"PAY",
 "fields":{
 "field":[
 {
 "temporary":false,
 "hidden":false,
 "maxlength":128,
 "attribute-name":"CUSTOMFIELD:pamPo_74",
 "orderBy":5,
 "label":"ФИО получателя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":74,
 "value":"Иван Иванович И"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":29,
 "attribute-name":"SECUREDFIELD:unsBo_79",
 "orderBy":1,
 "label":"уникальный номер сообщения от банка отправителя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":79,
 "value":"20200420100006166507724683403"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":32,
 "attribute-name":"SECUREDFIELD:minTime",
 "orderby":7,
 "label":"Минимальное время следующего шага.",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":996,
 "value":"2020-05-07t12:01:55.770+03:00"
 },
 {
 "temporary":true,
 "hidden":false,
 "maxlength":32,
 "attribute-name":"SECUREDFIELD:expirationTime",
 "orderBy":8,
 "label":"Время истечения ожидания следующего шага.",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":997,
 "value":"2020-05-07t12:04:49.770+03:00"
 }
 ]
 }
 }
 }
 }
}
```


## Шаг 5 (C2C Push). Выполнение перевода СБП (C2C Push)

На этом шаге выполняется перевод СБП (C2C) с использованием метода PaymentRequest: после выполнения запроса операция в течение 10 секунд должна перейти в финальный статус.


**Внимание! **Ограничения:

- значение description должно либо соответствовать значению SECUREDFIELD:np_32 шага 3, либо отсутствовать (при этом будет присвоено из шага 3);
- значение amount в PaymentRequest должно совпадать с SECUREDFIELD:sumOpSbp_44;
- рекомендуется использовать значение параметра isPayerAmount=false, при этом сумма amount соответствует переданной в параметре SECUREDFIELD:sumOpSbp_44 на шаге 3. Если значение isPayerAmount=true, то передаётся сумма из ответа, полученного на шаге 3 поля SECUREDFIELD:sourceAmount


SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns2:PaymentRequest xmlns:ns2="http://moneta.ru/schemas/messages.xsd" >
 <ns2:payer>11111111</ns2:payer>
 <ns2:payee>354</ns2:payee>
 <ns2:amount>10.12</ns2:amount>
 <ns2:isPayerAmount>false</ns2:isPayerAmount>
 <ns2:paymentPassword>827ccb0e********91f84e7b</ns2:paymentPassword>
 <ns2:clientTransaction>request_20200420100006166507724683403</ns2:clientTransaction>
 <ns2:description>DESC_TIV53_1587204346866_20200420100006166507724683403</ns2:description>
 <ns2:operationInfo>
 <ns2:attribute>
 <ns2:key>SECUREDFIELD:unsBo_79</ns2:key>
 <ns2:value>20200420100006166507724683403</ns2:value>
 </ns2:attribute>
 </ns2:operationInfo>
 </ns2:PaymentRequest>
 </SOAP-ENV:Body>
 </SOAP-ENV:Envelope>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:PaymentResponse xmlns:ns2="http://moneta.ru/schemas/messages.xsd">
 <ns2:id>1001312116</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>DESC_TIV53_1587204346866_20200420100006166507724683403</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>typeid</ns2:key>
 <ns2:value>4</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamount</ns2:key>
 <ns2:value>-10.12</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetalias</ns2:key>
 <ns2:value>Система Быстрых Платежей (СБП)</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>request_20200420100006166507724683403</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamountfee</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetamount</ns2:key>
 <ns2:value>10.12</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>INPROGRESS</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targettransaction</ns2:key>
 <ns2:value>A0111180304839010000043EE68465BB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2020-04-20T21:03:49.000+03:00</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetaccountid</ns2:key>
 <ns2:value>354</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>category</ns2:key>
 <ns2:value>WITHDRAWAL</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamounttotal</ns2:key>
 <ns2:value>-10.12</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourcecurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>-10.12</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>11111111</ns2:value>
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
 "Username": "Username",
 "Password": "Password"
 }
 }
 },
 "Body": {
 "PaymentRequest": {
 "payer": "11111111",
 "payee": "354",
 "amount": "10.12",
 "isPayerAmount": "false",
 "paymentPassword": "12345",
 "clientTransaction": "request_20200420100006166507724683403",
 "description": " DESC_TIV53_1587204346866_20200420100006166507724683403",
 "operationInfo": {
 "attribute": [
 {
 "key": "SECUREDFIELD:unsBo_79",
 "value": "20200420100006166507724683403"
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
 "Id": 1001312116,
 "attribute": [
 {
 "value": "rub",
 "key": "targetcurrencycode"
 },
 {
 "value": " DESC_TIV53_1587204346866_20200420100006166507724683403",
 "key": "DESCRIPTION"
 },
 {
 "value": "4",
 "key": "TYPEID"
 },
 {
 "value": "-10.12",
 "key": "SOURCEAMOUNT"
 },
 {
 "value": "СБП",
 "key": "TARGETALIAS"
 },
 {
 "value": "REQUEST_20200420100006166507724683403",
 "key": "CLIENTTRANSACTION"
 },
 {
 "value": "0",
 "key": "SOURCEAMOUNTFEE"
 },
 {
 "value": "10.12",
 "key": "TARGETAMOUNT"
 },
 {
 "value": "INPROGRESS",
 "key": "STATUSID"
 },
 {
 "value": "A0111180304839010000043EE68465BB",
 "key": " TARGETTRANSACTION "
 },
 {
 "value": "0",
 "key": "HASCHILDREN"
 },
 {
 "value": "2020-05-07T12:02:09.000+03:00",
 "key": "MODIFIED"
 },
 {
 "value": "354",
 "key": "TARGETACCOUNTID"
 },
 {
 "value": "WITHDRAWAL",
 "key": "CATEGORY"
 },
 {
 "value": "-10.12",
 "key": "SOURCEAMOUNTTOTAL"
 },
 {
 "value": "RUB",
 "key": "SOURCECURRENCYCODE"
 },
 {
 "value": "-10.12",
 "key": "SOURCEACCOUNTTOTAL"
 },
 {
 "value": "11111111",
 "key": "SOURCEACCOUNTID"
 }
 ]
 }
 }
 }
}
```