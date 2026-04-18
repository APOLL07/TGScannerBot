# TGScanner — Subagents Index

Проект разбит на 4 агента. Каждый описан в отдельном файле.

## Порядок запуска

```
[Агент 1: Foundation]  ← запустить первым, дождаться завершения
        │
        ├─── [Агент 2: Backend]   ← запустить параллельно
        └─── [Агент 3: Frontend]  ← запустить параллельно
                │
                └─── [Агент 4: Integration] ← запустить последним
```

## Файлы агентов

| Агент | Файл | Фаза | Задачи |
|-------|------|------|--------|
| Foundation | [docs/agents/agent-1-foundation.md](agents/agent-1-foundation.md) | 1 (первый) | Task 1, 2, 3 |
| Backend | [docs/agents/agent-2-backend.md](agents/agent-2-backend.md) | 2 (параллельно) | Task 4, 5 |
| Frontend | [docs/agents/agent-3-frontend.md](agents/agent-3-frontend.md) | 2 (параллельно) | Task 6, 7, 8, 9, 10 |
| Integration | [docs/agents/agent-4-integration.md](agents/agent-4-integration.md) | 3 (последний) | Task 11, 12 |

## Полный план реализации

`docs/superpowers/plans/2026-04-18-tgscanner.md`

## Спецификация

`docs/superpowers/specs/2026-04-18-tgscanner-design.md`
