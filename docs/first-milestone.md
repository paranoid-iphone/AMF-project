# Recommended first milestone — manual SPV assessment

## Статус

**RECOMMENDED.** Самый маленький end-to-end milestone, который даёт заявителю самостоятельную ценность и проверяет основу продукта без файлов, AI и административной проверки.

## Цель

Пользователь может зарегистрироваться, создать приватный SPV-проект, вручную заполнить анкету, сохранить черновик и получить воспроизводимую предварительную оценку с понятной детализацией.

## Happy path

```text
application starts
→ applicant registers with email/password
→ signs in
→ creates an SPV project
→ fills the questionnaire over one or more sessions
→ reviews and confirms all required answers
→ system calculates a versioned deterministic assessment
→ applicant sees A, blocks, criteria, risks, weak areas, and disclaimer
→ applicant edits answers and reassesses
→ data and assessment remain after reload
```

## Scope

### Application foundation

- выбранный простой stack и единый deployable application boundary;
- транзакционная база данных;
- базовые test/lint/typecheck/build quality gates;
- локальный способ запуска, зафиксированный для команды.

### Authentication and ownership

- регистрация по email и паролю;
- вход и выход;
- защищённая область приложения;
- пользователь видит только свои проекты;
- один пользователь может создать несколько проектов.

### SPV draft

- создание проекта;
- список проектов;
- сохранение незаполненного черновика;
- продолжение заполнения после нового входа;
- ручная structured questionnaire;
- validation обязательных полей;
- просмотр и явное подтверждение полной анкеты.

### Formal assessment

- versioned methodology/configuration;
- deterministic criterion scores;
- block contributions;
- A от 0 до 100;
- preliminary status при обязательных пропусках;
- questionnaire-derived Risk Flags и Hard Stops;
- одинаковые подтверждённые ответы всегда дают одинаковый результат;
- score-at-submission сохраняется и не пересчитывается молча.

### Evidence presentation

Документы в milestone отсутствуют, поэтому B не должен создавать впечатление проверки. Допустимое представление:

```text
B = 0/100
Документальные подтверждения не оценивались.
```

Либо UI может показывать только текстовый статус до появления document feature; точный вариант фиксируется в implementation specification.

### Applicant result

- A и methodology version;
- criterion и block breakdown;
- слабые места, полученные из формальных результатов без AI;
- Risk Flags и Hard Stops;
- пояснение preliminary/final относительно полноты анкеты;
- явный дисклеймер: данные предоставлены заявителем и не прошли независимую проверку;
- редактирование и повторная оценка;
- предыдущая оценка сохраняется внутри системы, даже если UI показывает только последнюю.

## Return criterion for milestone 1

### Рекомендуемый минимальный вариант

Чтобы не задерживать первый пользовательский тест финансовым модулем, milestone использует:

```text
methodology_version = SPV-DRAFT-0.1
заявленная годовая доходность проекта
```

Поле нельзя называть IRR. Результат должен быть явно экспериментальным.

### Следующий slice

После проверки ручного потока добавляется structured cash-flow form и deterministic Project IRR. Это создаёт `SPV-1.0` assessment либо явный пересчёт по новой версии. Исторический draft-result сохраняется.

## Explicit non-goals

- PDF/DOCX upload;
- document extraction;
- AI prefilling;
- AI recommendations;
- evidence matching и полноценный B workflow;
- Admin UI;
- verification, approval и publication;
- investor role и marketplace;
- calculated Project IRR в рекомендуемом минимальном варианте;
- OCR, изображения, таблицы и презентации;
- публичные категории и проходные пороги;
- configurable criteria и investor-specific weights;
- видимое сравнение истории оценок;
- due diligence;
- messaging, offers, payments и transactions;
- казахская и английская локализация.

## High-level completion checks

Milestone считается работающим, если фактически проверено:

1. Приложение запускается задокументированной командой.
2. Новый пользователь может зарегистрироваться, войти и выйти.
3. Пользователь может создать минимум два независимых проекта.
4. Черновик сохраняется и восстанавливается после выхода и повторного входа.
5. Другой пользователь не может прочитать или изменить чужой проект.
6. Обязательные пропуски не исчезают из расчёта и делают Assessment preliminary.
7. После подтверждения полной анкеты создаётся versioned Assessment.
8. Одинаковые входные данные дают одинаковый A и breakdown.
9. Результат показывает отсутствие документальной проверки и не заявляет due diligence.
10. Risk Flags и Hard Stops отображаются отдельно от A.
11. Изменение ответа и reassessment не изменяет исторический score-at-submission.
12. Данные сохраняются после перезапуска приложения/базы в пределах выбранной dev environment.
13. Проходят согласованные tests, lint, typecheck и build.
14. Основной flow проверен в браузере.

## Почему milestone не включает AI и документы

- Формальная ценность продукта должна работать без внешнего AI provider.
- Ручной flow является fallback для ошибок extraction.
- Документы требуют отдельной security, retention и consent модели.
- AI extraction зависит от стабильных question IDs и answer contracts.
- Исключение этих функций уменьшает стоимость первой проверки и не создаёт throwaway architecture.

## Решение, которое потребуется перед implementation specification

Подтвердить использование `SPV-DRAFT-0.1` с заявленной доходностью в первом milestone либо расширить milestone полноценным Project IRR calculator. Рекомендуемый default — draft fallback, а IRR — следующий вертикальный slice.
