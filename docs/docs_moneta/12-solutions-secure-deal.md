Логику безопасной сделки, включая процедуру рассмотрения споров, маркетплейс реализует самостоятельно.


В Системе МОНЕТА.РУ безопасная сделка состоит из двух этапов, интервал между которыми обусловлен логикой безопасной сделки.

Первый этап - прием платежа, например, с банковской карты покупателя на транзитный счет маркетплейса в Системе "МОНЕТА.РУ" (Создание базовой операции).

Принять платеж можно одним из способов, указанных в Разделе 1 документации платёжных запросов.

После проведения операции платежа Система "МОНЕТА.РУ" сообщит номер операции в параметре MNT_OPERATION_ID, этот номер операции маркетплейсу необходимо запомнить и учитывать у себя в системе.

Второй этап - это перевод принятого платежа с транзитного счета маркетплейса на расширенный счет продавца в Системе "МОНЕТА.РУ".

Расширенный счет в Системе "МОНЕТА.РУ" открывают только продавцы индивидуальные предприниматели и юридические лица.

Для перевода денежных средств с транзитного счета маркетплейса на расширенный счет продавца маркетплейса в Системе "МОНЕТА.РУ" необходимо использовать запрос PaymentRequest с помощью интерфейса MONETA.MerchantAPI, где payer=НОМЕР_ТРАНЗИТНОГО_СЧЕТА_ПЛОЩАДКИ, а payee=НОМЕРА_РАСШИРЕННОГО_СЧЕТА_ПРОДАВЦА.

Запрос:


```
{
 "Envelope":{
 "Header":{
 "Security":{
 "UsernameToken":{
 "Username":"логин",
 "Password":"пароль"
 }
 }
 },
 "Body":{
 "PaymentRequest":{
 "payer":"НОМЕР ТРАНЗИТНОГО СЧЕТА ПЛОЩАДКИ",
 "payee":"НОМЕРА РАСШИРЕННОГО СЧЕТА ПРОДАВЦА",
 "amount":"сумма",
 "clientTransaction":"внешний идентификатор транзакции",
 "operationInfo":{
 "attribute":[
 {
 "key":"PARENTID",
 "value":"12345678"
 }
 ]
 }
 }
 }
 }
}
```


Ответ:


```
{
 "Envelope":{
 "Body":{
 "PaymentResponse":{
 "transaction": "номер операции в системе МОНЕТУ.РУ",
 "dateTime": "2019-01-25T15:35:32.000+03:00",
 "status": "SUCCESS",
 "clientTransaction": "внешний идентификатор транзакции"
 }
 }
 }
}
```


```
<?php

$sdkAppFileName = __DIR__ . "/../moneta-sdk-lib/autoload.php";
include_once($sdkAppFileName);

try {
 $monetaSdk = new \Moneta\MonetaSdk();
 $monetaSdk->checkMonetaServiceConnection();

 $request = new \Moneta\Types\PaymentRequest();

 //номер счёта (в системе МОНЕТА.РУ) для списания средств
 //номер транзитного счёта магазина/маркетплейса
 $request->payer = '';

 //номер счёта (в системе МОНЕТА.РУ) для зачисления средств
 //номер расширенного счёта организации/продавца
 $request->payee = '';

 //сумма перевода
 $request->amount = '10.00';

 //номер транзакции в учётной системе магазина/маркетплейса.
 $request->clientTransaction = 'my-order-id-10_2';

 //платёжный пароль магазина/маркетплейса.
 $request->paymentPassword = '*******************';

 $operation = new \Moneta\Types\OperationInfo();

 //в параметре указывается номер базовой операции - это операция платежа на транзитный счёт магазина/маркетплейса.
 $attribute = new \Moneta\Types\KeyValueAttribute();
 $attribute->key = 'PARENTID';
 $attribute->value = '';
 $operation->addAttribute($attribute);

 $request->operationInfo = $operation;

 //запрос на перевод средств внутри системы МОНЕТА.РУ
 //с транзитного счёта магазина/маркетплейса на расширенный счёт организации(продавца)
 $result = $monetaSdk->monetaService->Payment($request);

 if (!$result['id']) {
 throw new Exception(print_r($result, true));
 }

 echo "Запрос обработан.";

 foreach ($result['attribute'] as $key => $attribute) {
 if ('statusid' === $attribute['key']) {
 if ((new \Moneta\Types\OperationStatus())::SUCCEED !== $attribute['value']) {
 echo " Операция НЕ проведена полностью.";
 }
 break;
 }
 }

} catch (Exception $e) {
 echo "Ошибка:<br />";
 echo "<pre>" . $e->getMessage() . "</pre>";
}
```


В атрибутах перевода необходимо указать номер базовой операции в поле PARENTID, это операция платежа на транзитный счет торговой площадки.

Для перевода денежных средств с расширенного счета продавца в Системе "МОНЕТА.РУ" на банковские реквизиты продавца необходимо использовать запрос PaymentRequest с помощью интерфейса MONETA.MerchantAPI, где payer=НОМЕРА РАСШИРЕННОГО СЧЕТА ПРОДАВЦА, а payee=5.

Запрос:


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
 "PaymentRequest":{
 "payer":НОМЕР РАСШИРЕННОГО СЧЕТА ПРОДАВЦА,
 "payee":5,
 "amount":10,
 "clientTransaction":"Внешний номер операции",
 "paymentPassword":12345,
 "isPayerAmount":true,
 "operationInfo":{
 "attribute":[
 {
 "key":"WIREPAYMENTPURPOSE",
 "value":"Перечисление суммы переводов денежных средств по Договору № ___ от DD.MM.YYYY. НДС не облагается."
 }
 ]
 }
 }
 }
 }
}
```


```
<?php

$sdkAppFileName = __DIR__ . "/../moneta-sdk-lib/autoload.php";
include_once($sdkAppFileName);

try {
 $monetaSdk = new \Moneta\MonetaSdk();
 $monetaSdk->checkMonetaServiceConnection();

 $request = new \Moneta\Types\PaymentRequest();

 //номер счёта (в системе МОНЕТА.РУ) для списания средств
 //номер расширенного счёта организации(продавца)
 $request->payer = '';

 //получатель перевода
 //5 - будет осуществлён банковский перевод по реквизитам; в банк организации(продавца)
 $request->payee = '5';

 //сумма перевода
 $request->amount = '10.00';

 //номер транзакции в учётной системе магазина/маркетплейса.
 $request->clientTransaction = 'my-order-id-10_3';

 //платёжный пароль магазина/маркетплейса.
 $request->paymentPassword = '***********';

 $request->isPayerAmount = true;

 $request->description = 'Перечисление на банковские реквизиты организации(продавца)';

 //запрос на перевод средств
 //с расширенного счёта организации(продавца) на банковские реквизиты организации(продавца)
 $result = $monetaSdk->monetaService->Payment($request);

 if (!$result['id']) {
 throw new Exception(print_r($result, true));
 }

 echo "Запрос обработан.";

 foreach ($result['attribute'] as $key => $attribute) {
 if ('statusid' === $attribute['key']) {
 if ((new \Moneta\Types\OperationStatus())::SUCCEED !== $attribute['value']) {
 echo " Операция НЕ проведена полностью.";
 }
 break;
 }
 }

} catch (Exception $e) {
 echo "Ошибка:<br />";
 echo "<pre>" . $e->getMessage() . "</pre>";
}
```


Запросы маркетплейс отправляет в рамках интерфейса MONETA.MerchantAPI.


**Примечание: **Интерфейс MONETA.MerchantAPI представляет собой Web-сервис, описанный по спецификации Web Services Description Language (WSDL), использующий протокол Simple Object Access Protocol (SOAP) для передачи информации.