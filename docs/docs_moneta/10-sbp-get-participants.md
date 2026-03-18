Список банков-участников СБП — это перечень банков, участвующих в переводах через СБП.

Список банков-участников СБП может отличаться в зависимости от сценариев СБП: например, самый обширный список банков можно получить при работе со сценариями C2C/Me2Me Push.

Особенности запроса списка банков-участников для сценариев C2C/Me2Me Push:

- наличие параметра «банк по умолчанию», подробнее про «банк по умолчанию» в разделе «Описание полей для переводов СБП»;
- запрос списка банков-участников с параметром «банк по умолчанию» проходит в два этапа (SECUREDFIELD:PAYMENT_STAGE=1 И 2).
- запрос списка банков-участников нужно выполнять для каждого перевода C2C/Me2Me Push (для сценариев B2COther, Me2MePull - достаточно выполнять 1 раз в сутки, рекомендуем в начале каждых суток, т.е. после 00:00 часов).


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


## Пример запроса списка банков-участников и «банка по умолчанию» (для сценариев C2C/Me2Me Push)

### Шаг 1. Передать номер телефона клиента-получателя перевода

На этом этапе передаются номера счёта списания и мобильного телефона, по которому будут переведены средства через СБП.

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
 <ns11:value>1</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>CUSTOMFIELD:idPo_20</ns11:name>
 <ns11:value>79000000000</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:nbsOt_30</ns11:name>
 <ns11:value>11111111</ns11:value>
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
 <ns2:value>79000000000</ns2:value>
 <ns2:label>Телефон получателя</ns2:label>
 <ns2:comment>Введите номер телефона получателя</ns2:comment>
 <ns2:dependency>{79}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-04-20T20:04:03.815Z</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false"
 temporary="true" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-04-20T20:07:00.815Z</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="998" maxlength="1" orderBy="9" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:payment_stage</ns2:attribute-name>
 <ns2:value>2</ns2:value>
 <ns2:label>Стадия выполнения оплаты</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="false"
 temporary="false" type="ENUM">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
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
 "value": "1"
 },
 {
 "name": "CUSTOMFIELD:idPo_20",
 "value": "79000000000"
 },
 {
 "name": "SECUREDFIELD:nbsOt_30",
 "value": "11111111"
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
 "id": 20,
 "value": "79000000000"
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
 "value": "2020-05-07T12:01:24.057Z"
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
 "value": "2020-05-07T12:04:21.057Z"
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
 "value": "2"
 },
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 12,
 "attribute-name": "SECUREDFIELD:idBp_24",
 "orderBy": 2,
 "comment": "",
 "label": "Идентификатор банка получателя",
 "id": 24,
 "type": "ENUM",
 "steps": [
 "PRE"
 ],
 "required": false
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
 "readonly": false,
 "hidden": false,
 "maxlength": 9,
 "attribute-name": "SECUREDFIELD:sumOpSbp_44",
 "orderBy": 4,
 "comment": "",
 "label": "Сумма операции",
 "id": 44,
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false
 },
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 10,
 "attribute-name": "SECUREDFIELD:nbsOt_30",
 "orderBy": 3,
 "comment": "",
 "label": "Номер Счета Отправителя",
 "id": 30,
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false
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


### Шаг 2. Получить список всех банков-участников СБП и «банк по умолчанию»

Здесь нужно получить список банков-участников СБП, между счетами которых возможны денежные переводы по сценарию C2C/Me2Me Push, и банк по умолчанию, если такой был установлен физическим лицом-держателем приложения ДБО.

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
 <ns11:value>2</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:unsBo_79</ns11:name>
 <ns11:value>20200420100006166507724683403</ns11:value>
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
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-04-20T17:04:01.178Z</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false"
 temporary="true" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-04-20T17:07:01.178Z</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="998" maxlength="1" orderBy="9" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:payment_stage</ns2:attribute-name>
 <ns2:value>3</ns2:value>
 <ns2:label>Стадия выполнения оплаты</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="true"
 temporary="false" type="ENUM">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
 <ns2:label>Идентификатор банка получателя</ns2:label>
 <ns2:comment/>
 <ns2:enum>
 <ns2:item id="1crt88888882">MKB Банк (по умолчанию)</ns2:item>
 <ns2:item id="100000000081">АКБ Форштадт</ns2:item>
 <ns2:item id="600000000022">АКБ Форштадт</ns2:item>
...
 <ns2:item id="1crt88888881">ПИР Банк</ns2:item>
 <ns2:item id="100000000022">ЯНДЕКС.ДЕНЬГИ</ns2:item>
 </ns2:enum>
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
 <ns2:field hidden="false" id="44" maxlength="9" orderBy="4" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sumOpSbp_44</ns2:attribute-name>
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
 <ns2:field hidden="false" id="32" maxlength="140" orderBy="3" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name> SECUREDFIELD:np_32</ns2:attribute-name>
 <ns2:label>Назначение платежа</ns2:label>
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
 "value": "2"
 },
 {
 "name": "SECUREDFIELD:unsBo_79",
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
 "value": "2020-05-07T09:01:21.060Z"
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
 "value": "2020-05-07T09:04:21.060Z"
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
 "value": "3"
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
 "enum": {
 "item": [
 {
 "id": "1crt88888882",
 "value": "MKB Банк (по умолчанию)"
 },
 …
 {
 "id": "100000000022",
 "value": "ЯНДЕКС.ДЕНЬГИ"
 }
 ]
 },
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 24
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
 "readonly": false,
 "hidden": false,
 "maxlength": 9,
 "attribute-name": "SECUREDFIELD:sumOpSbp_44",
 "orderBy": 4,
 "comment": "",
 "label": "Сумма операции",
 "id": 44,
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": true
 },
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 10,
 "attribute-name": "SECUREDFIELD:nbsOt_30",
 "orderBy": 3,
 "comment": "",
 "label": "Номер Счета Отправителя",
 "id": 30,
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false
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


Для получения списка банков-участников в зависимости от сценария нужно:

- сразу перейти к выполнению второго шага (SECUREDFIELD:PAYMENT_STAGE=2), т.е. запрос списка банков-участников происходит в один шаг;
- передать значение атрибута unsBo_79=0;
- указать сценарий оплаты в поле `SECUREDFIELD:scenarios`. Возможные значения параметра:`C2CPush`
- `C2BQRD`
- `C2BQRS`
- `C2BRfnd`
- `B2COther`
- `Me2MePull`


Описание указано в разделе «Введение». Если пропустить параметр `SECUREDFIELD:scenarios`, возвращается список для сценария C2CPush.


**Внимание! **При запросе списка банков-участников в один шаг не возвращается «банк по умолчанию».


SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns11:providerId>374.2</ns11:providerId>
 <ns11:fieldsInfo>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:payment_stage</ns11:name>
 <ns11:value>2</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:unsBo_79</ns11:name>
 <ns11:value>0</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:scenarios</ns11:name>
 <ns11:value>Me2MePull</ns11:value>
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
 <ns2:providerId>374.2</ns2:providerId>
 <ns2:nextStep>PRE</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="32" maxlength="140" orderBy="6" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:np_32</ns2:attribute-name>
 <ns2:label>Назначение Платежа</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="994" maxlength="12" orderBy="7" readonly="false" required="false"
temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:scenarios</ns2:attribute-name>
 <ns2:value>.Me2MePull</ns2:value>
 <ns2:label>Сценарий участника СБП</ns2:label>
 <ns2:dependency>{998}=="2"</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="995" maxlength="9" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sourceAmount</ns2:attribute-name>
 <ns2:label>Сумма списания с исходного счета на шаге 5</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:label>Минимальное время следующего шага</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:label>Время истечения ожидания следующего шага</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="998" maxlength="1" orderBy="9" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:payment_stage</ns2:attribute-name>
 <ns2:value>2</ns2:value>
 <ns2:label>Стадия выполнения оплаты</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="74" maxlength="128" orderBy="5" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:steps>PAY</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:label>ФИО получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="44" maxlength="9" orderBy="4" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sumOpSbp_44</ns2:attribute-name>
 <ns2:label>Сумма операции</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="true" id="79" maxlength="29" orderBy="1" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:steps>PAY</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>0</ns2:value>
 <ns2:label>Уникальный Номер Сообщения от Банка Отправителя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="241" maxlength="120" orderBy="2" pattern="^.+$" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:idBp_24_name</ns2:attribute-name>
 <ns2:label>Банк получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="true" id="20" maxlength="12" orderBy="0" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:idPo_20</ns2:attribute-name>
 <ns2:label>Телефон получателя</ns2:label>
 <ns2:comment>Введите номер телефона получателя</ns2:comment>
 <ns2:dependency>{79}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="false" temporary="false" type="ENUM">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
 <ns2:label>Идентификатор банка получателя</ns2:label>
 <ns2:comment/>
 <ns2:enum>
 <ns2:item id="100000000004">Тинькофф Банк</ns2:item>
 </ns2:enum>
 </ns2:field>
 <ns2:field hidden="false" id="27" maxlength="32" orderBy="6" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:ioOpkcSbp_27</ns2:attribute-name>
 <ns2:label>Номер операции СБП</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="true" id="30" maxlength="10" orderBy="3" pattern="^(\d*)$" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:nbsOt_30</ns2:attribute-name>
 <ns2:label>Номер Счета Отправителя</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{79}==""</ns2:dependency>
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
 "providerId": "374.2",
 "fieldsInfo": {
 "attribute": [
 {
 "name": "SECUREDFIELD:payment_stage",
 "value": "2"
 },
 {
 "name": "SECUREDFIELD:unsBo_79",
 "value": "0"
 },
 {
 "name": "SECUREDFIELD:scenarios",
 "value": "Me2MePull"
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
 "providerId": "374.2",
 "nextStep": "PRE",
 "fields": {
 "field": [
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 140,
 "attribute-name": "SECUREDFIELD:np_32",
 "orderBy": 6,
 "comment": "",
 "label": "Назначение Платежа",
 "id": 32,
 "type": "TEXT",
 "steps": ["PRE"],
 "required": false
 },
 {
 "temporary": false,
 "hidden": false,
 "dependency": "{998}==\"2\"",
 "maxlength": 12,
 "attribute-name": "SECUREDFIELD:scenarios",
 "orderBy": 7,
 "label": "Сценарий участника СБП",
 "type": "TEXT",
 "steps": ["PRE"],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 994,
 "value": "Me2MePull"
 },
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 9,
 "attribute-name": "SECUREDFIELD:sourceAmount",
 "orderBy": 7,
 "comment": "",
 "label": "Сумма списания с исходного счета на шаге 5",
 "id": 995,
 "type": "TEXT",
 "steps": ["PRE"],
 "required": false
 },
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:minTime",
 "orderBy": 7,
 "comment": "",
 "label": "Минимальное время следующего шага",
 "id": 996,
 "type": "TEXT",
 "steps": ["PRE"],
 "required": false
 },
 {
 "temporary": false,
 "readonly": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:expirationTime",
 "orderBy": 8,
 "comment": "",
 "label": "Время истечения ожидания следующего шага",
 "id": 997,
 "type": "TEXT",
 "steps": ["PRE"],
 "required": false
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 1,
 "attribute-name": "SECUREDFIELD:payment_stage",
 "orderBy": 9,
 "label": "Стадия выполнения оплаты",
 "type": "TEXT",
 "steps": ["PRE"],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 998,
 "value": "2"
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
 "maxlength": 9,
 "attribute-name": "SECUREDFIELD:sumOpSbp_44",
 "orderBy": 4,
 "comment": "",
 "label": "Сумма операции",
 "id": 44,
 "type": "TEXT",
 "steps": ["PRE"],
 "required": false
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
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 79,
 "value": "0"
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 120,
 "attribute-name": "CUSTOMFIELD:idBp_24_name",
 "pattern": "^.+$",
 "orderBy": 2,
 "label": "Банк получателя",
 "type": "TEXT",
 "steps": ["PRE"],
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
 "steps": ["PRE"],
 "required": false,
 "readonly": false,
 "comment": "Введите номер телефона получателя",
 "id": 20
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 12,
 "attribute-name": "SECUREDFIELD:idBp_24",
 "orderBy": 2,
 "label": "Идентификатор банка получателя",
 "type": "ENUM",
 "steps": ["PRE"],
 "enum": {
 "item": [
 {
 "id": "100000000004",
 "value": "Тинькофф Банк"
 }
 ]
 },
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 24
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
 "steps": ["PRE"],
 "required": false
 },
 {
 "temporary": false,
 "hidden": true,
 "dependency": "{79}==\"\"",
 "maxlength": 10,
 "attribute-name": "SECUREDFIELD:nbsOt_30",
 "pattern": "^(\\d*)$",
 "orderBy": 3,
 "label": "Номер Счета Отправителя",
 "type": "TEXT",
 "steps": ["PRE"],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 30
 }
 ]
 }
 }
 }
 }
}
```