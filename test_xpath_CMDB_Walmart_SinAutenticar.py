from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from PIL import Image
import smtplib
import os
import time
import shutil

# Configuración
GRAFANA_SERVIDOR_DYS = "10.10.26.250:3000"
GRAFANA_URL_LOGIN = f"http://{GRAFANA_SERVIDOR_DYS}/login"
GRAFANA_DASHBOARD_URL = f"http://{GRAFANA_SERVIDOR_DYS}/d/pbU_ZwTSz/consolidado-mdlw-add-cmdb?orgId=1"
GRAFANA_USERNAME = "admin"
GRAFANA_PASSWORD = "rene2603"

OUTPUT_DIR = "captures"
FINAL_IMAGE = "dashboard_CMDB_walmart.png"

def capture_dashboard():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1380")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

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
    container = driver.find_element(By.XPATH, '//*[@id="reactRoot"]/div[1]/main/div[3]/div/div/div[1]')
    scroll_height = driver.execute_script("return arguments[0].scrollHeight", container)
    viewport_height = 1080
    steps = scroll_height // viewport_height + 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    image_paths = []

    for i in range(steps):
        y = i * viewport_height
        driver.set_window_size(1920, viewport_height + 200)
        driver.execute_script("arguments[0].scrollTo(0, arguments[1]);", container, y)
        print(f"🕒 Capturando sección {i + 1}/{steps}...")
        time.sleep(1.5)
        filename = f"{OUTPUT_DIR}/screenshot_{i}.png"
        driver.save_screenshot(filename)
        image_paths.append(filename)

    driver.quit()

    print("🧵 Uniendo capturas...")
    stitched_image = stitch_images(image_paths)
    stitched_image.save(FINAL_IMAGE)
    print(f"✅ Imagen final guardada como {FINAL_IMAGE}")

    print("🧹 Limpiando capturas temporales...")
    clean_up_temp_images()

def stitch_images(image_paths):
    images = [Image.open(img) for img in image_paths]
    widths, heights = zip(*(img.size for img in images))
    total_height = sum(heights)
    max_width = max(widths)

    stitched_img = Image.new('RGB', (max_width, total_height))

    y_offset = 0
    for img in images:
        stitched_img.paste(img, (0, y_offset))
        y_offset += img.height

    return stitched_img

def clean_up_temp_images():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        print(f"🗑️ Carpeta '{OUTPUT_DIR}' eliminada.")

def send_mail_host_Sin_Autenticar():
    smtp_host = "smtp.dys.corp"
    smtp_port = 25
    from_address = "middleware@dys.corp"
    to_address = [
        "jonathan.valdes@darts-ti.com",
        # Puedes agregar más destinatarios aquí
    ]

    image_filename = FINAL_IMAGE

    if not os.path.exists(image_filename):
        print(f"❌ Imagen no encontrada: {image_filename}")
        return

    html_body = f"""
    <html>
        <body>
            <h2>Correo con Imagen Inline y Adjunta</h2>
            <p>Hola,<br><br>Este es un correo de prueba enviado desde un script en Python.</p>
            <p>A continuación, verás una imagen inline:</p>
            <img src="cid:image1" alt="Imagen Inline" style="width:800px;height:auto;">
            <p>Saludos,<br>Middleware Team</p>
        </body>
    </html>
    """

    msg = MIMEMultipart("related")
    msg["From"] = from_address
    msg["To"] = ", ".join(to_address)
    msg["Subject"] = "Reporte Diario: Dashboard CMDB"

    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_body, "html"))

    try:
        with open(image_filename, "rb") as img_file:
            mime_image = MIMEImage(img_file.read())
            mime_image.add_header("Content-ID", "<image1>")
            mime_image.add_header("Content-Disposition", "inline", filename=image_filename)
            msg.attach(mime_image)

        with open(image_filename, "rb") as img_file:
            attached_image = MIMEImage(img_file.read())
            attached_image.add_header("Content-Disposition", f"attachment; filename={image_filename}")
            msg.attach(attached_image)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.send_message(msg)
            print("📧 Correo enviado exitosamente con send_message()")
    except Exception as e:
        print(f"❌ Error al enviar el correo: {e}")

if __name__ == "__main__":
    capture_dashboard()
    send_mail_host_Sin_Autenticar()
