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

# -------------------- ENV --------------------
load_dotenv()


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

# Chrome paths en Debian slim (Dockerfile)
CHROME_BIN = get_env("CHROME_BIN", "/usr/bin/chromium")
CHROMEDRIVER_PATH = get_env("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")


# -------------------- Helpers --------------------
def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def date_label() -> str:
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def overlay_date(img: Image.Image, text: str) -> Image.Image:
    """
    Esto es SOLO para imprimir la fecha dentro de la imagen.
    Si no lo quieres, puedes borrar esta función y su llamada.
    """
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except Exception:
        font = ImageFont.load_default()

    padding = 14
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x, y = 20, 20
    box_w = text_w + padding * 2
    box_h = text_h + padding * 2

    draw.rectangle([x, y, x + box_w, y + box_h], fill=(0, 0, 0))
    draw.text((x + padding, y + padding), text, font=font, fill=(255, 255, 255))
    return img


def build_driver():
    """
    En OFFLINE NO usamos ChromeDriverManager (requiere internet).
    Usamos Chromium + Chromedriver instalados en el contenedor (paths fijos).
    """
    chrome_options = Options()
    chrome_options.binary_location = CHROME_BIN
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1380")

    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=chrome_options)


# ---------------- STITCH ----------------
def stitch_images_dynamic(shots, viewport_height):
    """
    Une capturas eliminando duplicación según el overlap REAL.
    shots: [(filepath, real_scrollTop), ...]
    """
    opened = [(Image.open(p).convert("RGB"), y) for p, y in shots]

    processed = []
    prev_y = None
    prev_img_h = None  # alto REAL del screenshot anterior (sin recorte)

    for idx, (img, y) in enumerate(opened):
        if idx == 0:
            processed.append(img)
            prev_y = y
            prev_img_h = img.size[1]
            continue

        overlap_px = (prev_y + (prev_img_h or viewport_height)) - y
        overlap_px = max(0, min(overlap_px, img.size[1] - 1))

        if overlap_px > 0:
            w, h = img.size
            img = img.crop((0, overlap_px, w, h))

        processed.append(img)

        prev_y = y
        prev_img_h = opened[idx][0].size[1]

    widths, heights = zip(*(im.size for im in processed))
    total_height = sum(heights)
    max_width = max(widths)

    stitched = Image.new("RGB", (max_width, total_height), (255, 255, 255))
    y_offset = 0
    for im in processed:
        stitched.paste(im, (0, y_offset))
        y_offset += im.size[1]

    return stitched


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

        # Desactivar animaciones (reduce cortes/reflow)
        driver.execute_script("""
        const style = document.createElement('style');
        style.innerHTML = '* { transition: none !important; animation: none !important; }';
        document.head.appendChild(style);
        """)

        print("⬇️ Capturando scroll completo (contenedor)...")

        container = driver.find_element(By.XPATH, '//*[@id="reactRoot"]/div[1]/main/div[3]/div/div/div[1]')

        driver.execute_script("arguments[0].scrollTo(0, 0);", container)
        time.sleep(1)

        viewport_height = driver.execute_script("return arguments[0].clientHeight", container)

        overlap = 140
        step = max(viewport_height - overlap, 200)

        shots = []  # [(filepath, real_scrollTop), ...]

        i = 0
        last_real_y = -1
        stuck_count = 0

        while True:
            scroll_height = driver.execute_script("return arguments[0].scrollHeight", container)
            max_y = max(scroll_height - viewport_height, 0)

            requested_y = min(i * step, max_y)

            driver.execute_script("arguments[0].scrollTo(0, arguments[1]);", container, requested_y)
            time.sleep(1.3)

            # ✅ IMPORTANTE: scroll REAL aplicado
            real_y = driver.execute_script("return arguments[0].scrollTop;", container)

            filename = os.path.join(tmp_dir, f"screenshot_{i}.png")
            container.screenshot(filename)
            shots.append((filename, real_y))

            print(f"📸 Captura {i+1} (real_y={real_y} / max_y={max_y})")

            # Evitar duplicado final
            if real_y == last_real_y:
                stuck_count += 1
            else:
                stuck_count = 0
            last_real_y = real_y

            if stuck_count >= 2:
                break

            if (max_y - real_y) < 5:
                break

            i += 1

        print("🧵 Uniendo capturas...")
        stitched = stitch_images_dynamic(shots, viewport_height)

        # ✅ Imprimir fecha dentro de la imagen (opcional)
        #stitched = overlay_date(stitched, f"Generado: {date_label()}")

        final_path = os.path.join(OUTPUT_DIR, f"{FILE_PREFIX}_{now_stamp()}.png")
        stitched.save(final_path, "PNG")
        print(f"✅ Imagen final guardada: {final_path}")
        return final_path

    finally:
        driver.quit()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def send_email(attachment_path: str):
    if not (SMTP_USER and SMTP_PASSWORD and EMAIL_TO):
        raise ValueError("Faltan variables SMTP_USER/SMTP_PASSWORD/EMAIL_TO para enviar correo")

    msg = EmailMessage()
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content("Buenos días,\n\nAdjunto captura del dashboard.\n\nSaludos.\n")

    with open(attachment_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename=os.path.basename(attachment_path))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    print("📤 Correo enviado exitosamente.")


if __name__ == "__main__":
    final_img = capture_dashboard()
    #Se toma variable desde archivo .env
    if SEND_EMAIL:
        send_email(final_img)
