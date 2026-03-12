# Frontend Rules — AI Coding Guide

> Этот файл используется как контекст/rules при работе с AI-ассистентом (Cursor, Claude).
> Подключай его к проекту чтобы AI следовал единым стандартам.

---

## Стек

| Категория | Технология |
|-----------|-----------|
| Фреймворк | Next.js 15, React 19 |
| Язык | TypeScript (strict mode) |
| Стили | TailwindCSS v4, CSS-переменные |
| Серверный стейт | React Query (TanStack Query) |
| Клиентский стейт | Zustand |
| Формы | React Hook Form + Zod |
| HTTP | Axios |
| Утилиты | clsx, tailwind-merge |

---

## Архитектура: Feature-Sliced Design (FSD)

Слои (зависимости только снизу вверх):

```
app -> widgets -> features -> entities -> shared
```

### Структура фичи

```
src/features/user-profile/
  api/            # API-функции (useQuery, useMutation)
  model/          # Хуки, стейт, бизнес-логика
  ui/             # React-компоненты
  config/         # Константы, конфиги
  lib/            # Хелперы
  types.ts        # Типы
  index.ts        # Публичный API (реэкспорт)
```

Правило: импортировать из фичи только через `index.ts`, не из внутренних файлов.

---

## TypeScript

- **strict mode** включён всегда
- Запрещён `any` — использовать `unknown` + type guards
- Интерфейсы для объектов: `interface Props { ... }`
- Типы для union/utility: `type Status = "active" | "inactive"`
- Все props компонентов типизированы
- Возвращаемые типы API-функций явно указаны

```typescript
// Хорошо
interface UserCardProps {
  user: User;
  onEdit: (id: string) => void;
}

// Плохо
const UserCard = ({ user, onEdit }: any) => ...
```

---

## Компоненты

- **Named exports** (не default export)
- `"use client"` только в компонентах с интерактивностью (useState, useEffect, обработчики)
- Серверные компоненты по умолчанию
- Композиция через `children`, не через пропс-drilling
- Один компонент на файл

```typescript
// components/Button.tsx
"use client";

interface ButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
  onClick?: () => void;
  disabled?: boolean;
}

export function Button({ children, variant = "primary", onClick, disabled }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "rounded-lg px-4 py-2 font-medium transition-colors",
        variant === "primary" && "bg-primary text-white hover:bg-primary/90",
        variant === "secondary" && "border border-gray-300 hover:bg-gray-50",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      {children}
    </button>
  );
}
```

---

## Стили (Tailwind)

- Utility-first подход, минимум кастомного CSS
- `cn()` хелпер для условных классов:

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- CSS-переменные для брендинга (цвета, логотип):

```css
:root {
  --color-primary: #1a5276;
  --color-primary-light: #1a527620;
}
```

- Адаптивность: mobile-first (`sm:`, `md:`, `lg:`)

---

## API-слой

### Axios instance

```typescript
// src/shared/api/client.ts
import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// Interceptor: auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor: error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login or refresh token
    }
    return Promise.reject(error);
  }
);
```

### Типизированные API-функции

```typescript
// src/features/users/api/getUsers.ts
import { api } from "@/shared/api/client";
import { useQuery } from "@tanstack/react-query";

interface UsersResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
}

export function useUsers(page = 1) {
  return useQuery({
    queryKey: ["users", page],
    queryFn: () => api.get<UsersResponse>("/users", { params: { page } }).then((r) => r.data),
  });
}
```

---

## Стейт

### React Query — серверные данные

- `useQuery` для GET-запросов
- `useMutation` для POST/PATCH/DELETE
- Invalidate кэш после мутации
- `staleTime` для контроля перезапросов

### Zustand — клиентский стейт

```typescript
// src/shared/store/auth.ts
import { create } from "zustand";

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  setToken: (token) => set({ token }),
  logout: () => {
    set({ token: null });
    localStorage.removeItem("access_token");
  },
}));
```

### React Hook Form + Zod — формы

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const schema = z.object({
  email: z.string().email("Некорректный email"),
  password: z.string().min(8, "Минимум 8 символов"),
});

type FormData = z.infer<typeof schema>;

export function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = (data: FormData) => { /* ... */ };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register("email")} />
      {errors.email && <span>{errors.email.message}</span>}
      {/* ... */}
    </form>
  );
}
```

---

## Паттерны

- **Loading states:** скелетоны или спиннеры через `isLoading` из React Query
- **Error states:** fallback UI, toast-уведомления
- **Optimistic updates:** через `onMutate` в useMutation
- **Debounced search:** `useDebouncedValue` хук (300ms)
- **Пагинация:** курсорная или offset, компонент `Pagination`
- **Empty states:** отдельный UI для "нет данных"

---

## Линтинг и форматирование

### ESLint

- `no-explicit-any`: error
- `no-console`: warn (удалять перед коммитом)
- `prefer-optional-chaining`: error
- `prefer-nullish-coalescing`: error

### Prettier

- `prettier-plugin-tailwindcss` для сортировки классов
- Порядок импортов: React -> сторонние -> `@/` алиасы -> относительные

### Import aliases

```json
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

---

## Чек-лист для AI

При создании нового компонента/фичи убедись что:

- [ ] TypeScript strict, нет `any`
- [ ] Компонент типизирован (Props interface)
- [ ] `"use client"` только если нужна интерактивность
- [ ] Стили через Tailwind + `cn()`, не inline styles
- [ ] API через React Query (useQuery/useMutation)
- [ ] Формы через React Hook Form + Zod
- [ ] Loading и error states обработаны
- [ ] Импорты через `@/` алиасы
- [ ] Файл экспортирует через `index.ts` фичи
