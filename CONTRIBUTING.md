# Contributing to News Dispatch

## Основные правила

- Всё, что попадает в репозиторий, должно быть **public-safe** (см. PUBLICATION_BOUNDARY.md).
- Новые диспатчи публикуются только со статусом `published`.
- Используй `tools/core.py` для общих функций.
- Перед коммитом запускай `python tools/validate_published.py` (если есть).

## Как добавить новый сигнал / dispatch

1. Запусти Daily Radar
2. Используй `python tools/synthesize_dispatch.py --from-radar --stream ai`
3. Отредактируй черновик
4. Проверь и переведи в `status: published`
5. Создай PR

## Структура

- `tools/` — скрипты и утилиты
- `dispatches/` — готовые публикации
- `signals/` — сырые сигналы
- `core.py` — используй в новых инструментах

Вопросы и предложения — через Issues.
