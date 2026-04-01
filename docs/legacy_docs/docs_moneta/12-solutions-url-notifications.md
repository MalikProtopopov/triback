Для настройки URL-уведомления необходимо отправить URL вашего обработчика на mp@payanyway.ru

URL-уведомления отправляются методом POST.

Content-type: application/x-www-form-urlencoded.

Encoding: UTF-8

На адрес вашего обработчика Система "МОНЕТА.РУ" будет направлять следующие уведомления:

`CREATE_UNIT` - Создание дочернего юнита.


**Примечание: **NOTIFICATION=CREATE_UNIT&ACTION=CREATE_UNIT&UNIT_ID=…&PARENT_ID=…&INN=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID +PROFILE_ID+OBJECT_ID+ключ)


`EDIT_CONTRACT` - Изменение статуса договора.

Статусы:

- `INACTIVE` - статус договора после регистрации в Системе "МОНЕТА.РУ"
- `ACTIVE` - статус договора после перевода юнита продавца из группы **Зарегистрированные клиенты** в **Рабочую группу**.
- `RESTRICTED` - статус договора после перевода из **Рабочей группы** в **Клиенты без заявления**.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_CONTRACT&UNIT_ID=…&CONTRACT_ID=…&OLD_STATUS=…&NEW_STATUS=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+CONTRACT_ID+OLD_STATUS+NEW_STATUS+ключ)


`CREATE_ACCOUNT` - Создание счетов.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=CREATE_ACCOUNT&UNIT_ID=…&ACCOUNT_ID=…&ACCOUNT_TYPE=…&ACCOUNT_CREDIT_EXTID=…& ACCOUNT_DEBIT_EXTID=…&ACCOUNT_NUMBER=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+ACCOUNT_ID+ACCOUNT_TYPE+ключ)


`SEND_AGREEMENT` - Продавцу сформировано Заявление о присоединении к Договору.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=SEND_AGREEMENT&UNIT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID +PROFILE_ID+OBJECT_ID+ключ)


`EDIT_PROFILE` - Редактирование Основного профиля.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_PROFILE&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID +PROFILE_ID+OBJECT_ID+ключ)


`MOVE_UNIT` - Перенос юнита. PARENT_ID - новый родительский юнит.


**Примечание: **NOTIFICATION=PROFILE_UPDATE &ACTION=MOVE_UNIT&UNIT_ID=…&PARENT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PARENT_ID+ключ)


`CREATE_BANK_ACCOUNT` - Создание банковских реквизитов.


**Примечание: **NOTIFICATION=PROFILE_UPDATE &ACTION=CREATE_BANK_ACCOUNT&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)


`EDIT_BANK_ACCOUNT` - Редактирование банковских реквизитов.


**Примечание: **NOTIFICATION=PROFILE_UPDATE &ACTION=EDIT_BANK_ACCOUNT&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)


`CREATE_LEGAL_INFO` - Создание юридических реквизитов.


**Примечание: **NOTIFICATION=PROFILE_UPDATE &ACTION=CREATE_LEGAL_INFO &UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)


`EDIT_LEGAL_INFO` - Редактирование юридических реквизитов.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_LEGAL_INFO&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)


`CREATE_DOCUMENT` - Создание документа.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=CREATE_DOCUMENT&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)


`EDIT_DOCUMENT` - Редактирование документа.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_DOCUMENT&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)


`CREATE_FOUNDER` - Создание Учредителя. `PROFILE_ID` равен `OBJECT_ID`.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=CREATE_FOUNDER&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)


`EDIT_FOUNDER` - Редактирование Учредителя. `PROFILE_ID` равен `OBJECT_ID`.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_FOUNDER&UNIT_ID=…&PROFILE_ID=…&OBJECT_ID=…&MNT_SIGNATURE=md5(ACTION+UNIT_ID+PROFILE_ID+OBJECT_ID+ключ)


`EDIT_PROFILE` - Обновление профиля.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=EDIT_PROFILE&UNIT_ID=…&UPDATE_DETAILS=…&MNT_SIGNATURE= md5(ACTION+UNIT_ID+UPDATE_DETAILS+ключ)


`CONDITION_REJECTED` - Продавец не прошёл проверку соответствия ПиУ.


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=CONDITION_REJECTED&UNIT_ID=…&PAYEE_DETAILS=…&PAYER_DETAILS=…&SITE_DETAILS=…&PAYMENT_INFO_DETAILS=…&CORRECT_DATA_DETAILS=…&MNT_SIGNATURE=… ACTION+UNIT_ID+ключ


`RECEIVED_AGREEMENT` - получено заявление о присоединении к Договору


**Примечание: **NOTIFICATION=PROFILE_UPDATE&ACTION=RECEIVED_AGREEMENT&UNIT_ID=…&PAYEE_DETAILS=&PAYER_DETAILS=&SITE_DETAILS=&PAYMENT_INFO_DETAILS=&CORRECT_DATA_DETAILS=&MNT_SIGNATURE=…


На уведомление следует ответить http-status=200 или строчкой: `SUCCESS`

Если адрес обработчика не может быть вызван по какой-либо причине, либо в ответе придёт не `SUCCESS`, то уведомление будет направлено повторно. Всего 8 раз в течении суток, с увеличивающейся периодичностью: 12 минут, 24 минуты, 48 минут и т. д.