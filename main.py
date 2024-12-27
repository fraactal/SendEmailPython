import os 
from dotenv import load_dotenv # pip intall python-dotenv
from email.message import EmailMessage
import ssl
import smtplib

load_dotenv()

email_sender = "jonas.aws.777@gmail.com"
password = os.getenv("PASSWORD")
#email_reciver = "jonathan.valdes.o@gmail.com"
email_reciver = "carolina.labras@gmail.com"
subject = "Python Email"
body= """
    Correo de prueba enviado desde python
"""

em = EmailMessage()
em["From"] = email_sender
em["To"] = email_reciver
em["Subject"] = subject
em.set_content(body)

#Enviarlo de forma segura libreria ssl
context = ssl.create_default_context()

with smtplib.SMTP_SSL("smtp.gmail.com",465,context=context) as smtp:
    smtp.login(email_sender,password)
    smtp.sendmail(email_sender,email_reciver,em.as_string())

