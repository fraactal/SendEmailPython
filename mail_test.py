import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configura tus datos SMTP
smtp_host = 'smtp.gmail.com'
smtp_port = 587  # Usa 465 si es SSL
smtp_user = 'jonathan.valdes.o@gmail.com'
smtp_pass = '50*2=Cien'

# Crea el mensaje
msg = MIMEMultipart()
msg['From'] = smtp_user
msg['To'] = 'jonathan.valdes@darts-ti.com'
msg['Subject'] = 'Asunto del correo'

# Cuerpo del mensaje
body = 'Hola, este es un correo enviado desde Python.'
msg.attach(MIMEText(body, 'plain'))

# Enviar el correo
try:
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()  # Seguridad TLS
    server.login(smtp_user, smtp_pass)
    server.send_message(msg)
    server.quit()
    print('Correo enviado exitosamente')
except Exception as e:
    print(f'Error al enviar el correo: {e}')