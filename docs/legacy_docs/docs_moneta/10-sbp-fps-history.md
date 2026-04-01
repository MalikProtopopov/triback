Сервис Moneta SBP/FPS позволяет просмотреть историю транзакций. История отображается в убывающем по дате создания транзакции порядке и позволяет посмотреть детальную информацию по выбранной транзакции на отдельной странице. Данные в истории обновляются автоматически с определенным периодом. Для отображения истории необходимо:

- сформировать и подписать токен доступа;
- открыть URL "<BASE_URL>/wallet/wallets/transactions", передав сформированный токен в качестве параметра.


```
// DEV окружение
<iframe
 src="https://fps-ui.dev.mnxsc.tech/wallet/wallets/transactions?frame=true&token={ONE_TIME_TOKEN}"
 style="
 width: 400px;
 height: 600px;
 border: 1px solid #CCC;
 border-radius: 10px">
</iframe>


// PROD окружение
<iframe
 src="https://fps-ui.prod.mnxsc.tech/wallet/wallets/transactions?frame=true&token={ONE_TIME_TOKEN}"
 style="
 width: 400px;
 height: 600px;
 border: 1px solid #CCC;
 border-radius: 10px">
</iframe>
```