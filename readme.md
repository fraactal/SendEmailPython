# SETUP OFFLINE -- Grafana Capture (Docker + Compose)

Este proyecto genera una **captura (screenshot) de un dashboard de
Grafana**, une las secciones en una sola imagen, le imprime la
**fecha/hora**, y guarda el archivo final en una **carpeta compartida
del servidor** (montada como volumen Docker).\
Opcionalmente puede enviar la imagen por correo vía SMTP.

> ✅ Diseñado para funcionar **offline** (sin necesidad de internet) en
> el servidor de producción.\
> 🔐 Las credenciales se cargan desde un archivo **`.env`** (no se sube
> al repositorio).

------------------------------------------------------------------------

## 1) Estructura del proyecto

    grafana-capture-offline/
    ├─ captura_Imagen_offline.py
    ├─ requirements.txt
    ├─ dockerfile_offline
    ├─ docker-compose.yml
    ├─ .env
    └─ .gitignore

------------------------------------------------------------------------

## 2) Variables de entorno (.env)

Crea un archivo `.env` en la misma carpeta del `docker-compose.yml`:

``` env
# Grafana
GRAFANA_SERVER=10.10.26.250:3000
GRAFANA_DASHBOARD_URL=http://10.10.26.250:3000/d/pbU_ZwTSz/consolidado-mdlw-add-cmdb?orgId=1
GRAFANA_USERNAME=admin
GRAFANA_PASSWORD=CAMBIAME

# Salida
OUTPUT_DIR=/data
FILE_PREFIX=dashboard_CMDB
TZ=America/Santiago

# Email (opcional)
SEND_EMAIL=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD="tu app password con espacios"
EMAIL_TO=correo1@dominio.com,correo2@dominio.com
EMAIL_FROM=tu_correo@gmail.com
EMAIL_SUBJECT=📈 Servidores Middleware
```

Permisos recomendados:

    chmod 600 .env

------------------------------------------------------------------------

## 3) Construcción de la imagen

``` bash
docker build -t captura-cmdb-offline:1.0 -f dockerfile_offline .
```

------------------------------------------------------------------------

## 4) Preparar carpeta compartida en el servidor

``` bash
sudo mkdir -p /srv/compartido/capturas
sudo chmod -R 775 /srv/compartido/capturas
```

------------------------------------------------------------------------

## 5) docker-compose.yml

``` yaml
services:
  captura:
    image: captura-cmdb-offline:1.0
    env_file:
      - .env
    environment:
      OUTPUT_DIR: /data
      TZ: America/Santiago
    volumes:
      - /capturas_cmdb:/data
    restart: "no"
```

------------------------------------------------------------------------

## 6) Ejecutar el contenedor

``` bash
docker compose up --abort-on-container-exit
```

Verifica la captura:

``` bash
ls -lah /capturas_cmdb
```

Resultado esperado:

    dashboard_CMDB_YYYY-MM-DD_HH-MM-SS.png

------------------------------------------------------------------------

## 7) Exportar imagen Docker para servidor offline

En máquina con internet:

``` bash
docker save captura-cmdb-offline:1.0 -o captura-cmdb-offline_1.0.tar
```

Copiar el archivo `.tar` al servidor offline.

En servidor offline:

``` bash
docker load -i captura-cmdb-offline_1.0.tar
docker compose up --abort-on-container-exit
```

------------------------------------------------------------------------

## 8) Ejecución manual (sin compose)

``` bash
docker run --rm \
  --env-file .env \
  -v /capturas_cmdb:/data \
  captura-cmdb-offline:1.0
```

------------------------------------------------------------------------

## 9) Seguridad

-   Nunca subas `.env` al repositorio.
-   Rota credenciales si fueron expuestas.
-   Usa permisos `chmod 600 .env`.

------------------------------------------------------------------------

## 10) Resultado final

Las imágenes generadas quedarán en:

    /srv/compartido/capturas/

Con sello de fecha y hora dentro de la imagen.
