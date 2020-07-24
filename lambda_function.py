from __future__ import print_function

import email.utils
import json
import os
import secrets
import smtplib
import time
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3


def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))
    message = event['Records'][0]['Sns']['Message']
    print("From SNS: " + message)
    uid = db_handler(message)
    sendEmail(message, uid)
    return message


def db_handler(email):
    # Create an SNS client
    client = boto3.client("dynamodb")
    # check if existed
    response = client.get_item(TableName='csye6225',
                               Key={'email': {
                                   'S': email
                               }})
    if "Item" in response:
        uuid_str = response["Item"]["uuid"]["S"]
        print("email existed!")
    else:
        # create new token
        uuid_str = str(uuid.uuid4())
        token_str = str(secrets.token_hex(16))
        ttl_time = str(int(time.time() + 900))
        client.put_item(TableName='csye6225',
                        Item={
                            "email": {
                                'S': email
                            },
                            "token": {
                                'S': token_str
                            },
                            "uuid": {
                                'S': uuid_str
                            },
                            "TimeToExist": {
                                'N': ttl_time
                            }
                        })
        print("new email")
    print(uuid_str)
    return uuid_str


def sendEmail(email_address, uuid_str):
    RECIPIENT = email_address
    SENDER = 'password-reset@prod.lazyless.me'
    SENDERNAME = 'Jing Yang'
    USERNAME_SMTP = os.environ.get('USERNAME_SMTP')
    PASSWORD_SMTP = os.environ.get('PASSWORD_SMTP')
    HOST = "email-smtp.us-east-1.amazonaws.com"
    PORT = 587
    SUBJECT = 'Password Reset'

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = SUBJECT
    msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
    msg['To'] = RECIPIENT

    # The HTML body of the email.
    BODY_HTML = """<html>
    <head><h1>Password Reset</h1></head>
    <body>
    <h3>Click Link Below to Reset Your Password</h3>
    <p>
        <a href='http://prod.lazyless.me/accounts/restore/{email_address}/{uuid_str}/'>This Link</a>
    </p>
    <h3>Or Copy This Link and Open in Your Browser to Reset Your Password</h3>
    <p>
        http://prod.lazyless.me/accounts/restore/{email_address}/{uuid_str}/
    </p>
    </body>
    </html>
                """.format(email_address=email_address, uuid_str=uuid_str)

    part2 = MIMEText(BODY_HTML, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.

    msg.attach(part2)

    # Try to send the message.
    try:
        server = smtplib.SMTP(HOST, PORT)
        server.ehlo()
        server.starttls()
        #stmplib docs recommend calling ehlo() before & after starttls()
        server.ehlo()
        server.login(USERNAME_SMTP, PASSWORD_SMTP)
        server.sendmail(SENDER, RECIPIENT, msg.as_string())
        server.close()
    # Display an error message if something goes wrong.
    except Exception as e:
        print("Error: ", e)
    else:
        print("Email sent!")
