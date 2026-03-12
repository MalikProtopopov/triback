# Стандарты кода и архитектуры проекта

Этот документ описывает принципы организации кода, соглашения и стандарты, используемые в проекте. Документ универсален и может быть применен к любым проектам.

---

## 📁 Архитектура проекта: Feature-Sliced Design (FSD)

Проект следует принципам **Feature-Sliced Design** — методологии для организации frontend-приложений.

### Структура слоев:

```
src/
├── app/                    # Слой приложения (страницы, роуты, глобальные стили)
├── widgets/                # Виджеты (самостоятельные блоки UI)
├── features/               # Фичи (функциональность с бизнес-логикой)
├── entities/               # Сущности (бизнес-модели)
├── shared/                 # Переиспользуемый код (UI-kit, utils, config)
└── providers/              # Провайдеры контекста и глобального состояния
```

### Правила слоев:

1. **Направление зависимостей**: снизу вверх
   - `shared` ← `entities` ← `features` ← `widgets` ← `app`
   - Верхние слои могут использовать нижние, но не наоборот

2. **Изоляция**: каждый модуль изолирован и имеет публичный API через `index.ts`

3. **Структура сущности/фичи**:
   ```
   feature-name/
   ├── api/           # API-методы
   ├── model/         # Хуки, стейт, бизнес-логика
   ├── ui/            # UI-компоненты
   ├── config/        # Конфигурация
   ├── lib/           # Вспомогательные функции
   ├── types.ts       # TypeScript типы
   └── index.ts       # Публичный API
   ```

---

## 🎨 Стилизация: TailwindCSS v4

### Подход к стилям

1. **Utility-first**: используем утилитарные классы Tailwind
2. **CSS Variables**: все цвета и темизация через CSS-переменные
3. **Контейнер**: используем класс `.container` для ограничения ширины контента

### CSS Variables (Дизайн-токены)

```css
:root {
  /* Фоны */
  --color-bg-primary: #0c0c0e;
  --color-bg-secondary: #151518;
  --color-bg-hover: #1d1d21;
  
  /* Границы */
  --color-border: #222225;
  
  /* Текст */
  --color-text-primary: #ffffff;
  --color-text-secondary: #b0b0b5;
  --color-text-muted: #71717a;
  
  /* Акценты */
  --color-accent-primary: #ffcd33;
  --color-accent-hover: #ffd84d;
  --color-accent-contrast: #332800;
  
  /* Семантические цвета */
  --color-success: #4ade80;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
}
```

### Использование классов Tailwind

```tsx
// ✅ Правильно: сокращенные имена для CSS-переменных
<div className="bg-bg-secondary text-text-primary border-border">

```

### Правила именования классов

1. **Порядок классов**: используем `prettier-plugin-tailwindcss` для автосортировки
2. **Условные классы**: группируем логически связанные классы
3. **Адаптивность**: mobile-first подход
   ```tsx
   <div className="text-sm md:text-base lg:text-lg">
   ```

---

## 📝 TypeScript

### Строгость настроек

```json
{
  "strict": true,
  "noImplicitAny": true,
  "strictNullChecks": true,
  "noUncheckedIndexedAccess": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "exactOptionalPropertyTypes": true
}
```

### Правила типизации

1. **Явная типизация**: всегда указываем типы для функций и переменных
   ```ts
   // ✅ Правильно
   const getUser = async (id: string): Promise<User> => { }
   
   // ❌ Неправильно
   const getUser = async (id) => { }
   ```

2. **Избегаем `any`**: используем `unknown` или специфичные типы
   ```ts
   // ✅ Правильно
   const data: unknown = await response.json();
   
   // ❌ Неправильно
   const data: any = await response.json();
   ```

3. **Type vs Interface**:
   - `type` — для union types, примитивов, утилитарных типов
   - `interface` — для объектов и классов с возможностью расширения

4. **Именование типов**:
   - Схемы API: `EntityNameResponseSchema`, `EntityNameRequestSchema`
   - Props компонентов: `ComponentNameProps`
   - Конфигурация: `ConfigName`

---

## 🧩 Компоненты (React)

### Структура компонента

```tsx
// 1. Импорты (сторонние библиотеки → внутренние модули)
import { useState } from "react";
import Link from "next/link";

import { Button } from "@/shared/ui";
import type { UserProps } from "./types";

// 2. Типы/интерфейсы (если не вынесены в отдельный файл)
interface ComponentProps {
  title: string;
  onSubmit: (data: FormData) => void;
}

// 3. Компонент
export const Component = ({ title, onSubmit }: ComponentProps) => {
  // Hooks
  const [state, setState] = useState(false);
  
  // Обработчики
  const handleClick = () => {
    setState(true);
  };
  
  // Render
  return (
    <div>
      {/* JSX */}
    </div>
  );
};
```

### Правила компонентов

1. **Именование**:
   - PascalCase для компонентов: `UserCard`, `LoginForm`
   - camelCase для функций: `handleSubmit`, `fetchData`

2. **Экспорт**:
   - Named export для компонентов: `export const Button`
   - Реэкспорт через `index.ts` в папке модуля

3. **Props**:
   - Всегда типизируем через интерфейс
   - Деструктуризация props в параметрах функции

4. **"use client"**: только там, где нужны клиентские хуки (useState, useEffect)

---

## 🔌 API и Data Fetching

### Архитектура API

```
entities/user/
├── api/
│   └── userApi.ts       # API-методы
├── model/
│   └── useUser.ts       # React Query hooks
└── types.ts             # Response/Request типы
```

### API Client (Axios)

```ts
// shared/api/api.ts
class ApiClient {
  private instance: AxiosInstance;
  
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.instance.get(url, config);
    return response.data;
  }
  
  async post<TRequest, TResponse>(
    url: string,
    data?: TRequest,
    config?: AxiosRequestConfig
  ): Promise<TResponse> {
    const response: AxiosResponse<TResponse> = 
      await this.instance.post(url, data, config);
    return response.data;
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
```

### API-методы

```ts
// entities/user/api/userApi.ts
import { apiClient } from "@/shared/api";
import type { UserResponseSchema } from "../types";

export const userApi = {
  getById: async (id: string): Promise<UserResponseSchema> => {
    return apiClient.get<UserResponseSchema>(`/users/${id}`);
  },
  
  create: async (data: UserCreateRequest): Promise<UserResponseSchema> => {
    return apiClient.post<UserCreateRequest, UserResponseSchema>("/users", data);
  },
};
```

### React Query Hooks

```ts
// entities/user/model/useUser.ts
import { useQuery, useMutation } from "@tanstack/react-query";
import { userApi } from "../api/userApi";

export const userKeys = {
  all: ["users"] as const,
  detail: (id: string) => [...userKeys.all, id] as const,
};

export const useUser = (id: string) => {
  return useQuery({
    queryKey: userKeys.detail(id),
    queryFn: () => userApi.getById(id),
    enabled: !!id,
  });
};

export const useCreateUser = () => {
  return useMutation({
    mutationFn: userApi.create,
  });
};
```

---

## 🎯 State Management

### Локальное состояние

**React Hook Form** — для форм:
```tsx
import { useForm } from "react-hook-form";

const { control, handleSubmit, formState: { errors } } = useForm({
  mode: "onChange",
  defaultValues: { name: "" },
});
```

**useState** — для простого UI-состояния:
```tsx
const [isOpen, setIsOpen] = useState(false);
```

### Серверное состояние

**React Query** — для данных с сервера:
```tsx
const { data, isLoading, error } = useQuery({
  queryKey: ["users"],
  queryFn: fetchUsers,
});
```

### Глобальное состояние

**Zustand** — для клиентского глобального стейта:
```ts
// store/useCartStore.ts
import { create } from "zustand";

interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
}

export const useCartStore = create<CartStore>((set) => ({
  items: [],
  addItem: (item) => set((state) => ({ 
    items: [...state.items, item] 
  })),
}));
```

---

## 🛣 Роутинг и навигация

### Структура роутов

```ts
// shared/config/routes.ts
export const ROUTES = {
  HOME: "/",
  PROFILE: (id: string) => `/profile/${id}`,
  SETTINGS: "/settings",
} as const;
```

### Использование

```tsx
import Link from "next/link";
import { ROUTES } from "@/shared/config";

<Link href={ROUTES.PROFILE(userId)}>Profile</Link>
```

---

## 🔧 Конфигурация

### API Endpoints

```ts
// shared/config/apiEndpoints.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000";

export const API_ENDPOINTS = {
  USER: {
    LIST: "/users",
    BY_ID: (id: string) => `/users/${id}`,
  },
  PRODUCT: {
    LIST: "/products",
  },
} as const;
```

### Импорты (Path Aliases)

```json
{
  "paths": {
    "@/*": ["./src/*"],
    "@/components/*": ["./src/components/*"],
    "@/types/*": ["./src/shared/types/*"]
  }
}
```

---

## 🛠 Утилиты и хелперы

### Организация

```
shared/
├── lib/
│   ├── format/
│   │   ├── toPriceFormat.ts
│   │   └── index.ts
│   └── validation/
│       ├── isEmail.ts
│       └── index.ts
└── config/
    └── cn.ts              # classnames utility
```

### cn() — Utility для классов

```ts
// shared/config/cn.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Использование:
```tsx
import { cn } from "@/shared/config";

<div className={cn(
  "base-class",
  isActive && "active-class",
  className
)} />
```

---

## 📦 Зависимости

### Основные библиотеки

```json
{
  "dependencies": {
    "next": "15.x",                          // React-фреймворк
    "react": "19.x",                         // UI-библиотека
    "axios": "^1.13.1",                      // HTTP-клиент
    "@tanstack/react-query": "^5.62.7",      // Серверное состояние
    "react-hook-form": "^7.66.0",            // Формы
    "zustand": "^5.0.8",                     // Глобальное состояние
    "zod": "^4.1.12",                        // Валидация схем
    "clsx": "^2.1.1",                        // Условные классы
    "tailwind-merge": "^3.3.1"               // Слияние Tailwind классов
  }
}
```

---

## 📏 ESLint правила

### Строгие правила TypeScript

```js
{
  "@typescript-eslint/no-explicit-any": "error",
  "@typescript-eslint/no-unsafe-assignment": "error",
  "@typescript-eslint/no-unused-vars": ["error", {
    "argsIgnorePattern": "^_",
    "varsIgnorePattern": "^_"
  }],
  "@typescript-eslint/prefer-nullish-coalescing": "warn",
  "@typescript-eslint/prefer-optional-chain": "error",
}
```

### Общие правила кода

```js
{
  "no-console": ["warn", { "allow": ["warn", "error"] }],
  "no-debugger": "error",
  "prefer-const": "error",
  "prefer-arrow-callback": "error",
  "prefer-template": "error",
  "eqeqeq": ["error", "always"],
}
```

### React правила

```js
{
  "react-hooks/rules-of-hooks": "error",
  "react-hooks/exhaustive-deps": "warn",
  "react/jsx-key": "error",
  "react/no-danger": "warn",
}
```

---

## 🎨 Prettier конфигурация

```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100,
  "plugins": [
    "prettier-plugin-tailwindcss",
    "@trivago/prettier-plugin-sort-imports"
  ],
  "importOrder": [
    "^react",
    "^next",
    "<THIRD_PARTY_MODULES>",
    "^@/(.*)$",
    "^[./]"
  ]
}
```

**Правила импортов**:
1. React/Next.js библиотеки
2. Сторонние библиотеки
3. Внутренние модули (@/)
4. Относительные импорты

---

## 📂 Файловая структура модуля

### Пример полной структуры фичи

```
features/auth/
├── api/
│   └── authApi.ts           # API-методы аутентификации
├── model/
│   ├── useAuth.ts           # React Query hooks
│   └── useAuthStore.ts      # Zustand store (если нужен)
├── ui/
│   ├── LoginForm.tsx        # Компонент формы входа
│   └── RegisterForm.tsx     # Компонент формы регистрации
├── lib/
│   └── validation.ts        # Схемы валидации (Zod)
├── config/
│   └── constants.ts         # Константы модуля
├── types.ts                 # TypeScript типы
└── index.ts                 # Публичный API модуля
```

### index.ts — Публичный API

```ts
// features/auth/index.ts
export { authApi } from "./api/authApi";
export { useAuth, useLogin, useRegister } from "./model/useAuth";
export { LoginForm, RegisterForm } from "./ui";
export type { LoginRequest, AuthResponse } from "./types";
```

---

## ✅ Чек-лист для нового компонента

- [ ] Создана папка с правильной структурой (api/model/ui/types.ts/index.ts)
- [ ] Все типы явно указаны
- [ ] Props деструктурированы и типизированы
- [ ] Компонент экспортируется через index.ts
- [ ] Используются CSS-переменные через короткие Tailwind-классы
- [ ] Импорты отсортированы (prettier)
- [ ] Нет `any`, `console.log`, `debugger`
- [ ] ESLint не показывает ошибок
- [ ] Компонент следует принципам FSD (правильный слой)

---

## 🚀 Команды разработки

```bash
# Разработка
yarn dev                 # Запуск dev-сервера (Turbopack)

# Сборка
yarn build              # Production сборка
yarn start              # Запуск production-сервера

# Качество кода
yarn lint               # Проверка ESLint
yarn format             # Форматирование Prettier
```

---

## 💡 Лучшие практики

### 1. Composition over Inheritance
```tsx
// ✅ Хорошо: композиция через children
const Card = ({ children }) => <div className="card">{children}</div>;

// ❌ Плохо: наследование
class Card extends BaseComponent { }
```

### 2. Маленькие, фокусированные функции
```tsx
// ✅ Хорошо
const validateEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
const validatePassword = (pass: string) => pass.length >= 8;

// ❌ Плохо
const validateForm = (data) => { /* 100 строк кода */ }
```

### 3. Избегаем prop drilling
```tsx
// ✅ Хорошо: используем Context или Zustand
const value = useThemeStore(state => state.theme);

// ❌ Плохо: передача через 5 уровней
<A theme={theme}>
  <B theme={theme}>
    <C theme={theme} />
  </B>
</A>
```

### 4. Ранний return
```tsx
// ✅ Хорошо
if (!user) return <Loading />;
if (error) return <Error />;
return <Content />;

// ❌ Плохо
if (user) {
  if (!error) {
    return <Content />;
  }
}
```

### 5. Descriptive naming
```tsx
// ✅ Хорошо
const isUserAuthenticated = checkAuthStatus();
const fetchUserProfile = async (userId: string) => { };

// ❌ Плохо
const flag = check();
const get = async (id: string) => { };
```

---

## 📖 Ресурсы

- [Feature-Sliced Design](https://feature-sliced.design/)
- [Next.js Documentation](https://nextjs.org/docs)
- [TailwindCSS v4](https://tailwindcss.com/)
- [React Query](https://tanstack.com/query/latest)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Версия документа**: 1.0  
**Последнее обновление**: December 2025

