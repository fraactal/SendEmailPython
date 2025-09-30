from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image
import smtplib
import os
import time
import shutil

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os

# Configuración
GRAFANA_SERVIDOR_DYS = "10.10.26.250:3000"
#GRAFANA_SERVIDOR_COM = "10.86.108.223:3000"
GRAFANA_URL_LOGIN = "http://"+GRAFANA_SERVIDOR_DYS+"/login"
GRAFANA_DASHBOARD_URL = "http://"+GRAFANA_SERVIDOR_DYS+"/d/pbU_ZwTSz/consolidado-mdlw-add-cmdb?orgId=1"
GRAFANA_USERNAME = "admin"
GRAFANA_PASSWORD = "rene2603"

OUTPUT_DIR = "captures"
FINAL_IMAGE = "dashboard_CMDB_walmart.png"

#SMTP_SERVER = "smtp.gmail.com"
#SMTP_PORT = 587
#SMTP_USER = "jonas.aws.777@gmail.com"
#SMTP_PASSWORD = "ctbc tjap evmn dtmh"
#EMAIL_TO = "angel.rojas@walmart.com,natalia.herrera0@walmart.com,alvaro.navarro@darts-ti.com,daniel.torres@darts-ti.com,jonathan.valdes@walmart.com"
#EMAIL_TO = "angel.rojas@walmart.com,natalia.herrera0@walmart.com,alvaro.navarro@darts-ti.com,daniel.torres@darts-ti.com,jonathan.valdes@walmart.com"
#EMAIL_FROM = SMTP_USER



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
    msg['Subject'] = '📈 Servidores Middleware'
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg.set_content('Buenos días,\n\nAdjunto Estado de los servidores MDW.\n\nSaludos Cordiales,\nJonathan Valdés.\n\n')

    with open(FINAL_IMAGE, 'rb') as f:
        msg.add_attachment(f.read(), maintype='image', subtype='png', filename=FINAL_IMAGE)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        print("📤 Correo enviado exitosamente.")

def send_mail_host():

    # Configuración del servidor SMTP
    #smtp_host = "smtp.dys.corp"
    #smtp_port = 25
    #from_address = "middleware@dys.corp"
    #to_address = "jonathan.valdes@darts-ti.com"  # Reemplaza con el destinatario

    smtp_host = "smtp.dys.corp"
    smtp_port = 25
    #from_address = "middleware@dys.corp"
    from_address = "svc_grafanacorreo_dys@dys.corp"
    smtp_password = "Sv.graf-559"
    to_address = "jonathan.valdes@darts-ti.com"


    # Ruta de la imagen (en el mismo directorio del script)
    image_filename = "dashboard_CMDB_walmart.png"  # Cambia el nombre de la imagen según corresponda

    # Cuerpo del correo en formato HTML (para mostrar la imagen inline)
    html_body = f"""
    <html>
        <body>
            <h2>Correo con Imagen Inline y Adjunta</h2>
            <p>Hola,<br><br>Este es un correo de prueba enviado desde un script en Python.</p>
            <p>A continuación, verás una imagen inline:</p>
            <img src="cid:image1" alt="Imagen Inline" style="width:300px;height:auto;">
            <p>Saludos,<br>Middleware Team</p>
        </body>
    </html>
    """

    # Crear el mensaje
    msg = MIMEMultipart("related")
    msg["From"] = from_address
    msg["To"] = to_address
    msg["Subject"] = "Correo con Imagen Inline y Adjunta"

    # Adjuntar el cuerpo HTML
    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_body, "html"))

    try:
        # Adjuntar la imagen (inline)
        with open(image_filename, "rb") as img_file:
            mime_image = MIMEImage(img_file.read())
            mime_image.add_header("Content-ID", "<image1>")  # Para inline en el HTML
            mime_image.add_header("Content-Disposition", "inline", filename=image_filename)
            msg.attach(mime_image)

        # Adjuntar la imagen como archivo adjunto
        with open(image_filename, "rb") as img_file:
            attached_image = MIMEImage(img_file.read())
            attached_image.add_header("Content-Disposition", f"attachment; filename={image_filename}")
            msg.attach(attached_image)


        # Conectar al servidor SMTP y enviar el correo
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(from_address, smtp_password)
            server.sendmail(from_address, to_address, msg.as_string())
            print("Correo enviado exitosamente con imagen inline y adjunta")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")


if __name__ == "__main__":
    capture_dashboard()
    #send_email()
    send_mail_host() #funciona



##########

'''
#################################### SMTP / Emailing ##########################
[smtp]

enabled = true
host = smtp.dys.corp:25
#user = z3drodriguezt
#password = "Lider.2025"
skip_verify = true
#from_address = middleware@walmart.cl
from_address = middleware@dys.corp
from_name = Alertas

'''


''' 

nslookup smtp.dys.corp
Server:		10.10.10.100
Address:	10.10.10.100#53

Name:	smtp.dys.corp
Address: 10.10.24.123
Name:	smtp.dys.corp
Address: 10.10.24.120
Name:	smtp.dys.corp
Address: 10.10.24.170

zsh: command not found: telnet

'''



