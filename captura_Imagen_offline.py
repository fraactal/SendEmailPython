import os
import time
import shutil
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
load_dotenv()  # carga .env del directorio actual (o donde ejecutes)

def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")


def get_env(name: str, default: str = "") -> str:
    val = os.getenv(name)
    return val if val is not None else default


# -------------------- Config desde ENV --------------------
GRAFANA_SERVER = get_env("GRAFANA_SERVER", "10.10.26.250:3000")
GRAFANA_URL_LOGIN = f"http://{GRAFANA_SERVER}/login"
GRAFANA_DASHBOARD_URL = get_env("GRAFANA_DASHBOARD_URL", "")

GRAFANA_USERNAME = get_env("GRAFANA_USERNAME", "")
GRAFANA_PASSWORD = get_env("GRAFANA_PASSWORD", "")

OUTPUT_DIR = get_env("OUTPUT_DIR", "/data")
FILE_PREFIX = get_env("FILE_PREFIX", "dashboard_CMDB")

SEND_EMAIL = env_bool("SEND_EMAIL", False)
SMTP_SERVER = get_env("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(get_env("SMTP_PORT", "587"))
SMTP_USER = get_env("SMTP_USER", "")
SMTP_PASSWORD = get_env("SMTP_PASSWORD", "")
EMAIL_TO = get_env("EMAIL_TO", "")
EMAIL_FROM = get_env("EMAIL_FROM", SMTP_USER)
EMAIL_SUBJECT = get_env("EMAIL_SUBJECT", "Grafana Dashboard Capture")

# Chrome paths en Debian slim (en Dockerfile)
CHROME_BIN = get_env("CHROME_BIN", "/usr/bin/chromium")
CHROMEDRIVER_PATH = get_env("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")


def now_stamp():
    # Fecha/hora del servidor (setear TZ en docker)
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def date_label():
    # Texto humano para imprimir en la imagen
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def stitch_images(image_paths):
    images = [Image.open(p).convert("RGB") for p in image_paths]
    widths, heights = zip(*(img.size for img in images))
    total_height = sum(heights)
    max_width = max(widths)

    stitched = Image.new("RGB", (max_width, total_height), (255, 255, 255))
    y = 0
    for img in images:
        stitched.paste(img, (0, y))
        y += img.height
    return stitched


def overlay_date(img: Image.Image, text: str) -> Image.Image:
    # Caja semitransparente + texto
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except Exception:
        font = ImageFont.load_default()

    padding = 14
    text_w, text_h = draw.textbbox((0, 0), text, font=font)[2:]
    box_w = text_w + padding * 2
    box_h = text_h + padding * 2

    x = 20
    y = 20

    # Dibujar rectángulo (simulamos “overlay” con un rectángulo oscuro)
    draw.rectangle([x, y, x + box_w, y + box_h], fill=(0, 0, 0))
    draw.text((x + padding, y + padding), text, font=font, fill=(255, 255, 255))
    return img


def build_driver():
    chrome_options = Options()
    chrome_options.binary_location = CHROME_BIN
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1380")

    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=chrome_options)


def capture_dashboard():
    if not GRAFANA_DASHBOARD_URL:
        raise ValueError("Falta GRAFANA_DASHBOARD_URL en el .env")
    if not GRAFANA_USERNAME or not GRAFANA_PASSWORD:
        raise ValueError("Falta GRAFANA_USERNAME / GRAFANA_PASSWORD en el .env")

    ensure_output_dir()

    tmp_dir = os.path.join(OUTPUT_DIR, "tmp_captures")
    os.makedirs(tmp_dir, exist_ok=True)

    driver = build_driver()
    try:
        print("🔐 Iniciando sesión en Grafana...")
        driver.get(GRAFANA_URL_LOGIN)
        time.sleep(2)

        driver.find_element(By.NAME, "user").send_keys(GRAFANA_USERNAME)
        driver.find_element(By.NAME, "password").send_keys(GRAFANA_PASSWORD + "\n")
        time.sleep(3)

        print("📊 Cargando dashboard...")
        driver.get(GRAFANA_DASHBOARD_URL)
        time.sleep(7)

        print("⬇️ Capturando por secciones del contenedor scrollable...")

        # OJO: este XPATH puede variar según versión/tema de Grafana
        container = driver.find_element(By.XPATH, '//*[@id="reactRoot"]/div[1]/main/div[3]/div/div/div[1]')

        scroll_height = driver.execute_script("return arguments[0].scrollHeight", container)
        viewport_height = 1080
        steps = scroll_height // viewport_height + 1

        image_paths = []
        for i in range(steps):
            y = i * viewport_height
            driver.set_window_size(1920, viewport_height + 200)
            driver.execute_script("arguments[0].scrollTo(0, arguments[1]);", container, y)
            time.sleep(1.5)

            filename = os.path.join(tmp_dir, f"screenshot_{i}.png")
            driver.save_screenshot(filename)
            image_paths.append(filename)
            print(f"📸 Captura {i+1}/{steps} guardada.")

        print("🧵 Uniendo capturas...")
        stitched = stitch_images(image_paths)

        print("🗓️ Imprimiendo fecha en la imagen...")
        stitched = overlay_date(stitched, f"Generado: {date_label()}")

        stamp = now_stamp()
        final_path = os.path.join(OUTPUT_DIR, f"{FILE_PREFIX}_{stamp}.png")
        stitched.save(final_path, "PNG")

        print(f"✅ Imagen final guardada: {final_path}")
        return final_path

    finally:
        driver.quit()
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


def send_email(attachment_path: str):
    if not (SMTP_USER and SMTP_PASSWORD and EMAIL_TO):
        raise ValueError("Faltan variables SMTP_USER/SMTP_PASSWORD/EMAIL_TO para enviar correo")#

    msg = EmailMessage()
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content("Buenos días,\n\nAdjunto captura del dashboard.\n\nSaludos.\n")#

    with open(attachment_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename=os.path.basename(attachment_path))#

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    print("📤 Correo enviado exitosamente.")


if __name__ == "__main__":
    final_img = capture_dashboard()
    if SEND_EMAIL:
        send_email(final_img)
