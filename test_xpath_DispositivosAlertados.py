from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from email.message import EmailMessage
from PIL import Image
import smtplib
import os
import time
import shutil

# Configuración
GRAFANA_SERVIDOR_DYS = "10.10.26.250:3000"
#GRAFANA_SERVIDOR_COM = "10.86.108.223:3000"
GRAFANA_URL_LOGIN = "http://"+GRAFANA_SERVIDOR_DYS+"/login"
GRAFANA_DASHBOARD_URL = "http://"+GRAFANA_SERVIDOR_DYS+"/d/0vENUxwIk/dispositivos-alertados-v2?orgId=1&refresh=30s"
GRAFANA_USERNAME = "admin"
GRAFANA_PASSWORD = "rene2603"

OUTPUT_DIR = "captures"
FINAL_IMAGE = "dashboard_dispositivosAlertados.png"
SMTP_SERVER = "smtp.tuservidor.com"
SMTP_PORT = 587
SMTP_USER = "usuario@email.com"
SMTP_PASSWORD = "tu_contraseña"
EMAIL_TO = "destinatario@email.com"
EMAIL_FROM = SMTP_USER

def capture_dashboard():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Activar si no deseas ver el navegador
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
    #container = driver.find_element(By.XPATH, '//*[@id="reactRoot"]/div[1]/main/div[3]/div')
    # 
    scroll_height = driver.execute_script("return arguments[0].scrollHeight", container)
    viewport_height = 1080
    steps = scroll_height // viewport_height + 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    image_paths = []

    for i in range(steps):
        y = i * viewport_height
        #driver.set_window_size(1920, viewport_height + 200)  # Extender altura para evitar cortes
        driver.set_window_size(1920, viewport_height + 200)  # Extender altura para evitar cortes
        driver.execute_script("arguments[0].scrollTo(0, arguments[1]);", container, y)
        print(f"🕒 Esperando para cargar la sección {i+1}/{steps}...")
        time.sleep(1.5)
        filename = f"{OUTPUT_DIR}/screenshot_{i}.png"
        driver.save_screenshot(filename)
        image_paths.append(filename)
        print(f"📸 Captura {i+1}/{steps} guardada.")

    driver.quit()

    print("🧵 Uniendo capturas...")
    stitched_image = stitch_images(image_paths)
    stitched_image.save(FINAL_IMAGE)
    print(f"✅ Imagen final guardada como {FINAL_IMAGE}")

    print("🧹 Eliminando imágenes temporales...")
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

def send_email():
    msg = EmailMessage()
    msg['Subject'] = '📈 Dashboard Completo - Grafana'
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg.set_content('Hola,\n\nAdjunto el dashboard completo en una sola imagen.\n\nSaludos.')

    with open(FINAL_IMAGE, 'rb') as f:
        msg.add_attachment(f.read(), maintype='image', subtype='png', filename=FINAL_IMAGE)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        print("📤 Correo enviado exitosamente.")

if __name__ == "__main__":
    capture_dashboard()
    #send_email()
