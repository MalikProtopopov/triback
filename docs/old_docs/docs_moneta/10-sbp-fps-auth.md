## Общая информация

Для инициализиции виджета Moneta SBP/FPS маркетплейсу необходимо передать одноразовый токен безопасности, в котором надежно зашифрована вся необходимая информация для проведения перевода. Токен безопасности должен формироваться на стороне маркетплейса, по указанным ниже правилам.

## Формирование токена и подписи

Предварительные условия:

- Необходимо пройти процедуру регистрации маркетплейса и получить ApiKey и ApiSecret.
- Необходимо установить доверительные отношения с сервисом Moneta SBP/FPS.


Для реализации алгоритма формирования единовременного токена использованы следующие стандарты:

- RFC 3986 Uniform Resource Identifier (URI): Generic Syntax.
- RFC 2104 HMAC: Keyed-Hashing for Message Authentication.
- RFC 4648 The Base16, Base32, and Base64 Data Encodings.


Токен состоит из 2-х частей:

- Информационное сообщение, содержащее ключевую информацию о маркетплейсе и Пользователе ЭСП МОНЕТА.РУ, служебную информацию по переводу.
- Подпись/Хэш от информационного сообщения из п.1, и использованием заранее полученного общего секрета - `ApiSecret`.


### Формирование информационного сообщения

Информационное сообщение состоит из набора ключ-значение, которые закодированы в соответствии с правилами URL-кодирования строк по RFC 3986. Пример:

```
key1=someKey&key2=Some%20Key2&extraKey=100500

```

Ниже приведен набор обязательных параметров, которые необходимо указать при формировании информационного сообщения (ключи должны следовать в отсортированном порядке, как в таблице ниже):


| Ключ | Описание | Тип | Пример |
| --- | --- | --- | --- |
| cid | Идентификатор операции на стороне маркетплейса | String | i-17-203112 |
| cidExpireAt | Дата/время до которой можно провести оплату (в EpohMills) | Число | 1610464610097 |
| key | ApiKey полученный при регистрации в MonetaId | Url Encoded String | site-x |
| nonce | Число, использующееся для невозможности повторного использования одного и того же токена (см. ниже) | Число | 10201010 |
| unitId | Номер профиля/юнита пользователя ЭСП МОНЕТА.РУ | Число | 987654321 |
| accountId | Номер ЭСП МОНЕТА.РУ для списания средств | Число | 1230567 |
| callbackUrl | Опциональный параметр для demo окружения: Возможность задать тестовый callback url, отличный от того, что задан партнеру при регистрации. | Url Encoded String | http%3A%2F%2Fya.ru |


При формировании nonce удобно использовать текущее время в секундах на момент формирования токена. Каждый новый nonce в новом токене, формирующийся для данного unitId должен быть строго больше предыдущего для данного юнита (т.е. nonce должен строго монотонно возрастать), иначе он будет отброшен как некорректный.

Пример итогового информационного сообщения:

```
cid=i103020&cidExpireAt=1601375568244&key=partner123&nonce=1601375468244&unitId=987654321&accountId=1230567

```

### Формирование подписи

После того, как информационное сообщение сформировано, необходимо вычислить подпись/хеш с использованием общего секрета - ApiSecret.

Алгоритм формирования:

- Вычислить HMAC-SHA512 хеш используя пару (информационное сообщение, секрет).
- Полученный массив байт перевести в строку в шестнадцатеричном представлении.


```
// message - инф. сообщение
// secret - секрет/apiSecret

signatureBytes = hmac_sha512(message, secret)
signatureString = bytesToHex(signatureBytes)
```


После того, как подпись в виде hex-строки сформирована, необходимо добавить ее к информационному сообщению с ключом signature:

```
cid=i103020cidExpireAt=1601375568244&key=partner123&nonce=1601375468244&unitId=987654321&accountId=1230567&signature=7d7b968768f664bcdbd67bbd4e3f59347b300226734ade68bed660ab7794522fe0e3e66ecdb211f746dae1c44681a306ee221f8706c63195607e525e979360

```

Финальным шагом необходимо полученную строку (информационное сообщение + подпись) закодировать при помощи base64, использовать при перенаправлении на виджет Moneta SBP/FPS.


```
// СЕРВЕР
// на стороне сервера формируем итоговый токен
message = "cid=i103020cidExpireAt=1601375568244&key=partner123&nonce=1601375468244&unitId=987654321&accountId=1230567&signature=7d7b968768f664bcdbd67bbd4e3f59347b300226734ade68bed660ab7794522fe0e3e66ecdb211f746dae1c44681a306ee221f8706c63195607e525e979360"
token = base64(message)

// БРАУЗЕР КЛИЕНТА
// делаем редирект в браузере клиента на указанный адрес с этим токеном

// DEV окружение
https://fps-ui.dev.mnxsc.tech/?token={{token}}

// PROD окружение
https://fps-ui.prod.mnxsc.tech/?token={{token}}
```


### Примеры кода для формирования токена


```
$secretKey = "secretKey";
$cid = "i103020";
$cidExpireAt = 1601375568244;
$key = "partner123";
$nonce = time();
$unitId = 987654321;
$accountId = 1230567;

$infoMessage = "cid=" . $cid . "&cidExpireAt=" . $cidExpireAt . "&key=" . $key . "&nonce=" . $nonce . "&unitId=" . $unitId . "&accountId" . $accountId;
$signatureString = hash_hmac("sha512", $infoMessage, $secretKey);

$token = base64_encode($infoMessage . "&signature=" . $signatureString);
```


```
const SECRET_KEY = 'secretKey';
const cid = "i103020";
const cidExpireAt = 1601375568244;
const key = 'partner123';
const nonce = Date.now();
const unitId = 987654321;
const accountId = 1230567;

const urlEncodedParams =
 'cid='+encodeURIComponent(cid)
 +'&cidExpireAt='+encodeURIComponent(cidExpireAt)
 +'&key='+encodeURIComponent(key)
 +'&nonce='+encodeURIComponent(nonce)
 +'&unitId='+encodeURIComponent(unitId)
 +'&accountId='+encodeURIComponent(accountId);
const signature = CryptoJS.HmacSHA512(urlEncodedParams, SECRET_KEY);
const signatureHex = CryptoJS.enc.Hex.stringify(signature);
const finalParams = urlEncodedParams + '&signature='+encodeURIComponent(signatureHex);

const token = CryptoJS.enc.Base64.stringify(CryptoJS.enc.Utf8.parse(finalParams));
```