«Прочие выплаты физическому лицу» - это перевод денег со счёта юридического лица и/или индивидуального предпринимателя на счёт физического лица по номеру мобильного телефона. Например, выплата заработной платы или выдача займов.


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


## Шаг 1 (B2COther). Запросить список банков-участников по сценарию B2COther

SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns11:providerId>364.2</ns11:providerId>
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
 <ns11:value>B2COther</ns11:value>
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
 <ns2:providerId>364.2</ns2:providerId>
 <ns2:nextStep>PRE</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="994" maxlength="12" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:scenarios</ns2:attribute-name>
 <ns2:value>B2COther</ns2:value>
 <ns2:label>Сценарий участника СБП</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="true" temporary="false" type="ENUM">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
 <ns2:label>Идентификатор банка получателя</ns2:label>
 <ns2:comment/>
 <ns2:enum>
 <ns2:item id="500000000006">Digital payment</ns2:item>
 <ns2:item id="100000000164">KEB EichEnBi Bank</ns2:item>
 ...
 <ns2:item id="100000000030">ЮниКредит Банк</ns2:item>
 <ns2:item id="100000000022">ЯНДЕКС.ДЕНЬГИ</ns2:item>
 </ns2:enum>
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
 "providerId": "364.2",
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
 "value": "B2COther"
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
 "providerId":"364.2",
 "nextStep":"PRE",
 "fields":{
 "field":[
 {
 "temporary":false,
 "hidden":false,
 "maxlength":12,
 "attribute-name":"SECUREDFIELD:scenarios",
 "orderBy":7,
 "label":"Сценарий участника СБП",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":994,
 "value":"B2COther"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":12,
 "attribute-name":"SECUREDFIELD:idBp_24",
 "orderBy":2,
 "label":"Идентификатор банка получателя",
 "type":"ENUM",
 "steps":[
 "PRE"
 ],
 "enum":{
 "item":[
 {
 "id": "500000000006",
 "value": "Digital payment"
 },
 {
 "id": "100000000164",
 "value": "KEB EichEnBi Bank"
 },
 ...
 {
 "id": "100000000030",
 "value": "ЮниКредит Банк"
 },
 {
 "id": "100000000022",
 "value": "ЯНДЕКС.ДЕНЬГИ"
 }
 ]
 },
 "required":true,
 "readonly":false,
 "comment":"",
 "id":24
 }
 ]
 }
 }
 }
 }
}
```


## Шаг 2 (B2COther). Запрос PAM Получателя платежа

На этом шаге нужно:

- передать номер телефона, по которому будет выполнен перевод денег по СБП;
- передать счёт списания. Он должен быть зарегистрирован в СБП (уточните у сотрудника НКО «МОНЕТА» (ООО);
- передать id банка в `SECUREDFIELD:idBp_24`, в который планируется перевести деньги.


**Примечание: **Значение параметра `isPayerAmount`=`false`/`true` на Шаге 4 (B2COther). Выполнение перевода СБП.

Если в запросе на Шаге 4 (B2COther). Выполнение перевода СБП используется значение параметра `isPayerAmount`=`false` (сумма зачисления), то в этом же запросе в качестве значения amount передается значение суммы, использованной ранее в параметре `SECUREDFIELD:sumOpSbp_44`.

Если в запросе на Шаге 4 (B2COther). Выполнение перевода СБП используется значение параметра `isPayerAmount`=`true` (сумма списания), то в этом же запросе в качестве значения amount передается значение суммы, использованной ранее в параметре `SECUREDFIELD:sourceAmount`.

Значение `SECUREDFIELD:sourceAmount` возвращается в ответе на Шаге 2 (B2COther). Запрос PAM Получателя платежа.

На Шаге 2 (B2COther). Запрос PAM Получателя платежа можно указать атрибут `SECUREDFIELD:sourceAmount` (сумма списания): `SECUREDFIELD:sourceAmount` будет обязательным, если не указан атрибут `SECUREDFIELD:sumOpSbp_44`.


### Пример с использованием атрибута SECUREDFIELD:sumOpSbp_44

SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11=http://moneta.ru/schemas/messages-serviceprovider-server.xsd>
 <ns11:providerId>364.1</ns11:providerId>
 <ns11:fieldsInfo>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:nbsOt_30</ns11:name>
 <ns11:value>12345678</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:np_32</ns11:name>
 <ns11:value>TIV53</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>CUSTOMFIELD:idPo_20</ns11:name>
 <ns11:value>+79999999999</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:idBp_24</ns11:name>
 <ns11:value>100000000120</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:payment_stage</ns11:name>
 <ns11:value>3</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:sumOpSbp_44</ns11:name>
 <ns11:value>10.21</ns11:value>
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
 <ns2:providerId>364.1</ns2:providerId>
 <ns2:nextStep>PRE</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="32" maxlength="140" orderBy="6" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:np_32</ns2:attribute-name>
 <ns2:value>TIV53_REF</ns2:value>
 <ns2:label>Назначение Платежа</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="995" maxlength="9" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sourceAmount</ns2:attribute-name>
 <ns2:value>10.52</ns2:value>
 <ns2:label>Сумма списания</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{44}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:02:17.458Z</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="20" maxlength="13" orderBy="3" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:idPo_20</ns2:attribute-name>
 <ns2:value>+79999999999</ns2:value>
 <ns2:label>Номер телефона получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:05:17.458Z</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага</ns2:label>
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
 <ns2:field hidden="true" id="1111" maxlength="16" orderBy="8" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:operationId2Refund</ns2:attribute-name>
 <ns2:label>Номер операции для возврата</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
 <ns2:value>100000000120</ns2:value>
 <ns2:label>Идентификатор банка получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="74" maxlength="140" orderBy="9" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:label>PAM покупателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="44" maxlength="9" orderBy="4" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sumOpSbp_44</ns2:attribute-name>
 <ns2:value>10.21</ns2:value>
 <ns2:label>Сумма зачисления</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="30" maxlength="10" orderBy="3" pattern="^(\d*)$" readonly="false"
 required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:nbsOt_30</ns2:attribute-name>
 <ns2:value>12345678</ns2:value>
 <ns2:label>Номер Счета Отправителя</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{1111}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="true" id="79" maxlength="29" orderBy="1" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>20200814100006157910009923581</ns2:value>
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
 "Username": "username",
 "Password": "password"
 }
 }
 },
 "Body": {
 "GetNextStepRequest": {
 "providerId": "364.1",
 "fieldsInfo": {
 "attribute": [
 {
 "name": "SECUREDFIELD:nbsOt_30",
 "value": "12345678"
 },
 {
 "name": "SECUREDFIELD:np_32",
 "value": "TIV53"
 },
 {
 "name": "CUSTOMFIELD:idPo_20",
 "value": "+79999999999"
 },
 {
 "name": "SECUREDFIELD:idBp_24",
 "value": "100000000120"
 },
 {
 "name": "SECUREDFIELD:payment_stage",
 "value": "3"
 },
 {
 "name": "SECUREDFIELD:sumOpSbp_44",
 "value": "10.21"
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
 "providerId":"364.1",
 "nextStep":"PRE",
 "fields":{
 "field":[
 {
 "temporary":false,
 "hidden":false,
 "maxlength":140,
 "attribute-name":"SECUREDFIELD:np_32",
 "orderBy":6,
 "label":"Назначение Платежа",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":32,
 "value":"TIV53"
 },
 {
 "temporary":false,
 "hidden":false,
 "dependency":"{44}==\"\"",
 "maxlength":9,
 "attribute-name":"SECUREDFIELD:sourceAmount",
 "orderBy":7,
 "label":"Сумма списания",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":995,
 "value":"10.52"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":32,
 "attribute-name":"SECUREDFIELD:minTime",
 "orderBy":7,
 "label":"Минимальное время следующего шага.",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":996,
 "value":"2020-08-15T12:02:17.458Z"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":13,
 "attribute-name":"CUSTOMFIELD:idPo_20",
 "orderBy":3,
 "label":"Номер телефона получателя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":20,
 "value":"+79999999999"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":32,
 "attribute-name":"SECUREDFIELD:expirationTime",
 "orderBy":8,
 "label":"Время истечения ожидания следующего шага",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":997,
 "value":"2020-08-15T12:05:17.458Z"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":1,
 "attribute-name":"SECUREDFIELD:payment_stage",
 "orderBy":9,
 "label":"Стадия выполнения оплаты",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":998,
 "value":"4"
 },
 {
 "temporary":false,
 "readonly":false,
 "hidden":true,
 "maxlength":16,
 "attribute-name":"SECUREDFIELD:operationId2Refund",
 "orderBy":8,
 "comment":"",
 "label":"Номер операции для возврата",
 "id":1111,
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":12,
 "attribute-name":"SECUREDFIELD:idBp_24",
 "orderBy":2,
 "label":"Идентификатор банка получателя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":24,
 "value":"100000000120"
 },
 {
 "temporary":false,
 "readonly":false,
 "hidden":false,
 "maxlength":140,
 "attribute-name":"CUSTOMFIELD:pamPo_74",
 "orderBy":9,
 "comment":"",
 "label":"PAM покупателя",
 "id":74,
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":false
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":9,
 "attribute-name":"SECUREDFIELD:sumOpSbp_44",
 "orderBy":4,
 "label":"Сумма зачисления",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":44,
 "value":"10.21"
 },
 {
 "temporary":false,
 "hidden":false,
 "dependency":"{1111}==\"\"",
 "maxlength":10,
 "attribute-name":"SECUREDFIELD:nbsOt_30",
 "pattern":"^(\\d*)$",
 "orderBy":3,
 "label":"Номер Счета Отправителя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":30,
 "value":"12345678"
 },
 {
 "temporary":false,
 "hidden":true,
 "maxlength":29,
 "attribute-name":"SECUREDFIELD:unsBo_79",
 "orderBy":1,
 "label":"Уникальный Номер Сообщения от Банка Отправителя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":79,
 "value":"20200814100006157910009923581"
 }
 ]
 }
 }
 }
 }
}
```


### Пример с использованием атрибута SECUREDFIELD:sourceAmount

SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11=http://moneta.ru/schemas/messages-serviceprovider-server.xsd>
 <ns11:providerId>364.1</ns11:providerId>
 <ns11:fieldsInfo>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:nbsOt_30</ns11:name>
 <ns11:value>12345678</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:np_32</ns11:name>
 <ns11:value>TIV53</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>CUSTOMFIELD:idPo_20</ns11:name>
 <ns11:value>+79999999999</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:idBp_24</ns11:name>
 <ns11:value>100000000120</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:payment_stage</ns11:name>
 <ns11:value>3</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:sourceAmount</ns11:name>
 <ns11:value>10.52</ns11:value>
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
 <ns2:providerId>364.1</ns2:providerId>
 <ns2:nextStep>PRE</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="32" maxlength="140" orderBy="6" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:np_32</ns2:attribute-name>
 <ns2:value>TIV53_REF</ns2:value>
 <ns2:label>Назначение Платежа</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="995" maxlength="9" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sourceAmount</ns2:attribute-name>
 <ns2:value>10.52</ns2:value>
 <ns2:label>Сумма списания</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{44}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:02:17.458Z</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="20" maxlength="13" orderBy="3" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:idPo_20</ns2:attribute-name>
 <ns2:value>+79999999999</ns2:value>
 <ns2:label>Номер телефона получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:05:17.458Z</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага</ns2:label>
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
 <ns2:field hidden="true" id="1111" maxlength="16" orderBy="8" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:operationId2Refund</ns2:attribute-name>
 <ns2:label>Номер операции для возврата</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
 <ns2:value>100000000120</ns2:value>
 <ns2:label>Идентификатор банка получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="74" maxlength="140" orderBy="9" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:label>PAM покупателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="44" maxlength="9" orderBy="4" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sumOpSbp_44</ns2:attribute-name>
 <ns2:value>10.21</ns2:value>
 <ns2:label>Сумма зачисления</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="30" maxlength="10" orderBy="3" pattern="^(\d*)$" readonly="false"
 required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:nbsOt_30</ns2:attribute-name>
 <ns2:value>12345678</ns2:value>
 <ns2:label>Номер Счета Отправителя</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{1111}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="true" id="79" maxlength="29" orderBy="1" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>20200814100006157910009923581</ns2:value>
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
 "Username": "username",
 "Password": "password"
 }
 }
 },
 "Body": {
 "GetNextStepRequest": {
 "providerId": "364.1",
 "fieldsInfo": {
 "attribute": [
 {
 "name": "SECUREDFIELD:nbsOt_30",
 "value": "12345678"
 },
 {
 "name": "SECUREDFIELD:np_32",
 "value": "TIV53"
 },
 {
 "name": "CUSTOMFIELD:idPo_20",
 "value": "+79999999999"
 },
 {
 "name": "SECUREDFIELD:idBp_24",
 "value": "100000000120"
 },
 {
 "name": "SECUREDFIELD:payment_stage",
 "value": "3"
 },
 {
 "name": "SECUREDFIELD:sourceAmount",
 "value": "10.52"
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
 "providerId":"364.1",
 "nextStep":"PRE",
 "fields":{
 "field":[
 {
 "temporary":false,
 "hidden":false,
 "maxlength":140,
 "attribute-name":"SECUREDFIELD:np_32",
 "orderBy":6,
 "label":"Назначение Платежа",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":32,
 "value":"TIV53"
 },
 {
 "temporary":false,
 "hidden":false,
 "dependency":"{44}==\"\"",
 "maxlength":9,
 "attribute-name":"SECUREDFIELD:sourceAmount",
 "orderBy":7,
 "label":"Сумма списания",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":995,
 "value":"10.52"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":32,
 "attribute-name":"SECUREDFIELD:minTime",
 "orderBy":7,
 "label":"Минимальное время следующего шага.",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":996,
 "value":"2020-08-15T12:02:17.458Z"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":13,
 "attribute-name":"CUSTOMFIELD:idPo_20",
 "orderBy":3,
 "label":"Номер телефона получателя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":20,
 "value":"+79999999999"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":32,
 "attribute-name":"SECUREDFIELD:expirationTime",
 "orderBy":8,
 "label":"Время истечения ожидания следующего шага",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":997,
 "value":"2020-08-15T12:05:17.458Z"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":1,
 "attribute-name":"SECUREDFIELD:payment_stage",
 "orderBy":9,
 "label":"Стадия выполнения оплаты",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":998,
 "value":"4"
 },
 {
 "temporary":false,
 "readonly":false,
 "hidden":true,
 "maxlength":16,
 "attribute-name":"SECUREDFIELD:operationId2Refund",
 "orderBy":8,
 "comment":"",
 "label":"Номер операции для возврата",
 "id":1111,
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":12,
 "attribute-name":"SECUREDFIELD:idBp_24",
 "orderBy":2,
 "label":"Идентификатор банка получателя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":24,
 "value":"100000000120"
 },
 {
 "temporary":false,
 "readonly":false,
 "hidden":false,
 "maxlength":140,
 "attribute-name":"CUSTOMFIELD:pamPo_74",
 "orderBy":9,
 "comment":"",
 "label":"PAM покупателя",
 "id":74,
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":false
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":9,
 "attribute-name":"SECUREDFIELD:sumOpSbp_44",
 "orderBy":4,
 "label":"Сумма зачисления",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":44,
 "value":"10.21"
 },
 {
 "temporary":false,
 "hidden":false,
 "dependency":"{1111}==\"\"",
 "maxlength":10,
 "attribute-name":"SECUREDFIELD:nbsOt_30",
 "pattern":"^(\\d*)$",
 "orderBy":3,
 "label":"Номер Счета Отправителя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":30,
 "value":"12345678"
 },
 {
 "temporary":false,
 "hidden":true,
 "maxlength":29,
 "attribute-name":"SECUREDFIELD:unsBo_79",
 "orderBy":1,
 "label":"Уникальный Номер Сообщения от Банка Отправителя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":79,
 "value":"20200814100006157910009923581"
 }
 ]
 }
 }
 }
 }
}
```


**Примечание: **Использование параметра `SOURCETARIFFMULTIPLIER` на Шаге 4 (B2COther). Выполнение перевода СБП.

Если в запросе на Шаге 4 (B2COther). Выполнение перевода СБП используется значение параметра `isPayerAmount`=`true` (сумма списания) в сочетании с параметром `SOURCETARIFFMULTIPLIER`, то на Шаге 2 (B2COther). Запрос PAM Получателя платежа следует указать атрибут `SECUREDFIELD:SOURCETARIFFMULTIPLIER`.


### Примеры с использованием атрибутов SECUREDFIELD:sourceAmount, isPayerAmount=true, SECUREDFIELD:SOURCETARIFFMULTIPLIER

SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11=http://moneta.ru/schemas/messages-serviceprovider-server.xsd>
 <ns11:providerId>364.1</ns11:providerId>
 <ns11:fieldsInfo>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:nbsOt_30</ns11:name>
 <ns11:value>12345678</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:np_32</ns11:name>
 <ns11:value>TIV53</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>CUSTOMFIELD:idPo_20</ns11:name>
 <ns11:value>+79999999999</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:idBp_24</ns11:name>
 <ns11:value>100000000120</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:payment_stage</ns11:name>
 <ns11:value>3</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name> SECUREDFIELD:sourceAmount </ns11:name>
 <ns11:value>10</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name> SECUREDFIELD:SOURCETARIFFMULTIPLIER</ns11:name>
 <ns11:value>0.2</ns11:value>
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
 <ns2:providerId>364.1</ns2:providerId>
 <ns2:nextStep>PRE</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="32" maxlength="140" orderBy="6" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:np_32</ns2:attribute-name>
 <ns2:value>TIV53_REF</ns2:value>
 <ns2:label>Назначение Платежа</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="992" maxlength="9" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:SOURCETARIFFMULTIPLIER</ns2:attribute-name>
 <ns2:value>0.2</ns2:value>
 <ns2:label>Управляемый размер комиссии</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{44}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="995" maxlength="9" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sourceAmount</ns2:attribute-name>
 <ns2:value>10</ns2:value>
 <ns2:label>Сумма списания</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{44}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:02:17.458Z</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="20" maxlength="13" orderBy="3" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:idPo_20</ns2:attribute-name>
 <ns2:value>+79999999999</ns2:value>
 <ns2:label>Номер телефона получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:05:17.458Z</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага</ns2:label>
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
 <ns2:field hidden="true" id="1111" maxlength="16" orderBy="8" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:operationId2Refund</ns2:attribute-name>
 <ns2:label>Номер операции для возврата</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
 <ns2:value>100000000120</ns2:value>
 <ns2:label>Идентификатор банка получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="74" maxlength="140" orderBy="9" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:label>PAM покупателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="44" maxlength="9" orderBy="4" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sumOpSbp_44</ns2:attribute-name>
 <ns2:value>8</ns2:value>
 <ns2:label>Сумма зачисления</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="30" maxlength="10" orderBy="3" pattern="^(\d*)$" readonly="false"
 required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:nbsOt_30</ns2:attribute-name>
 <ns2:value>12345678</ns2:value>
 <ns2:label>Номер Счета Отправителя</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{1111}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="true" id="79" maxlength="29" orderBy="1" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>20200814100006157910009923581</ns2:value>
 <ns2:label>Уникальный Номер Сообщения от Банка Отправителя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 </ns2:fields>
 </ns2:GetNextStepResponse>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:GetNextStepResponse xmlns:ns2="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns2:providerId>364.1</ns2:providerId>
 <ns2:nextStep>PRE</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="32" maxlength="140" orderBy="6" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:np_32</ns2:attribute-name>
 <ns2:value>TIV53_REF</ns2:value>
 <ns2:label>Назначение Платежа</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="992" maxlength="9" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:SOURCETARIFFMULTIPLIER</ns2:attribute-name>
 <ns2:value>0.2</ns2:value>
 <ns2:label>Управляемый размер комиссии</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{44}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="995" maxlength="9" orderBy="7" readonly="false" required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sourceAmount</ns2:attribute-name>
 <ns2:value>10</ns2:value>
 <ns2:label>Сумма списания</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{44}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:02:17.458Z</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="20" maxlength="13" orderBy="3" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:idPo_20</ns2:attribute-name>
 <ns2:value>+79999999999</ns2:value>
 <ns2:label>Номер телефона получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:05:17.458Z</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага</ns2:label>
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
 <ns2:field hidden="true" id="1111" maxlength="16" orderBy="8" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:operationId2Refund</ns2:attribute-name>
 <ns2:label>Номер операции для возврата</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="24" maxlength="12" orderBy="2" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:idBp_24</ns2:attribute-name>
 <ns2:value>100000000120</ns2:value>
 <ns2:label>Идентификатор банка получателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="74" maxlength="140" orderBy="9" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:label>PAM покупателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="44" maxlength="9" orderBy="4" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:sumOpSbp_44</ns2:attribute-name>
 <ns2:value>8</ns2:value>
 <ns2:label>Сумма зачисления</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="30" maxlength="10" orderBy="3" pattern="^(\d*)$" readonly="false"
 required="false" temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:nbsOt_30</ns2:attribute-name>
 <ns2:value>12345678</ns2:value>
 <ns2:label>Номер Счета Отправителя</ns2:label>
 <ns2:comment/>
 <ns2:dependency>{1111}==""</ns2:dependency>
 </ns2:field>
 <ns2:field hidden="true" id="79" maxlength="29" orderBy="1" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>20200814100006157910009923581</ns2:value>
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
 "Username": "username",
 "Password": "password"
 }
 }
 },
 "Body": {
 "GetNextStepRequest": {
 "providerId": "364.1",
 "fieldsInfo": {
 "attribute": [
 {
 "name": "SECUREDFIELD:nbsOt_30",
 "value": "12345678"
 },
 {
 "name": "SECUREDFIELD:np_32",
 "value": "TIV53"
 },
 {
 "name": "CUSTOMFIELD:idPo_20",
 "value": "+79999999999"
 },
 {
 "name": "SECUREDFIELD:idBp_24",
 "value": "100000000120"
 },
 {
 "name": "SECUREDFIELD:payment_stage",
 "value": "3"
 },
 {
 "name": "SECUREDFIELD:sourceAmount",
 "value": "10"
 },
 {
 "name": "SECUREDFIELD:SOURCETARIFFMULTIPLIER",
 "value": "0.2"
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
 "providerId":"364.1",
 "nextStep":"PRE",
 "fields":{
 "field":[
 {
 "temporary":false,
 "hidden":false,
 "maxlength":140,
 "attribute-name":"SECUREDFIELD:np_32",
 "orderBy":6,
 "label":"Назначение Платежа",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":32,
 "value":"TIV53"
 },
 {
 "temporary": false,
 "hidden": false,
 "dependency": "{44}==\"\"",
 "maxlength": 9,
 "attribute-name": "SECUREDFIELD:SOURCETARIFFMULTIPLIER",
 "orderBy": 7,
 "label": "Управляемый размер комиссии",
 "type": "TEXT",
 "steps": [
 "PRE"
 ],
 "required": false,
 "readonly": false,
 "comment": "",
 "id": 992,
 "value": "0.2"
 },
 {
 "temporary":false,
 "hidden":false,
 "dependency":"{44}==\"\"",
 "maxlength":9,
 "attribute-name":"SECUREDFIELD:sourceAmount",
 "orderBy":7,
 "label":"Сумма списания",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":995,
 "value":"10"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":32,
 "attribute-name":"SECUREDFIELD:minTime",
 "orderBy":7,
 "label":"Минимальное время следующего шага.",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":996,
 "value":"2020-08-15T12:02:17.458Z"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":13,
 "attribute-name":"CUSTOMFIELD:idPo_20",
 "orderBy":3,
 "label":"Номер телефона получателя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":20,
 "value":"+79999999999"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":32,
 "attribute-name":"SECUREDFIELD:expirationTime",
 "orderBy":8,
 "label":"Время истечения ожидания следующего шага",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":997,
 "value":"2020-08-15T12:05:17.458Z"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":1,
 "attribute-name":"SECUREDFIELD:payment_stage",
 "orderBy":9,
 "label":"Стадия выполнения оплаты",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":998,
 "value":"4"
 },
 {
 "temporary":false,
 "readonly":false,
 "hidden":true,
 "maxlength":16,
 "attribute-name":"SECUREDFIELD:operationId2Refund",
 "orderBy":8,
 "comment":"",
 "label":"Номер операции для возврата",
 "id":1111,
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":12,
 "attribute-name":"SECUREDFIELD:idBp_24",
 "orderBy":2,
 "label":"Идентификатор банка получателя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":24,
 "value":"100000000120"
 },
 {
 "temporary":false,
 "readonly":false,
 "hidden":false,
 "maxlength":140,
 "attribute-name":"CUSTOMFIELD:pamPo_74",
 "orderBy":9,
 "comment":"",
 "label":"PAM покупателя",
 "id":74,
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":false
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":9,
 "attribute-name":"SECUREDFIELD:sumOpSbp_44",
 "orderBy":4,
 "label":"Сумма зачисления",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":44,
 "value":"8"
 },
 {
 "temporary":false,
 "hidden":false,
 "dependency":"{1111}==\"\"",
 "maxlength":10,
 "attribute-name":"SECUREDFIELD:nbsOt_30",
 "pattern":"^(\\d*)$",
 "orderBy":3,
 "label":"Номер Счета Отправителя",
 "type":"TEXT",
 "steps":[
 "PRE"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":30,
 "value":"12345678"
 },
 {
 "temporary":false,
 "hidden":true,
 "maxlength":29,
 "attribute-name":"SECUREDFIELD:unsBo_79",
 "orderBy":1,
 "label":"Уникальный Номер Сообщения от Банка Отправителя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":79,
 "value":"20200814100006157910009923581"
 }
 ]
 }
 }
 }
 }
}
```


## Шаг 3 (B2COther). Отобразить PAM-фразу (ФИО) Получателя перевода

На этом шаге нужно получить PAM-фразу (ФИО) Получателя перевода. При этом в полученном ответе на запрос будет указано время, за которое нужно успеть выполнить «Шаг 4 (B2COther). Выполнение перевода СБП». Ограничение по времени прописывается в полях 996 «Минимальное время следующего шага» и 997 «Время истечения ожидания следующего шага» ответа на запрос.

### SECUREDFIELD:sumOpSbp_44 & isPayerAmount=false

SOAP запрос:


```
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns11:providerId>364.1</ns11:providerId>
 <ns11:fieldsInfo>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:nbsOt_30</ns11:name>
 <ns11:value>12345678</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:np_32</ns11:name>
 <ns11:value>TIV53</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>CUSTOMFIELD:idPo_20</ns11:name>
 <ns11:value>+79999999999</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:idBp_24</ns11:name>
 <ns11:value>100000000120</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:payment_stage</ns11:name>
 <ns11:value>4</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:unsBo_79</ns11:name>
 <ns11:value>20200814100006157910009923581</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:sumOpSbp_44</ns11:name>
 <ns11:value>10.21</ns11:value>
 </ns11:attribute>
 </ns11:fieldsInfo>
 </ns11:GetNextStepRequest>
</SOAP-ENV:Body>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:GetNextStepResponse xmlns:ns2="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns2:providerId>364.1</ns2:providerId>
 <ns2:nextStep>PAY</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:02:17.458+03:00</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:05:17.458+03:00</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="998" maxlength="1" orderBy="9" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:payment_stage</ns2:attribute-name>
 <ns2:value>Payment</ns2:value>
 <ns2:label>Стадия выполнения оплаты</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="74" maxlength="140" orderBy="9" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:steps>PAY</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:value>Петр Петрович П</ns2:value>
 <ns2:label>PAM покупателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="true" id="79" maxlength="29" orderBy="1" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:steps>PAY</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>20200814100006157910009923581</ns2:value>
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
 "Username": "username",
 "Password": "password"
 }
 }
 },
 "Body": {
 "GetNextStepRequest": {
 "providerId": "364.1",
 "fieldsInfo": {
 "attribute": [
 {
 "name": "SECUREDFIELD:nbsOt_30",
 "value": "12345678"
 },
 {
 "name": "SECUREDFIELD:np_32",
 "value": "TIV53"
 },
 {
 "name": "CUSTOMFIELD:idPo_20",
 "value": "+79999999999"
 },
 {
 "name": "SECUREDFIELD:idBp_24",
 "value": "100000000120"
 },
 {
 "name": "SECUREDFIELD:payment_stage",
 "value": "4"
 },
 {
 "name": "SECUREDFIELD:unsBo_79",
 "value": "20200814100006157910009923581"
 },
 {
 "name": "SECUREDFIELD:sumOpSbp_44",
 "value": "10.21"
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
 "providerId":"364.1",
 "nextStep":"PAY",
 "fields":{
 "field":[
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:minTime",
 "orderBy": 7,
 "label": "Минимальное время следующего шага.",
 "type": "TEXT",
 "steps": [
 "PAY",
 "PRE"
 ],
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 996,
 "value": "2020-08-15T12:02:17.458+03:00"
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:expirationTime",
 "orderBy": 8,
 "label": "Время истечения ожидания следующего шага",
 "type": "TEXT",
 "steps": [
 "PAY",
 "PRE"
 ],
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 997,
 "value": "2020-08-15T12:05:17.458+03:00"
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
 "PAY",
 "PRE"
 ],
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 998,
 "value": "Payment"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":140,
 "attribute-name":
 "CUSTOMFIELD:pamPo_74",
 "orderBy":9,
 "label":"PAM покупателя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":74,
 "value":"Петр Петрович П"
 },
 {
 "temporary":false,
 "hidden":true,
 "maxlength":29,
 "attribute-name":"SECUREDFIELD:unsBo_79",
 "orderBy":1,
 "label":"Уникальный Номер Сообщения от Банка Отправителя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":79,
 "value":"20200814100006157910009923581"
 }
 ]
 }
 }
 }
 }
}
```


### SECUREDFIELD:sourceAmount & isPayerAmount=true

SOAP запрос:


```
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns11:GetNextStepRequest xmlns:ns11="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns11:providerId>364.1</ns11:providerId>
 <ns11:fieldsInfo>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:nbsOt_30</ns11:name>
 <ns11:value>12345678</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:np_32</ns11:name>
 <ns11:value>TIV53</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>CUSTOMFIELD:idPo_20</ns11:name>
 <ns11:value>+79999999999</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:idBp_24</ns11:name>
 <ns11:value>100000000120</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:payment_stage</ns11:name>
 <ns11:value>4</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:unsBo_79</ns11:name>
 <ns11:value>20200814100006157910009923581</ns11:value>
 </ns11:attribute>
 <ns11:attribute>
 <ns11:name>SECUREDFIELD:sourceAmount</ns11:name>
 <ns11:value>10.52</ns11:value>
 </ns11:attribute>
 </ns11:fieldsInfo>
 </ns11:GetNextStepRequest>
</SOAP-ENV:Body>
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:GetNextStepResponse xmlns:ns2="http://moneta.ru/schemas/messages-serviceprovider-server.xsd">
 <ns2:providerId>364.1</ns2:providerId>
 <ns2:nextStep>PAY</ns2:nextStep>
 <ns2:fields>
 <ns2:field hidden="false" id="996" maxlength="32" orderBy="7" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:minTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:02:17.458+03:00</ns2:value>
 <ns2:label>Минимальное время следующего шага.</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="997" maxlength="32" orderBy="8" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:expirationTime</ns2:attribute-name>
 <ns2:value>2020-08-15T12:05:17.458+03:00</ns2:value>
 <ns2:label>Время истечения ожидания следующего шага</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="998" maxlength="1" orderBy="9" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PAY</ns2:steps>
 <ns2:steps>PRE</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:payment_stage</ns2:attribute-name>
 <ns2:value>Payment</ns2:value>
 <ns2:label>Стадия выполнения оплаты</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="false" id="74" maxlength="140" orderBy="9" readonly="false" required="false"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:steps>PAY</ns2:steps>
 <ns2:attribute-name>CUSTOMFIELD:pamPo_74</ns2:attribute-name>
 <ns2:value>Петр Петрович П</ns2:value>
 <ns2:label>PAM покупателя</ns2:label>
 <ns2:comment/>
 </ns2:field>
 <ns2:field hidden="true" id="79" maxlength="29" orderBy="1" readonly="false" required="true"
 temporary="false" type="TEXT">
 <ns2:steps>PRE</ns2:steps>
 <ns2:steps>PAY</ns2:steps>
 <ns2:attribute-name>SECUREDFIELD:unsBo_79</ns2:attribute-name>
 <ns2:value>20200814100006157910009923581</ns2:value>
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
 "Username": "username",
 "Password": "password"
 }
 }
 },
 "Body": {
 "GetNextStepRequest": {
 "providerId": "364.1",
 "fieldsInfo": {
 "attribute": [
 {
 "name": "SECUREDFIELD:nbsOt_30",
 "value": "12345678"
 },
 {
 "name": "SECUREDFIELD:np_32",
 "value": "TIV53"
 },
 {
 "name": "CUSTOMFIELD:idPo_20",
 "value": "+79999999999"
 },
 {
 "name": "SECUREDFIELD:idBp_24",
 "value": "100000000120"
 },
 {
 "name": "SECUREDFIELD:payment_stage",
 "value": "4"
 },
 {
 "name": "SECUREDFIELD:unsBo_79",
 "value": "20200814100006157910009923581"
 },
 {
 "name": "SECUREDFIELD:sourceAmount",
 "value": "10.52"
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
 "providerId":"364.1",
 "nextStep":"PAY",
 "fields":{
 "field":[
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:minTime",
 "orderBy": 7,
 "label": "Минимальное время следующего шага.",
 "type": "TEXT",
 "steps": [
 "PAY",
 "PRE"
 ],
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 996,
 "value": "2020-08-15T12:02:17.458+03:00"
 },
 {
 "temporary": false,
 "hidden": false,
 "maxlength": 32,
 "attribute-name": "SECUREDFIELD:expirationTime",
 "orderBy": 8,
 "label": "Время истечения ожидания следующего шага",
 "type": "TEXT",
 "steps": [
 "PAY",
 "PRE"
 ],
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 997,
 "value": "2020-08-15T12:05:17.458+03:00"
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
 "PAY",
 "PRE"
 ],
 "required": true,
 "readonly": false,
 "comment": "",
 "id": 998,
 "value": "Payment"
 },
 {
 "temporary":false,
 "hidden":false,
 "maxlength":140,
 "attribute-name":
 "CUSTOMFIELD:pamPo_74",
 "orderBy":9,
 "label":"PAM покупателя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":false,
 "readonly":false,
 "comment":"",
 "id":74,
 "value":"Петр Петрович П"
 },
 {
 "temporary":false,
 "hidden":true,
 "maxlength":29,
 "attribute-name":"SECUREDFIELD:unsBo_79",
 "orderBy":1,
 "label":"Уникальный Номер Сообщения от Банка Отправителя",
 "type":"TEXT",
 "steps":[
 "PRE",
 "PAY"
 ],
 "required":true,
 "readonly":false,
 "comment":"",
 "id":79,
 "value":"20200814100006157910009923581"
 }
 ]
 }
 }
 }
 }
}
```


## Шаг 4 (B2COther). Выполнение перевода СБП

На этом шаге выполняется перевод СБП. Для протокола B2COther обычно применяется запрос PaymentRequest.


**Примечание: **Значение параметра `isPayerAmount`=`false`/`true`

Если в запросе используется `isPayerAmount`=`false` (сумма зачисления), то в этом же запросе в качестве значения amount передается значение суммы, использованной ранее в параметре `SECUREDFIELD:sumOpSbp_44`.

Если в запросе используется значение параметра `isPayerAmount`=`true` (сумма списания), то в этом же запросе в качестве значения amount передается значение суммы, использованной ранее в параметре `SECUREDFIELD:sourceAmount`.

Значение `SECUREDFIELD:sourceAmount` возвращается в ответе на Шаге 2 (B2COther). Запрос PAM Получателя платежа.


### isPayerAmount=false

SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:PaymentRequest xmlns:ns2="http://moneta.ru/schemas/messages.xsd" >
 <ns2:payer>12345678</ns2:payer>
 <ns2:payee>364</ns2:payee>
 <ns2:amount>10.21</ns2:amount>
 <ns2:isPayerAmount>false</ns2:isPayerAmount>
 <ns2:paymentPassword>e10adc39********f20f883e</ns2:paymentPassword>
 <ns2:clientTransaction>SOURCE_SBP_1597654776778</ns2:clientTransaction>
 <ns2:description>TIV53</ns2:description>
 <ns2:operationInfo>
 <ns2:attribute>
 <ns2:key>SECUREDFIELD:unsBo_79</ns2:key>
 <ns2:value>20200814100006157910009923581</ns2:value>
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
 <ns2:id>1001563566</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sbpphone</ns2:key>
 <ns2:value>0079999999999</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:idpo_20</ns2:key>
 <ns2:value>+79999999999</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>TIV53</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>typeid</ns2:key>
 <ns2:value>4</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamount</ns2:key>
 <ns2:value>-10.52</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetalias</ns2:key>
 <ns2:value>Система Быстрых Платежей C2B (СБП)</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:ioopkcsbp_27</ns2:key>
 <ns2:value>A020200817100006183977996283538D</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>SOURCE_SBP_1597654776778</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:pampo_74</ns2:key>
 <ns2:value>Петр Петрович П</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamountfee</ns2:key>
 <ns2:value>-0.31</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetamount</ns2:key>
 <ns2:value>10.21</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>TAKENIN_NOTSENT</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targettransaction</ns2:key>
 <ns2:value>A020200817100006183977996283538D</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2020-08-15T15:04:17.458+03:00"</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetaccountid</ns2:key>
 <ns2:value>364</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>category</ns2:key>
 <ns2:value>WITHDRAWAL</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:idbp_24_name</ns2:key>
 <ns2:value>АО КБ ИНТЕРПРОМБАНК</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamounttotal</ns2:key>
 <ns2:value>-10.52</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourcecurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>stage</ns2:key>
 <ns2:value>5</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>-10.52</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>12345678</ns2:value>
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
 "payer": "12345678",
 "payee": "364",
 "amount": "10.21",
 "isPayerAmount": false,
 "paymentPassword": "e10adc39********f20f883e",
 "clientTransaction": "SOURCE_SBP_1597654776778",
 "description": "TIV53",
 "operationInfo": {
 "attribute": [
 {
 "key": "SECUREDFIELD:unsBo_79",
 "value": "20200814100006157910009923581"
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
 "PaymentResponse":{
 "id":1001563566,
 "attribute":[
 {
 "value":"RUB",
 "key":"targetcurrencycode"
 },
 {
 "value":"0079999999999",
 "key":"sbpphone"
 },
 {
 "value":"+79999999999",
 "key":"customfield:idpo_20"
 },
 {
 "value":"TIV53",
 "key":"description"
 },
 {
 "value":"4",
 "key":"typeid"
 },
 {
 "value":"-10.52",
 "key":"sourceamount"
 },
 {
 "value":"Система Быстрых Платежей C2B (СБП)",
 "key":"targetalias"
 },
 {
 "value":"A020200817100006183977996283538D",
 "key":"customfield:ioopkcsbp_27"
 },
 {
 "value":"SOURCE_SBP_1597654776778",
 "key":"clienttransaction"
 },
 {
 "value":"Петр Петрович П",
 "key":"customfield:pampo_74"
 },
 {
 "value":"-0.31",
 "key":"sourceamountfee"
 },
 {
 "value":"10.21",
 "key":"targetamount"
 },
 {
 "value":"TAKENIN_NOTSENT",
 "key":"statusid"
 },
 {
 "value":"A020200817100006183977996283538D",
 "key":"targettransaction"
 },
 {
 "value":"0",
 "key":"haschildren"
 },
 {
 "value":"2020-08-15T15:04:17.458+03:00",
 "key":"modified"
 },
 {
 "value":"364",
 "key":"targetaccountid"
 },
 {
 "value":"services",
 "key":"initby"
 },
 {
 "value":"WITHDRAWAL",
 "key":"category"
 },
 {
 "value":"АО КБ ИНТЕРПРОМБАНК",
 "key":"customfield:idbp_24_name"
 },
 {
 "value":"-10.52",
 "key":"sourceamounttotal"
 },
 {
 "value":"RUB",
 "key":"sourcecurrencycode"
 },
 {
 "value":"5",
 "key":"stage"
 },
 {
 "value":"-10.52",
 "key":"sourceaccounttotal"
 },
 {
 "value":"12345678",
 "key":"sourceaccountid"
 }
 ]
 }
 }
 }
}
```


### isPayerAmount=true

SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:PaymentRequest xmlns:ns2="http://moneta.ru/schemas/messages.xsd" >
 <ns2:payer>12345678</ns2:payer>
 <ns2:payee>364</ns2:payee>
 <ns2:amount>10.52</ns2:amount>
 <ns2:isPayerAmount>true</ns2:isPayerAmount>
 <ns2:paymentPassword>e10adc39********f20f883e</ns2:paymentPassword>
 <ns2:clientTransaction>SOURCE_SBP_1597654776778</ns2:clientTransaction>
 <ns2:description>TIV53</ns2:description>
 <ns2:operationInfo>
 <ns2:attribute>
 <ns2:key>SECUREDFIELD:unsBo_79</ns2:key>
 <ns2:value>20200814100006157910009923581</ns2:value>
 </ns2:attribute>
 </ns2:operationInfo>
 </ns2:PaymentRequest>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:PaymentResponse xmlns:ns2="http://moneta.ru/schemas/messages.xsd">
 <ns2:id>1001563566</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sbpphone</ns2:key>
 <ns2:value>0079999999999</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:idpo_20</ns2:key>
 <ns2:value>+79999999999</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>TIV53</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>typeid</ns2:key>
 <ns2:value>4</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamount</ns2:key>
 <ns2:value>-10.52</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetalias</ns2:key>
 <ns2:value>Система Быстрых Платежей C2B (СБП)</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:ioopkcsbp_27</ns2:key>
 <ns2:value>A020200817100006183977996283538D</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>SOURCE_SBP_1597654776778</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:pampo_74</ns2:key>
 <ns2:value>Петр Петрович П</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamountfee</ns2:key>
 <ns2:value>-0.31</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetamount</ns2:key>
 <ns2:value>10.21</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>TAKENIN_NOTSENT</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targettransaction</ns2:key>
 <ns2:value>A020200817100006183977996283538D</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2020-08-15T15:04:17.458+03:00"</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetaccountid</ns2:key>
 <ns2:value>364</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>category</ns2:key>
 <ns2:value>WITHDRAWAL</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:idbp_24_name</ns2:key>
 <ns2:value>АО КБ ИНТЕРПРОМБАНК</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamounttotal</ns2:key>
 <ns2:value>-10.52</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourcecurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>stage</ns2:key>
 <ns2:value>5</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>-10.52</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>12345678</ns2:value>
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
 "payer": "12345678",
 "payee": "364",
 "amount": "10.52",
 "isPayerAmount": true,
 "paymentPassword": "e10adc39********f20f883e",
 "clientTransaction": "SOURCE_SBP_1597654776778",
 "description": "TIV53",
 "operationInfo": {
 "attribute": [
 {
 "key": "SECUREDFIELD:unsBo_79",
 "value": "20200814100006157910009923581"
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
 "PaymentResponse":{
 "id":1001563566,
 "attribute":[
 {
 "value":"RUB",
 "key":"targetcurrencycode"
 },
 {
 "value":"0079999999999",
 "key":"sbpphone"
 },
 {
 "value":"+79999999999",
 "key":"customfield:idpo_20"
 },
 {
 "value":"TIV53",
 "key":"description"
 },
 {
 "value":"4",
 "key":"typeid"
 },
 {
 "value":"-10.52",
 "key":"sourceamount"
 },
 {
 "value":"Система Быстрых Платежей C2B (СБП)",
 "key":"targetalias"
 },
 {
 "value":"A020200817100006183977996283538D",
 "key":"customfield:ioopkcsbp_27"
 },
 {
 "value":"SOURCE_SBP_1597654776778",
 "key":"clienttransaction"
 },
 {
 "value":"Петр Петрович П",
 "key":"customfield:pampo_74"
 },
 {
 "value":"-0.31",
 "key":"sourceamountfee"
 },
 {
 "value":"10.21",
 "key":"targetamount"
 },
 {
 "value":"TAKENIN_NOTSENT",
 "key":"statusid"
 },
 {
 "value":"A020200817100006183977996283538D",
 "key":"targettransaction"
 },
 {
 "value":"0",
 "key":"haschildren"
 },
 {
 "value":"2020-08-15T15:04:17.458+03:00",
 "key":"modified"
 },
 {
 "value":"364",
 "key":"targetaccountid"
 },
 {
 "value":"services",
 "key":"initby"
 },
 {
 "value":"WITHDRAWAL",
 "key":"category"
 },
 {
 "value":"АО КБ ИНТЕРПРОМБАНК",
 "key":"customfield:idbp_24_name"
 },
 {
 "value":"-10.52",
 "key":"sourceamounttotal"
 },
 {
 "value":"RUB",
 "key":"sourcecurrencycode"
 },
 {
 "value":"5",
 "key":"stage"
 },
 {
 "value":"-10.52",
 "key":"sourceaccounttotal"
 },
 {
 "value":"12345678",
 "key":"sourceaccountid"
 }
 ]
 }
 }
 }
}
```


**Примечание: **Если в запросе на Шаге 2 (B2COther). Запрос PAM Получателя платежа был указан атрибут `SECUREDFIELD:SOURCETARIFFMULTIPLIER`, то в запросе на Шаге 4 (B2COther). Выполнение перевода СБП используется значение параметра `isPayerAmount`=`true` (сумма списания) в сочетании с параметром `SOURCETARIFFMULTIPLIER` (в качестве значения amount передаётся значение суммы, использованной ранее в параметре `SECUREDFIELD:sourceAmount`).


SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:PaymentRequest xmlns:ns2="http://moneta.ru/schemas/messages.xsd" >
 <ns2:payer>12345678</ns2:payer>
 <ns2:payee>364</ns2:payee>
 <ns2:amount>10</ns2:amount>
 <ns2:isPayerAmount>true</ns2:isPayerAmount>
 <ns2:paymentPassword>e10adc39********f20f883e</ns2:paymentPassword>
 <ns2:clientTransaction>SOURCE_SBP_1597654776778</ns2:clientTransaction>
 <ns2:description>TIV53</ns2:description>
 <ns2:operationInfo>
 <ns2:attribute>
 <ns2:key>SECUREDFIELD:unsBo_79</ns2:key>
 <ns2:value>20200814100006157910009923581</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>SOURCETARIFFMULTIPLIER</ns2:key>
 <ns2:value>0.2</ns2:value>
 </ns2:attribute>
 </ns2:operationInfo>
 </ns2:PaymentRequest>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope
```


SOAP ответ:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/>
<SOAP-ENV:Body>
 <ns2:PaymentResponse xmlns:ns2="http://moneta.ru/schemas/messages.xsd">
 <ns2:id>1001563566</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sbpphone</ns2:key>
 <ns2:value>0079999999999</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:idpo_20</ns2:key>
 <ns2:value>+79999999999</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourcetariffmultiplier</ns2:key>
 <ns2:value>0.2</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>description</ns2:key>
 <ns2:value>TIV53</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>typeid</ns2:key>
 <ns2:value>4</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamount</ns2:key>
 <ns2:value>-10</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetalias</ns2:key>
 <ns2:value>Система Быстрых Платежей C2B (СБП)</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:ioopkcsbp_27</ns2:key>
 <ns2:value>A020200817100006183977996283538D</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>SOURCE_SBP_1597654776778</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:pampo_74</ns2:key>
 <ns2:value>Петр Петрович П</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetamount</ns2:key>
 <ns2:value>8</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>statusid</ns2:key>
 <ns2:value>TAKENIN_NOTSENT</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targettransaction</ns2:key>
 <ns2:value>A020200817100006183977996283538D</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>haschildren</ns2:key>
 <ns2:value>0</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>modified</ns2:key>
 <ns2:value>2020-08-15T15:04:17.458+03:00"</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamountcompensation</ns2:key>
 <ns2:value>2</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetaccountid</ns2:key>
 <ns2:value>364</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>category</ns2:key>
 <ns2:value>WITHDRAWAL</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>customfield:idbp_24_name</ns2:key>
 <ns2:value>АО КБ ИНТЕРПРОМБАНК</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamounttotal</ns2:key>
 <ns2:value>-10</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourcecurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>stage</ns2:key>
 <ns2:value>5</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>-10</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>12345678</ns2:value>
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
 "payer": "12345678",
 "payee": "364",
 "amount": "10",
 "isPayerAmount": true,
 "paymentPassword": "e10adc39********f20f883e",
 "clientTransaction": "SOURCE_SBP_1597654776778",
 "description": "TIV53",
 "operationInfo": {
 "attribute": [
 {
 "key": "SECUREDFIELD:unsBo_79",
 "value": "20200814100006157910009923581"
 },
 {
 "key": "SOURCETARIFFMULTIPLIER",
 "value": "0.2"
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
 "PaymentResponse":{
 "id":1001563566,
 "attribute":[
 {
 "value":"RUB",
 "key":"targetcurrencycode"
 },
 {
 "value":"0079999999999",
 "key":"sbpphone"
 },
 {
 "value":"+79999999999",
 "key":"customfield:idpo_20"
 },
 {
 "value": "0.2",
 "key": "sourcetariffmultiplier"
 },
 {
 "value":"TIV53",
 "key":"description"
 },
 {
 "value":"4",
 "key":"typeid"
 },
 {
 "value":"-10",
 "key":"sourceamount"
 },
 {
 "value":"Система Быстрых Платежей C2B (СБП)",
 "key":"targetalias"
 },
 {
 "value":"A020200817100006183977996283538D",
 "key":"customfield:ioopkcsbp_27"
 },
 {
 "value":"SOURCE_SBP_1597654776778",
 "key":"clienttransaction"
 },
 {
 "value":"Петр Петрович П",
 "key":"customfield:pampo_74"
 },
 {
 "value":"8",
 "key":"targetamount"
 },
 {
 "value":"TAKENIN_NOTSENT",
 "key":"statusid"
 },
 {
 "value":"A020200817100006183977996283538D",
 "key":"targettransaction"
 },
 {
 "value":"0",
 "key":"haschildren"
 },
 {
 "value":"2020-08-15T15:04:17.458+03:00",
 "key":"modified"
 },
 {
 "value": "2",
 "key": "sourceamountcompensation"
 },
 {
 "value":"364",
 "key":"targetaccountid"
 },
 {
 "value":"services",
 "key":"initby"
 },
 {
 "value":"WITHDRAWAL",
 "key":"category"
 },
 {
 "value":"АО КБ ИНТЕРПРОМБАНК",
 "key":"customfield:idbp_24_name"
 },
 {
 "value":"-10",
 "key":"sourceamounttotal"
 },
 {
 "value":"RUB",
 "key":"sourcecurrencycode"
 },
 {
 "value":"5",
 "key":"stage"
 },
 {
 "value":"-10",
 "key":"sourceaccounttotal"
 },
 {
 "value":"12345678",
 "key":"sourceaccountid"
 }
 ]
 }
 }
 }
}
```