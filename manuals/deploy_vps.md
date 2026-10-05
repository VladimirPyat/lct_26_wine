# Деплой на VPS (2 vCPU / 4 GB, без GPU)

Разворачивание на чистом сервере одной командой: скрипт сам скачивает модели, готовую базу и картинки каталога, проверяет sha256, поднимает Postgres из архива тома и собирает CPU-образ приложения.

Что работает на сервере иначе, чем на dev-машине (профиль `APP_ENV=vps`, оверлеи в `config/profiles/vps/`):

- энкодер — int8 `bin/siglip2_wine_p1_epoch_3_int8.onnx`, батч 1, один инференс одновременно;
- всё на CPU (2 потока ORT), OCR этикетки — через LLM API (`QWEN_API_KEY`), PHOCR на сервере не используется;
- база — готовый том Postgres из `pgdata.tar.zst` (каталог уже проиндексирован на GPU, на сервере ничего не кодируется).

## 1. Требования к серверу

- Ubuntu 22.04+ / Debian 12, **x86_64** (архив базы — сырой data-dir Postgres, ARM не подойдёт);
- 2 vCPU, 4 GB RAM, ~10 GB свободного диска (образ ≈2 GB, модели ≈0,5 GB, картинки ≈130 MB, сборка образа временно занимает больше);
- открытые порты 22 (SSH) и 80 (HTTP).

## 2. Подготовка сервера (один раз)

Docker Engine + compose plugin — по официальной инструкции: <https://docs.docker.com/engine/install/ubuntu/> (для Debian — <https://docs.docker.com/engine/install/debian/>).

После установки — чтобы запускать docker без `sudo` (перелогиниться после команды):

```bash
sudo usermod -aG docker $USER
```

Утилиты для скриптов:

```bash
sudo apt-get update && sudo apt-get install -y git curl zstd
```

Swap 2 GB — страховка от OOM при сборке образа и пиках памяти (если `swapon --show` пусто):

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Файрвол (если используется `ufw`):

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw enable
```

## 3. Код

Репозиторий публичный — клонируем по HTTPS, SSH-ключ GitHub на сервере не нужен:

```bash
cd ~
git clone https://github.com/VladimirPyat/lct_26_wine.git
cd ~/lct_26_wine
```

Если репозиторий станет приватным — создайте на сервере **отдельный** deploy key, личный ключ не копируйте:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/vine_deploy -N ""
cat ~/.ssh/vine_deploy.pub   # → GitHub: Settings → Deploy keys → Add (read-only)
GIT_SSH_COMMAND="ssh -i ~/.ssh/vine_deploy" git clone git@github.com:VladimirPyat/lct_26_wine.git ~/lct_26_wine
```

## 4. Секреты (`.env`)

Вариант А — шаблон на сервере:

```bash
cp .env.vps.example .env
nano .env          # QWEN_API_KEY=<ключ>
```

Вариант Б — скопировать свой `.env` с dev-машины (выполнять на dev-машине):

```bash
scp .env user@<ip>:lct_26_wine/.env      # при нужном ключе: scp -i ~/.ssh/<ключ> ...
```

`APP_ENV=vps` и `DATABASE_URL` для контейнера задаёт `docker-compose.vps.yml`, поэтому dev-значения из скопированного `.env` им не мешают. Обязателен только `QWEN_API_KEY`. Опционально: `VINE_PORT` (по умолчанию 80), `VINE_LOG_LEVEL`, `VINE_PG_VOLUME`.

## 5. Запуск

```bash
cd ~/lct_26_wine
scripts/deploy/deploy_vps.sh
```

Скрипт выполняет 4 шага (можно идти пить чай — первый запуск 10–20 минут, в основном сборка образа):

1. `scripts/deploy/fetch_assets.sh` — скачивает с Google Drive всё из `scripts/deploy/assets.lock`, проверяет sha256: модели → `bin/`, `images.tar.zst` → распаковка в `static/wines/`, `pgdata.tar.zst` → `data/tmp/deploy/`;
2. `scripts/deploy/restore_db_volume.sh` — создаёт том `vine_vps_pgdata` из архива, поднимает `db`, печатает число вин и число slug без картинки (ожидается `wines in DB: 2091`, без картинки — `0`);
3. `docker compose -f docker-compose.vps.yml up -d --build` — сборка CPU-образа и старт;
4. ожидание `/health`.

Проверка снаружи:

```bash
curl http://<ip>/health     # {"status":"ok","profile":"vps"}
```

Интерфейс — `http://<ip>/`, eval-эндпоинт — `http://<ip>/v1/eval/predict`.

Скачивание моделей без запуска — `scripts/deploy/fetch_assets.sh`; проверка, всё ли на месте, — `scripts/deploy/fetch_assets.sh --check`. Если Drive оборвал загрузку — просто запустите скрипт ещё раз: уже скачанные файлы с верным sha256 пропускаются.

Замер скорости энкодера на CPU сервера (опционально):

```bash
docker compose -f docker-compose.vps.yml exec app uv run python scripts/bench_encoder_cpu.py \
  bin/siglip2_wine_p1_epoch_3_int8.onnx --threads 2
```

## 6. Повседневные команды

```bash
cd ~/lct_26_wine
docker compose -f docker-compose.vps.yml ps
docker compose -f docker-compose.vps.yml logs -f --tail 100 app
docker compose -f docker-compose.vps.yml restart app
docker compose -f docker-compose.vps.yml down        # остановить (том базы сохраняется)
```

Контейнеры перезапускаются сами после ребута (`restart: unless-stopped`).

Очистка фото пользовательских запросов старше срока хранения (`storage.retention_days`) — ежедневно через cron (`crontab -e`):

```cron
30 4 * * * cd ~/lct_26_wine && docker compose -f docker-compose.vps.yml exec -T app uv run python scripts/cleanup_search_queries.py >> data/tmp/cleanup.log 2>&1
```

## 7. Обновление

### Кнопкой из GitHub (основной способ)

GitHub → **Actions** → **Deploy VPS** → **Run workflow**:

- `ref` — ветка, тег или полный SHA коммита (по умолчанию `master`). Откат кода = запуск с SHA предыдущего коммита;
- `replace_db` — галочка = `--yes` (заменить том базы из архива в `assets.lock`, старый — в бэкап).

Workflow (`.github/workflows/deploy-vps.yml`) заходит на сервер по SSH, переключает репозиторий на `ref` (`git fetch` + `checkout --detach`) и запускает `scripts/deploy/deploy_vps.sh`: образ пересобирается на сервере (слой зависимостей кэшируется — обычно пара минут), затем проверка `/health`. Если на сервере изменены файлы из git, деплой останавливается, ничего не перезаписывая (`.env`, `bin/`, `data/` не в git — их это не касается). История: `data/tmp/deploy/state/deploy_history.log`.

Одноразовая настройка:

1. На своей машине создать **отдельную** пару ключей для GitHub (без пароля):

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/vine_actions -N "" -C github-actions-deploy
   ```

2. Публичный ключ — на сервер (пользователь, под которым запускали деплой, должен быть в группе `docker`):

   ```bash
   ssh-copy-id -i ~/.ssh/vine_actions.pub user@<ip>
   ```

3. GitHub → репозиторий → **Settings → Secrets and variables → Actions**:

   | Тип | Имя | Значение |
   |---|---|---|
   | Secret | `VPS_HOST` | IP сервера |
   | Secret | `VPS_USER` | пользователь на сервере |
   | Secret | `VPS_SSH_KEY` | содержимое `~/.ssh/vine_actions` (приватный ключ целиком, с строками `BEGIN`/`END`) |
   | Secret | `VPS_KNOWN_HOSTS` | вывод `ssh-keyscan <ip>` (защита от подмены сервера) |
   | Variable | `VPS_APP_DIR` | путь к репозиторию на сервере, если не `~/lct_26_wine` |
   | Variable | `VPS_PORT` | порт SSH, если не 22 |

4. Проверка: запустить workflow с `ref=master` — в логе шага **Deploy** будет `deploying <коммит>` и `healthy: {...}`.

### Вручную на сервере

```bash
cd ~/lct_26_wine
git fetch origin master && git checkout --detach FETCH_HEAD
scripts/deploy/deploy_vps.sh
```

(После первого деплоя кнопкой репозиторий на сервере в состоянии detached HEAD, поэтому `git pull` не используется.) База не трогается, если архив в `assets.lock` не менялся.

### Новый каталог

Новый `pgdata.tar.zst` + картинки: обновить `assets.lock` в репозитории (раздел 8) → деплой кнопкой с галочкой `replace_db` (или вручную `scripts/deploy/deploy_vps.sh --yes`).

`--yes` разрешает заменить существующий том: старый сначала копируется в `vine_vps_pgdata_bak_<дата>`. Откат базы — указать бэкап в `.env` и перезапустить:

```bash
echo 'VINE_PG_VOLUME=vine_vps_pgdata_bak_<дата>' >> .env
docker compose -f docker-compose.vps.yml up -d
```

Старые бэкап-тома: `docker volume ls | grep vine_vps_pgdata_bak` (удалять вручную, когда больше не нужны).

## 8. Как собрать новый архив базы (на dev-машине)

1. Каталог проиндексирован fp32/fp16-энкодером на GPU (int8-каталог хуже — сервер кодирует int8 только запросы).
2. Остановить `db` (копировать только остановленный том), упаковать том и посчитать sha256:

   ```bash
   docker compose stop db
   docker run --rm -v vine_pgdata:/data:ro pgvector/pgvector:pg16@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b \
     tar --numeric-owner -C /data -cf - . | zstd -19 -T0 > pgdata.tar.zst
   docker compose start db
   sha256sum pgdata.tar.zst
   ```

   Образ Postgres должен совпадать с digest в `docker-compose.vps.yml` (та же версия PG и pgvector).
3. Картинки: `tar -C static/wines -cf - --exclude='.*' . | zstd -19 -T0 > images.tar.zst`.
4. Залить на Google Drive (доступ «все, у кого есть ссылка»), вписать ID файла (из ссылки `.../file/d/<ID>/view`) и sha256 в `scripts/deploy/assets.lock`, закоммитить.
5. На сервере — раздел 7 «Новый каталог».

## 9. Типовые проблемы

| Симптом | Что делать |
|---|---|
| `sha256 mismatch` в `fetch_assets.sh` | Drive отдал HTML вместо файла (нет общего доступа или лимит скачиваний) — проверить доступ по ссылке, повторить позже |
| `Unable to find image 'pgvector/pgvector:pg16@sha256:...'` и ошибка сети / DNS (`i/o timeout`, `failed to resolve reference`) на шаге `2/4 database volume` | архив базы скачан нормально — не докачался образ Postgres из Docker Hub (на нём распаковывается архив и работает база). Скачать вручную: `docker pull pgvector/pgvector:pg16@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`, затем `scripts/deploy/deploy_vps.sh --yes` (том успел создаться пустым; модели и картинки повторно не скачиваются). Если DNS сбоит регулярно — `DNS=1.1.1.1 8.8.8.8` в `/etc/systemd/resolved.conf.d/dns.conf`, `sudo systemctl restart systemd-resolved docker` |
| `volume ... exists with other data` | том уже есть с другой базой (или пустой после оборванной распаковки) — `deploy_vps.sh --yes` (с бэкапом) |
| `app did not become healthy` | скрипт печатает логи; частые причины — нет `QWEN_API_KEY`, нет моделей в `bin/` (`fetch_assets.sh --check`) |
| порт 80 занят | `VINE_PORT=8080` в `.env`, повторить `deploy_vps.sh` |
| OOM / контейнер перезапускается | проверить swap (`swapon --show`), `docker stats`; лимиты — `mem_limit` в `docker-compose.vps.yml` |
| `permission denied ... docker.sock` | не перелогинились после `usermod -aG docker` |

Связанные документы: профили и настройки — [configuration_guide.md](configuration_guide.md); локальный запуск на GPU — [quickstart.md](quickstart.md); план и решения — `agent_docs/plans/deploy_vps.md`.
