from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from PIL import Image

import smtplib
from email.message import EmailMessage

import os
import time
import shutil
from datetime import datetime


# ---------------- CONFIG ----------------
GRAFANA_SERVIDOR_DYS = "10.10.26.250:3000"
GRAFANA_URL_LOGIN = "http://" + GRAFANA_SERVIDOR_DYS + "/login"
GRAFANA_DASHBOARD_URL = "http://" + GRAFANA_SERVIDOR_DYS + "/d/pbU_ZwTSz/consolidado-mdlw-add-cmdb?orgId=1"
GRAFANA_USERNAME = "admin"
GRAFANA_PASSWORD = "rene2603"

OUTPUT_DIR = "captures"
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
FINAL_IMAGE = f"dashboard_CMDB_{timestamp}.png"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "jonas.aws.777@gmail.com"
SMTP_PASSWORD = "ctbc tjap evmn dtmh"
EMAIL_TO = "jonathan.valdes.o@gmail.com,jonathan.valdes@darts-ti.com,ignacio.riquelme@darts-ti.com,daniel.torres@darts-ti.com,jonathan.valdes@walmart.com"
EMAIL_FROM = SMTP_USER


# ---------------- CAPTURE ----------------
def capture_dashboard():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1380")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

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

        # Contenedor scrolleable (puede variar según versión/tema)
        container = driver.find_element(By.XPATH, '//*[@id="reactRoot"]/div[1]/main/div[3]/div/div/div[1]')

        # Inicio arriba
        driver.execute_script("arguments[0].scrollTo(0, 0);", container)
        time.sleep(1)

        viewport_height = driver.execute_script("return arguments[0].clientHeight", container)

        # Solape para evitar "cortes" entre capturas
        overlap = 140
        step = max(viewport_height - overlap, 200)

        os.makedirs(OUTPUT_DIR, exist_ok=True)

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

            # ✅ IMPORTANTE: Grafana a veces ajusta el scroll, capturamos el valor REAL
            real_y = driver.execute_script("return arguments[0].scrollTop;", container)

            filename = os.path.join(OUTPUT_DIR, f"screenshot_{i}.png")
            container.screenshot(filename)
            shots.append((filename, real_y))

            print(f"📸 Captura {i+1} (real_y={real_y} / max_y={max_y})")

            # Si no avanzamos, cortamos (evita duplicado final)
            if real_y == last_real_y:
                stuck_count += 1
            else:
                stuck_count = 0
            last_real_y = real_y

            if stuck_count >= 2:
                break

            # Si estamos a ~5px del final, cortamos
            if (max_y - real_y) < 5:
                break

            i += 1

        print("🧵 Uniendo capturas...")
        stitched_image = stitch_images_dynamic(shots, viewport_height)
        stitched_image.save(FINAL_IMAGE)
        print(f"✅ Imagen final guardada como {FINAL_IMAGE}")

    finally:
        driver.quit()
        print("🧹 Eliminando imágenes temporales...")
        clean_up_temp_images()


# ---------------- STITCH ----------------
def stitch_images_dynamic(shots, viewport_height):
    """
    Une capturas eliminando duplicación según el overlap REAL.
    shots: [(filepath, real_scrollTop), ...]
    viewport_height: fallback si hace falta
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

        # Overlap real (cuánto se repite)
        overlap_px = (prev_y + (prev_img_h or viewport_height)) - y
        overlap_px = max(0, min(overlap_px, img.size[1] - 1))

        if overlap_px > 0:
            w, h = img.size
            img = img.crop((0, overlap_px, w, h))

        processed.append(img)

        # Actualiza referencias usando imagen original anterior
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


# ---------------- CLEANUP ----------------
def clean_up_temp_images():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
        print(f"🗑️ Carpeta '{OUTPUT_DIR}' eliminada.")


# ---------------- EMAIL (opcional) ----------------
def send_email():
    msg = EmailMessage()
    msg["Subject"] = "📈 Servidores Middleware"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content(
        "Buenos días,\n\nAdjunto Estado de los servidores MDW.\n\nSaludos Cordiales,\nEquipo Darts-TI.\n\n"
    )

    with open(FINAL_IMAGE, "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename=FINAL_IMAGE)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        print("📤 Correo enviado exitosamente.")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    capture_dashboard()
    send_email()
