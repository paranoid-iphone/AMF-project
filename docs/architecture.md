# Архитектурный контекст

## Статус

**Approved initial architecture.** Логические границы и основной технологический стек утверждены. Конкретные cloud/AI/object-storage providers остаются открытыми. Feature-specific contracts фиксируются в specifications.

Последнее обновление: 2026-10-02.

## Обзор системы

Продукт — веб-приложение для подготовки и оценки инвестиционных проектов. Первый продуктовый контур работает с новым проектом/SPV и включает:

- аккаунт заявителя;
- проекты и черновики анкет;
- загрузку PDF/DOCX;
- извлечение данных с помощью AI;
- подтверждение ответов пользователем;
- детерминированный score engine;
- отдельный слой документальной подтверждённости;
- отдельный слой risk flags и hard stops;
- AI-объяснения и рекомендации;
- целевой административный workflow проверки и публикации.

Инвесторский marketplace не входит в первый milestone.

## Основной принцип оценки

```text
Questionnaire ─→ A: project quality/readiness
Documents     ─→ B: evidence level
Risk rules    ─→ warnings / hard stops
AI            ─→ extraction / matching / conflicts / explanations
Admin         ─→ verification / conflict resolution / publish decision
```

Слои независимы:

- AI не изменяет формальный A;
- B не перезаписывает ответ пользователя и не меняет A;
- risk status не скрывается внутри A;
- hard stop влияет на публикацию, а не на числовой A;
- административная проверка не называется полноценным due diligence без отдельной утверждённой процедуры.

Подробная утверждённая продуктовая основа: `docs/spv-scoring-methodology-v1.md`. История анализа и альтернатив: `docs/scoring-methodology-decisions.md`.

## Основные логические компоненты

### 1. Web application

- регистрация и вход по email/паролю;
- список проектов пользователя;
- создание и редактирование SPV-проекта;
- загрузка документов;
- просмотр извлечённых значений и источников;
- заполнение пропусков и разрешение конфликтов;
- просмотр A, B, рисков и AI-рекомендаций;
- административный интерфейс — отдельный feature slice.

Approved frontend stack:

- React + TypeScript + Vite;
- React Router;
- TanStack Query;
- React Hook Form + Zod for UX validation;
- Tailwind CSS + shadcn/ui;
- Recharts;
- OpenAPI-generated TypeScript client.

Frontend never owns authoritative scoring, permissions, workflow transitions, or data-integrity decisions. Django validates every write again.

### 2. Application backend

- авторизация и проверка доступа к проекту;
- управление жизненным циклом проекта и анкеты;
- выдача временного/контролируемого доступа к файлам;
- оркестрация извлечения и AI-анализа;
- запуск детерминированного score engine;
- управление версиями методики и результатами;
- risk evaluation;
- административные действия и audit trail.

Approved backend stack:

- Python + current supported Django LTS;
- Django REST Framework;
- `drf-spectacular` for OpenAPI;
- Django ORM;
- PostgreSQL;
- Django session authentication with CSRF protection;
- email-first custom User model from the first migration.

Backend is an API-first modular monolith. Business logic lives in application/domain services, not DRF serializers or views.

### Module boundaries

```text
accounts
projects
methodologies
questionnaires
assessments
scoring
evidence
risks
documents
reviews
publication
audit
notifications
```

The normal dependency direction is `API → application service → domain logic → persistence/integration adapters`. Generic repositories and abstraction layers are added only when they solve a demonstrated problem.

### 3. Score engine

Отдельный детерминированный модуль:

- принимает утверждённые ответы и версию методики;
- валидирует обязательные поля;
- вычисляет raw и normalized scores;
- возвращает детализацию по вопросам и блокам;
- не вызывает AI;
- не читает документы напрямую;
- не изменяет исторические результаты;
- должен быть полностью покрываемым unit-тестами на уровне таблицы методики.

Логический контракт:

```text
score(confirmed_answers, methodology_version)
  → A score
  → criterion breakdown
  → completeness/preliminary status
  → calculation metadata
```

Формула A, пять блоков и девять весов утверждены в `docs/spv-scoring-methodology-v1.md`. Score engine рассчитывает вклад критерия как `weight × score / 10` и итоговый A как сумму вкладов.

Score engine также содержит детерминированный Project IRR calculator для nominal after-tax unlevered annual cash flows. Расчёт использует Year 0 и 5–10 прогнозных лет; неоднозначный или невычислимый результат получает `IRR_REQUIRES_REVIEW`.

### 4. Evidence engine

- сопоставляет подтверждённый ответ с найденными документальными значениями;
- хранит источники и статусы `unverified / matched / conflict`;
- в будущем учитывает `admin_verified`;
- вычисляет B по тем же весам, что A, и коэффициентам доказательности `1.0 / 0.5 / 0`;
- не выбирает автоматически, какой конфликтующий источник «правильный».

Формула: `B = Σ criterion weight × verification coefficient`. Конфликт имеет коэффициент 0 и отдельный conflict flag. Внутренний `A × B / 100` допускается только для административной приоритизации.

### 5. Risk engine

- применяет версионированные правила warnings и hard stops;
- сохраняет код риска, причину, источники и статус;
- не изменяет A;
- сообщает publication gate;
- блокирует публикацию при активном Hard Stop;
- не изменяет A или B.

MVP Hard Stops и Risk Flags утверждены в `docs/spv-scoring-methodology-v1.md`. Hard-stop override не входит в первый Admin MVP.

### 6. Document ingestion

Начальные форматы: текстовые PDF и DOCX.

Конвейер:

```text
upload
→ secure object storage
→ text extraction
→ AI structured extraction
→ source references/confidence
→ proposed questionnaire values
→ user review
```

Обработка таблиц, презентаций, изображений и OCR отложена.

Отказ извлечения не блокирует ручное заполнение анкеты.

### 7. AI integration

AI получает только необходимый контекст и используется для недетерминированных вспомогательных задач:

- извлечение структурированных кандидатов;
- поиск пропусков и противоречий;
- предложение категории для чек-листов;
- объяснение результата;
- рекомендации;
- дополнительные наблюдения вне формальной методики.

AI output не является доверенным формальным результатом. Перед использованием извлечённые ответы подтверждаются пользователем или администратором согласно workflow.

AI provider, модель, политика retention и допустимость обработки конфиденциальных данных пока **OPEN**.

### 8. Admin review

Admin MVP включает:

- review queue;
- просмотр источников и расхождений;
- назначение verification status;
- комментарии;
- решение о публикации;
- действия `Return for Correction`, `Approve`, `Publish`;
- запрет `Publish` при активном Hard Stop;
- запуск явного пересчёта;
- audit log.

Статусы проекта: `Draft`, `Review`, `Conflict`, `Ready`, `Published`. Фактическая аудитория статуса `Published` определяется отдельной feature specification; investor matching сюда не входит.

### 9. Telegram notification adapter

Telegram is a secondary channel layered over the same application backend.

Initial responsibilities:

- notify about document-processing completion or failure;
- notify about missing information or return for correction;
- notify about review/status changes;
- provide authenticated/deep links to the primary web interface.

The bot does not own scoring, project state, files, or authorization rules. Long-running work is queued by the backend and completed outside the Telegram update handler.

`aiogram` is the preferred option if the selected backend ecosystem is Python; the final library choice remains part of stack selection. A Telegram Mini App is explicitly deferred until the standard web interface is stable.

## Логическая модель данных

Это перечень доменных сущностей, а не утверждённая схема таблиц.

### User

- идентичность и email-auth;
- роль и разрешения;
- один пользователь может владеть несколькими проектами.

### Project

- владелец;
- тип `SPV` в MVP;
- информационные поля;
- lifecycle/publication status;
- текущая версия анкеты.

### Document

- принадлежность проекту;
- storage reference;
- тип, размер, hash и processing status;
- metadata извлечения;
- правила retention/deletion.

### Questionnaire / Answer

- версия анкеты и методики;
- `answer_value`;
- обязательность;
- подтверждение пользователем;
- связь с найденными документальными значениями.

### Evidence observation

- `document_value`;
- source reference;
- confidence;
- verification status;
- admin comment;
- связь с конкретным ответом.

### Assessment

- methodology version;
- A и breakdown;
- B и evidence breakdown;
- criterion и block breakdown;
- score-at-submission;
- current score/related recalculation при необходимости;
- timestamps и причина пересчёта;
- признак preliminary/final относительно полноты данных.

### Risk finding

- rule version и risk code;
- warning или hard stop;
- субъект, сумма и источник, где применимо;
- status и resolution;
- publication-blocking state и resolution history.

### Investment terms

- требуемая сумма;
- предлагаемая доля;
- implied valuation;
- тип сделки.

Эти условия не входят в A без отдельного утверждения методики.

### Audit event

- actor;
- action;
- target;
- timestamp;
- before/after или ссылка на изменение;
- reason для административно значимых действий.

## Ключевой поток данных

```text
1. Пользователь создаёт проект.
2. Загружает PDF/DOCX либо переходит к ручной анкете.
3. Extractor получает текст, AI предлагает значения и источники.
4. Система сохраняет document_value отдельно от answer_value.
5. Пользователь заполняет пропуски, разрешает видимые конфликты и подтверждает анкету.
6. Score engine рассчитывает A по конкретной methodology_version.
7. Evidence engine рассчитывает статусы и в будущем B.
8. Risk engine создаёт warnings/hard stops и publication gate.
9. AI формирует объяснения и рекомендации, не меняя A/B/risks.
10. Администратор проверяет расхождения, назначает evidence statuses, при необходимости запускает пересчёт и решает вопрос публикации.
```

## Версионирование и воспроизводимость

### DECIDED

- Методика версионируется с первой оценки, начиная с согласованной версии вроде `SPV-1.0`.
- Изменение критериев, весов, формул, нормализации или risk rules создаёт новую версию.
- Исторический `score_at_submission` не изменяется молча.
- Каждый результат содержит входную версию методики и детализацию расчёта.

### OPEN

- хранится ли каждый пересчёт как новый Assessment или как current score со связанной историей;
- когда пользователь может добровольно пересчитать старый проект по новой версии;
- можно ли сравнивать результаты разных версий в UI.

## Авторизация и доступ

### DECIDED

- Проект приватный по умолчанию.
- Заявитель имеет доступ только к своим проектам.
- Администратор получает доступ только в рамках явно определённых полномочий.
- Публикация является отдельным состоянием и не происходит автоматически после оценки.

### OPEN

- модель ролей администратора;
- назначение и отзыв административных полномочий;
- granular access к коммерчески чувствительным файлам;
- доступ инвесторов после появления marketplace;
- удаление и retention после проверки или публикации.

## Хранение файлов

Требуется объектное хранилище с приватным доступом; конкретный сервис **OPEN**.

Минимальные требования:

- файлы не являются публичными по URL;
- доступ проверяется на backend или выдаётся ограниченной signed URL;
- шифрование при передаче и хранении;
- проверка типа/размера и защита от вредоносных файлов;
- журнал административного доступа;
- определённая политика retention и удаления;
- запрет использования документов AI-провайдером для обучения без отдельного явного основания.

## База данных

PostgreSQL is the primary transactional database accessed through Django ORM. The system uses one database; separate databases per module, microservices, event sourcing, and distributed transactions are not required.

Версионированные оценки, ответы, evidence observations, риски и audit events должны быть связаны так, чтобы результат можно было воспроизвести.

## Background processing

Извлечение и AI-анализ документов потенциально длительные и должны выполняться persistent background workers, независимо от HTTP-запроса.

Для ранней версии используется PostgreSQL-backed job/outbox mechanism за небольшим application-level task interface; конкретная библиотека выбирается в соответствующей specification. Web, worker и будущий aiogram bot запускаются отдельными процессами из одного backend codebase/image. Повторные попытки идемпотентны и не создают дубликаты evidence observations или assessments.

## Интеграции

Предполагаемые внешние зависимости:

- email delivery для регистрации/восстановления;
- AI provider;
- object storage;
- hosting/database provider;
- Telegram Bot API for the secondary notification channel;
- в будущем разрешённые источники проверки данных в Казахстане.

Конкретные поставщики не выбраны.

## Deployment

Local development uses Docker Compose. Production topology keeps one product boundary:

```text
/        → built React SPA
/api/    → Django REST API
/admin/  → internal Django Admin
```

A reverse proxy or managed platform provides same-origin routing so browser auth uses secure HttpOnly Django session cookies without JWT in localStorage. Frontend and backend remain separate build artifacts, but backend domain modules are one deployable modular monolith. Managed PostgreSQL is preferred for public pilots. Microservices, Kubernetes, and event-driven architecture are not required.

## Security and privacy

Критичные области:

- коммерчески чувствительные бизнес-планы;
- персональные данные заявителей;
- финансовые прогнозы;
- сведения о долгах и судебных рисках;
- административные решения, изменения значений и пересчёты;
- отправка документов внешнему AI-провайдеру.

До реализации загрузки документов должны быть утверждены:

- допустимые типы данных;
- consent/notice для AI-обработки;
- provider retention/training policy;
- сроки хранения и удаление;
- журналирование доступа;
- процедура реагирования на утечку;
- граница между document matching, admin verification и due diligence.

## Важные архитектурные решения

### DECIDED

- модульный монолит предпочтительнее микросервисов для MVP;
- primary web client is a React/TypeScript/Vite SPA;
- backend is a Django/DRF API-first modular monolith using Django ORM and PostgreSQL;
- frontend contracts are generated from backend OpenAPI;
- Django owns users, sessions, permissions, and authoritative validation;
- same-origin session-cookie + CSRF auth is preferred over browser JWT storage;
- long operations run in persistent background workers, not request or bot handlers;
- score engine детерминирован и отделён от AI;
- A, B и risks — независимые результаты;
- ответы и документальные значения хранятся отдельно;
- методика и risk rules версионируются;
- исторические результаты воспроизводимы;
- файлы приватны;
- AI является помощником, а не судьёй;
- публикация контролируется отдельно от расчёта.

### Не принимать пока

- конкретный cloud, email, AI, and object-storage provider;
- отдельные микросервисы;
- сложную message queue;
- realtime;
- blockchain/audit ledger;
- автоматическое принятие инвестиционного решения;
- автоматическую публикацию по числовому баллу;
- единую публичную формулу `A × B`;
- категории результата до пилотной калибровки.

## Дорогие открытые решения

- хранение и удаление документов;
- условия внешней AI-обработки;
- юридическое значение публикации проекта;
- фактическая аудитория и контроль доступа для статуса `Published`;
- будущая модель доступа инвесторов.
- Telegram account linking and notification-consent behavior.

## Delivery references

- Dependency-ordered backlog: `docs/initial-feature-backlog.md`.
- Recommended first end-to-end slice: `docs/first-milestone.md`.
