## Примеры CSS стилей для виджета moneta.ru


​


Пример 1

Пример 1


Пример 2

Пример 2


Пример 3

Пример 3


```
html.widget .page-wrapper {
 width: 350px !important;
}

html.widget .page-wrapper form input[type="text"],
html.widget .page-wrapper form input[type="password"] {
 height: 32px !important;
}

html.widget .page-wrapper dl {
 margin-bottom: 0;
}

html.widget #tab-ps-selector {
 display: none;
}

html.widget #content {
 background: #ccc;
 width: 350px !important;
 height: 320px !important;
}

html.widget .form-error-wrapper {
 position: absolute;
 margin-top: 38px !important;
}

#cvc_hint {
 display: none;
}

.field-cardHolder {
 position: absolute;
 margin-top: 125px;
 display: none;
}

.field-cardNumber {
 margin-top: -10px;
}

.field-cardExpiration {
 margin-top: -10px;
}

.field-cardCVV2 {
 margin-top: -7px;
 margin-right: 0;
}

.field-cardCVV2 dt {
 text-align: right;
}

.field-cardCVV2 dd {
 float: right;
}

.field-cardCVV2 .form-error-wrapper {
 display: none;
}

.field-totalAmount {
 position: absolute;
 margin-top: 184px;
}

.field-ownerLogin {
 position: absolute;
 margin-top: 130px;
}

.field-ownerLogin .hint {
 display: none;
}

.field-description {
 display: none;
}

.h-buttons {
 margin-left: 192px;
 margin-top: 55px;
 position: absolute;
}

.verified-by-systems {
 margin-top: 96px !important;
}

html.widget .page-wrapper form select {
 padding: 0 4px;
}

.js {
 margin: 0 !important;
}

.oauth-splitter {
 display: none;
}

.oauth {
 display: none;
}
```


```
html.widget #tab-ps-selector {
 display: none;
}

html.widget #content {
 background: #f1f1f5;
}

html.widget .page-wrapper form input[type="text"],
html.widget .page-wrapper form input[type="password"] {
 height: 32px !important;
}

html.widget .page-wrapper dl {
 margin-bottom: 0;
}

html.widget .form-error-wrapper {
 position: absolute;
 margin-top: 38px !important;
}

.field-cardHolder {
 margin-left: 188px;
 width: 324px;
 background: #fff;
 padding-left: 13px;
 padding-top: 10px;
 border: 1px solid #00bb00;
 border-radius: 4px;
 display: none;
}

.field-ownerLogin {
 margin-left: 188px;
 width: 324px;
 background: #fff;
 margin-top: 15px;
 padding-left: 13px;
 padding-top: 10px;
 border: 1px solid #00bb00;
 border-radius: 4px;
}

.field-cardNumber {
 margin-left: 188px;
 width: 324px;
 background: #fff;
 margin-top: 15px;
 padding-left: 13px;
 padding-top: 10px;
 border-top: 1px solid #00bb00;
 border-left: 1px solid #00bb00;
 border-right: 1px solid #00bb00;
 border-top-left-radius: 4px;
 border-top-right-radius: 4px;
}

.field-cardExpiration {
 margin-left: 188px;
 width: 224px !important;
 background: #fff;
 padding-left: 13px;
 border-bottom: 1px solid #00bb00;
 border-left: 1px solid #00bb00;
 border-bottom-left-radius: 4px;
}

.field-cardCVV2 {
 width: 100px;
 background: #fff;
 border-bottom: 1px solid #00bb00;
 border-right: 1px solid #00bb00;
 border-bottom-right-radius: 4px;
}

.field-description {
 position: absolute;
 margin-top: 52px;
 width: 161px !important;
 text-align: center;
}

.field-description dt {
 display: none;
}

.field-description dd {
 width: 100%;
 height: 103px;
 text-align: center;
 display: flex;
 align-items: center;
 justify-content: center;
}

.field-totalAmount {
 position: absolute;
 margin-top: 15px;
 width: 161px !important;
}

.field-totalAmount dt {
 display: none;
}

.field-totalAmount dd {
 width: 100%;
 text-align: center;
 color: #0077cc;
 font-size: 23px;
 font-weight: bold;
}

.verified-by-systems {
 display: none;
}

.h-buttons {
 margin-top: -70px;
 position: absolute;
}

.h-buttons .form_button {
 width: 169px;
 height: 50px;
 font-size: 18px !important;
 color: #fff;
 background: #42aaff !important;
}

#additionalParameters_cardNumber {
 border-color: #fafafa;
 background: #fafafa;
 box-shadow: none;
}

#additionalParameters_cardHolder {
 border-color: #fafafa;
 background: #fafafa;
 box-shadow: none;
}

#additionalParameters_cardCVV2 {
 border-color: #fafafa;
 background: #fafafa;
 box-shadow: none;
}

#additionalParameters_ownerLogin {
 border-color: #fafafa;
 background: #fafafa;
 box-shadow: none;
}

#cardExpirationMonth {
 background: #fafafa;
 box-shadow: none;
}

#cardExpirationYear {
 background: #fafafa;
 box-shadow: none;
}

#cardtype, .card-type {
 margin: -22px -1px;
}

#cvc_hint {
 display: none;
}

.oauth-splitter {
 display: none;
}

.oauth {
 display: none;
}
```


```
html.widget #content {
 color: #fff;
 background: rgba(0, 0, 0, 0) url("https://moneta.ru/info/public/w/partnership/cardbg3.gif") repeat scroll 0 0;
}

html.widget #tab-ps-selector {
 display: none;
}

html.widget .verified-by-systems {
 display: none;
}

html.widget .page-wrapper form input[type="text"],
html.widget .page-wrapper form input[type="password"] {
 color: #000;
 height: 32px !important;
}

html.widget form select {
 height: 32px !important;
 color: #000;
 padding: 4px !important;
}

html.widget .tab-container {
 padding: 28px 17px;
}

.h-buttons {
 position: absolute;
 margin-top: 21px;
 color: #000;
}

.input-label {
 color: #fff;
}

.field-cardHolder {
 display: none;
}

.field-ownerLogin {
 display: none;
}

.field-description {
 display: none;
}

.field-totalAmount {
 position: absolute;
 font-weight: bold;
 margin-left: 113px;
 margin-top: 187px;
 color: #000;
}

.field-totalAmount .input-label {
 display: none;
}

.field-cardCVV2 {
 position: absolute;
 margin-left: 370px;
 margin-top: 52px;
}

.field-cardExpiration dd {
 display: flex;
 align-items: center;
}

#cvc_hint {
 display: none;
}

#additionalParameters_cardNumber {
 border: none;
 background: none;
 box-shadow: none;
}

#additionalParameters_cardHolder {
 border: none;
 background: none;
 box-shadow: none;
}

#additionalParameters_cardCVV2 {
 border: none;
 background: none;
 box-shadow: none;
}

#additionalParameters_ownerLogin {
 border: none;
 background: none;
 box-shadow: none;
}

#cardExpirationMonth {
 background: #aae3c9;
 box-shadow: none;
 margin-right: 5px;
 font-size: 15px;
}

#cardExpirationYear {
 background: #aae3c9;
 box-shadow: none;
 margin-left: 5px;
 font-size: 15px;
}

#cardtype, .card-type {
 margin: 90px 77px;
}

.oauth-splitter {
 display: none;
}

.oauth {
 display: none;
}
```