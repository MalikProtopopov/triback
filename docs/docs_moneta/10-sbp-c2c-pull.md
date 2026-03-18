Переводы СБП по сценарию Me2Me Pull — это переводы по номеру телефона между счетами клиентов в разных банках по инициативе Получателя.

Перевод денег по этому сценарию:

- Пользователь выполняет запрос из банка, в который хочет получить деньги;
- Пользователь даёт распоряжение на перевод денег из банка, из которого переводит деньги. Распоряжение может быть разовым или оформленным на все последующие переводы. Оформив распоряжение на последующие переводы в определенный Банк-Получатель, пользователь, отправляя запрос на получение денег из Банка-Получателя, даёт согласие проводить переводы из Банка-Отправителя без подтверждения.


Создать запрос на перевод Me2Me Pull, когда НКО «МОНЕТА» (ООО) выступает в роли банка, получающего перевод, можно, если:

- статус ЭСП «МОНЕТА.РУ», получающего перевод — упрощённо-идентифицированный или идентифицированный.


В настройках счёта-прототипа для работы с ЭСП «МОНЕТА.РУ» при реализации сценария Me2Me Pull удобно настроить URL-уведомления об отмене операции (Действия при зачислении/списании средств -> Вызвать URL после отмены зачисления средств): для этого сообщите url обработчика специалисту коммерческого отдела НКО «МОНЕТА» (ООО).


**Примечание: **Может пригодиться раздел «Описание полей для переводов СБП».


## Шаг 1. Запросить список банков-участников по сценарию Me2Me Pull

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


## Шаг 2. Создать запрос на перевод денег в выбранный Банк Отправителя

Алгоритм создания запроса на перевод денег в Банке Отправителя:

- после получения списка банков-участников для сценария Me2Me Pull и выбора среди них id банка, из которого планируется перевести деньги, нужно выполнить `InvoiceRequest`;
- в `InvoiceRequest` нужно указать id банка, из которого планируется перевести деньги, в атрибуте `SECUREDFIELD:SBPBANKID`;
- в `InvoiceResponse` должен присутствовать атрибут EXTERNALTRANSACTION, который информирует об успешном создании запроса на перевод в банк, из которого планируется перевести деньги: если в InvoiceResponse не вернулось значение EXTERNALTRANSACTION, необходимо проверить корректность запроса InvoiceRequest с параметром SECUREDFIELD:SBPBANKID;
- далее ожидаем информацию о создании счёта на перевод денег в Банке Отправителя (не больше семи секунд): если счёт на перевод денег в Банке Отправителя не сформирован, созданная по запросу в InvoceRequest операция отменяется с указанием причины. При отмене будет вызван «URL после отмены зачисления» (если был настроен). Если счёт на перевод денег в Банке Отправителя сформирован, но неизвестно, оплачен ли, дополнительные URL-уведомления об этом не приходят. Отсутствие URL-уведомления на адрес обработчика «URL после отмены зачисления» значит, что на стороне Банка Отправителя был создан счёт на перевод денег;
- далее ожидаем оплату по созданному в Банке Отправителя счёту; если счёт в Банке Отправителе не оплачен в течение 10 минут после получения InvoiceResponse (с атрибутом EXTERNALTRANSACTION), счёт будет отменён и будет вызван «URL после отмены зачисления» (если был настроен).


## Пример запроса InvoiceRequest с указанием SECUREDFIELD:SBPBANK

SOAP запрос:


```
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
 <SOAP-ENV:Header/>
 <SOAP-ENV:Body>
 <ns11:InvoiceRequest xmlns:ns11="http://moneta.ru/schemas/messages.xsd" ns11:version="VERSION_2">
 <ns11:payer>374</ns11:payer>
 <ns11:payee>11111111</ns11:payee>
 <ns11:amount>100</ns11:amount>
 <ns11:clientTransaction>me2me_pull_01</ns11:clientTransaction>
 <ns11:operationInfo>
 <ns11:attribute>
 <ns11:key>SECUREDFIELD:SBPBANKID</ns11:key>
 <ns11:value>100000000025</ns11:value>
 </ns11:attribute>
 </ns11:operationInfo>
 </ns11:InvoiceRequest>
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
 <ns2:dateTime>2021-03-22T14:52:40.000+03:00</ns2:dateTime>
 <ns2:transaction>2583358</ns2:transaction>
 <ns2:clientTransaction>me2me_pull_01</ns2:clientTransaction>
 <ns2:operationInfo>
 <ns2:id>2583358</ns2:id>
 <ns2:attribute>
 <ns2:key>targetcurrencycode</ns2:key>
 <ns2:value>RUB</ns2:value>
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
 <ns2:value>СБП</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>clienttransaction</ns2:key>
 <ns2:value>me2me_pull_01</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceamountfee</ns2:key>
 <ns2:value>0</ns2:value>
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
 <ns2:value>2021-03-22T14:52:40.000+03:00</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>targetaccountid</ns2:key>
 <ns2:value>374</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>category</ns2:key>
 <ns2:value>BUSINESS</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>externaltransaction</ns2:key>
 <ns2:value>20210322100006125702386603759732</ns2:value>
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
 <ns2:key>invoicerequest</ns2:key>
 <ns2:value>1</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccounttotal</ns2:key>
 <ns2:value>100</ns2:value>
 </ns2:attribute>
 <ns2:attribute>
 <ns2:key>sourceaccountid</ns2:key>
 <ns2:value>11111111</ns2:value>
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
 "Username": "Username",
 "Password": "Password"
 }
 }
 },
 "Body": {
 "InvoiceRequest": {
 "version" : "VERSION_2",
 "payer": "374",
 "payee": "11111111",
 "amount": 100,
 "clientTransaction": "me2me_pull_01",
 "operationInfo": {
 "attribute": [
 {
 "key": "SECUREDFIELD:SBPBANKID",
 "value": "100000000025"
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
 "dateTime": "2021-03-22T14:52:40.000+03:00",
 "operationInfo": {
 "id": 2583358,
 "attribute": [
 {
 "value": "RUB",
 "key": "targetcurrencycode"
 },
 {
 "value": "3",
 "key": "typeid"
 },
 {
 "value": "100",
 "key": "sourceamount"
 },
 {
 "value": "СБП",
 "key": "targetalias"
 },
 {
 "value": "me2me_pull_01",
 "key": "clienttransaction"
 },
 {
 "value": "0",
 "key": "sourceamountfee"
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
 "value": "2021-03-22T14:52:40.000+03:00",
 "key": "modified"
 },
 {
 "value": "374",
 "key": "targetaccountid"
 },
 {
 "value": "BUSINESS",
 "key": "category"
 },
 {
 "value": "20210322100006125702386603759732",
 "key": "externaltransaction"
 },
 {
 "value": "100",
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
 "value": "100",
 "key": "sourceaccounttotal"
 },
 {
 "value": "11111111",
 "key": "sourceaccountid"
 },
 {
 "value": "true",
 "key": "isreversed"
 }
 ]
 },
 "clientTransaction": "me2me_pull_01",
 "transaction": 2583358,
 "status": "CREATED"
 }
 }
 }
}
```