## Код для вставки виджета в iframe


```
// DEV окружение
<iframe
 src="https://fps-ui.dev.mnxsc.tech/withdrawal?frame=true&token={ONE_TIME_TOKEN}"
 style="
 width: 400px;
 height: 600px;
 border: 1px solid #CCC;
 border-radius: 10px">
</iframe>


// PROD окружение
<iframe
 src="https://fps-ui.prod.mnxsc.tech/withdrawal?frame=true&token={OONE_TIME_TOKEN"
 style="
 width: 400px;
 height: 600px;
 border: 1px solid #CCC;
 border-radius: 10px">
</iframe>
```


- Рекомендуемые размеры iframe: 400 x 600
- формирование ONE_TIME_TOKEN описано в разделе генерации токена партнера.


## Ограничения использования iframe


| Ограничение | Решение |
| --- | --- |
| Не работает вставка https iframe в http родителя. | Браузеры ограничивают возможности таких iframe, поэтому для тестов нужен https родитель. Например: https://localhost:8080 |


## Получение событий из iframe

Виджет отправляет родительской странице события, которые можно обработать в js коде:


```
// код на сайте:

window.addEventListener("message", receiveMessage, false);

function receiveMessage(event) {

 // событие от виджета
 if(event.origin === 'https://fps-ui.prod.mnxsc.tech'){

 const data = event.data || {};
 console.log(data.type);
 }
}
```


| Тип события | Описание |
| --- | --- |
| initialized | Виджет инициализирован |
| error | Произошла ошибка отображения виджета, при этом data.error будет содержать код ошибки |
| loggedOut | Пользователь завершил работу с виджетом |
| verificationFinished | Верификация пользователя завершена, при этом в поле data.status будет результат операции: 'SUCCESS' либо 'FAILED' |
| withdrawalFinished | Вывод завершен, при этом в поле data.status будет результат операции: 'SUCCESS' либо 'FAILED' |