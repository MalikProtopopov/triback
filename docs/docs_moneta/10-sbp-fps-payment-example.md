Запрос формируется согласно интерфейсу MONETA.MerchantAPI.


```
{
 "Envelope": {
 "Header": {
 "Security": {
 "UsernameToken": {
 "Username": "USERNAME",
 "Password": "PASSWORD"
 }
 }
 },
 "Body": {
 "PaymentRequest": {
 "payer": "номер ЭСП МОНЕТА.РУ",
 "payee": "0operationId",
 "amount": "10",
 "isPayerAmount": false,
 "paymentPassword": "010101010",
 "operationInfo": {
 "attribute": [
 {
 "key": "SECUREDFIELD:unsBo_79",
 "value": "1234123452345345645674567578"
 }
 ] }

 }
 }
 }
}
```