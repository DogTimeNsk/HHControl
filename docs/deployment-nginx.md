# Развёртывание за Nginx

Эта инструкция предполагает, что Docker Compose и системный Nginx работают на
одном сервере. Внешний Nginx выдаёт TLS-сертификат, пропускает только
разрешённые IP-адреса и передаёт трафик на frontend-контейнер по loopback.

## 1. DNS и приложение

1. Создайте DNS-запись `A` для вашего домена, указывающую на публичный IP сервера.
2. В `dev.hh.ru` и в `.env` используйте строго один callback URL:

   ```dotenv
   HH_OAUTH_REDIRECT_URI=https://hh-control.example.org/hh/redirect
   ```

3. Для production добавьте в `.env`:

   ```dotenv
   COOKIE_SECURE=true
   APP_SESSION_SECRET=<длинное-случайное-значение>
   TOKEN_ENCRYPTION_KEY=<ключ-Fernet>
   ```

   Значения можно создать так:

   ```bash
   openssl rand -hex 32
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. Запустите сервис из корня проекта:

   ```bash
   docker compose up -d --build
   make admin_add
   ```

   Compose публикует frontend только на `${FRONTEND_BIND_ADDRESS}:${FRONTEND_PORT}`;
   API и SQLite наружу не публикуются. Для этой инструкции используйте
   `FRONTEND_BIND_ADDRESS=127.0.0.1`, выберите свободный `FRONTEND_PORT` и
   укажите этот же порт в `proxy_pass` ниже.

## 2. Nginx и ACL по IP

Создайте `/etc/nginx/sites-available/hh-control`. Замените домен и IP-адреса в
`allow` на ваши публичные статические адреса (один адрес на строку).

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name hh-control.example.org;

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name hh-control.example.org;

    ssl_certificate     /etc/letsencrypt/live/hh-control.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hh-control.example.org/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # ACL: добавьте все разрешённые адреса до deny all.
    allow 203.0.113.10;
    allow 198.51.100.0/24;
    deny all;

    location / {
        proxy_pass http://127.0.0.1:8080;  # Замените 8080 на FRONTEND_PORT.
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # noVNC uses WebSocket at /browser/websockify. This must be a separate
    # location because the outer Nginx also has to preserve the Upgrade.
    location /browser/ {
        proxy_pass http://127.0.0.1:8080;  # Замените 8080 на FRONTEND_PORT.
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
}
```

`deny all` действует и на `/api`, и на `/hh/redirect`, поэтому OAuth callback
доступен только с IP, с которого пользователь проходит авторизацию. Если
hh.ru не перенаправляет браузер через свой сервер (обычный OAuth redirect), это
именно желаемое поведение. Если callback будет приходить сервер-сервером,
создайте отдельное, более узкое правило для его подтверждённых адресов.

Browser login is served by the frontend at `/browser/`. The frontend additionally
validates the `hh_control_session` cookie through its API before serving noVNC
assets or the WebSocket, so an anonymous or expired browser session receives
`401 Unauthorized` even from an allowed IP. Do not create a public proxy
directly to the browser service, its VNC port, or its control port.

Включите конфигурацию и проверьте её:

```bash
sudo ln -s /etc/nginx/sites-available/hh-control /etc/nginx/sites-enabled/hh-control
sudo nginx -t
sudo systemctl reload nginx
```

## 3. Сертификат Let's Encrypt

До первого выпуска сертификата временно оставьте только HTTP server-блок выше,
выпустите сертификат и затем добавьте HTTPS server-блок:

```bash
sudo certbot --nginx -d hh-control.example.org
sudo nginx -t
sudo systemctl reload nginx
```

Проверьте с разрешённого IP `https://hh-control.example.org/api/health`; с другого
IP Nginx должен вернуть `403 Forbidden`.

## Обновление

```bash
git pull
docker compose up -d --build
docker compose ps
```

Не открывайте `FRONTEND_PORT` в firewall и не публикуйте Docker volume с SQLite.
