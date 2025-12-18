# Мастер рядом

PWA для поиска проверенных бытовых мастеров в радиусе 1–3 км.

## Что уже есть
- PWA (manifest + service worker)
- Геолокация пользователя
- Выбор услуги и радиуса
- Мок-данные мастеров (до 5 в выдаче)
- Офлайн-режим
- Установка как приложение

## Запуск локально
```bash
python3 -m http.server 5174


> ⚠️ Если терминал ругнётся на вложенные ``` — скажи, дам версию без них.

---

### Шаг 2. Зафиксируем README
```bash
git add README.md
git commit -m "Add README with project overview"
git push

cd ~/master-nearby-pwa

cat > README.md <<'MD'
# Мастер рядом (PWA)

PWA для поиска проверенных бытовых мастеров в радиусе 1–3 км.

## Запуск локально
```bash
python3 -m http.server 5174

cat > CODEX_PROMPT.md <<'MD'
TASK:
Update existing files: index.html, styles.css, app.js, manifest.webmanifest, sw.js.
Goal: minimal installable PWA “Мастер рядом”: geolocation, service + radius (1–3km), show up to 5 masters with rating/distance and tel: contact.
Rules: no frameworks, do not run commands, keep changes small and readable.
Out of scope: auth, payments, ads, maps, reviews UI.
