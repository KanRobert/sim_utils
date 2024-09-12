#!/usr/bin/env python3

import os, smtplib, subprocess, mimetypes, socket, sys
import pandas as pd


from argparse import ArgumentParser
from email.policy import SMTP
from pretty_html_table import build_table
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def file_to_html_str(path):
    with open(path, 'r') as fp:
        content = fp.read().replace('\n','<br>')
    return content

def add_attachment(msg, f):
    with open(f, "rb") as fil:
        part = MIMEApplication(
            fil.read(),
            Name=os.path.basename(f)
        )
    # After the file is closed
    part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(f)
    msg.attach(part)

def main():
    parser = ArgumentParser(
        description='Send report as a MIME message. Unless the -o option is given, the email is sent by forwarding to your local SMTP server, which then does the normal delivery process')
    parser.add_argument('dir', help='directory of the inputs')
    parser.add_argument('--subject', help='the value of the Subject: header')
    parser.add_argument('-s', '--sender', help='the value of the From: header')
    parser.add_argument('-r', '--recipient', action='append', metavar='RECIPIENT', default=[], dest='recipients', help='a To: header value')
    parser.add_argument('-a', '--attach', action='append', metavar='ATTACHMENT', default=[], dest='attachments', help='add a attachment')
    parser.add_argument('-o', '--output', metavar='FILE', help='print the composed message to a HTML FILE')
    parser.add_argument('--csv', action='append', required=True, help='csv file to display as a table in message')
    parser.add_argument('--text', action='append', help='cat the file to body of the message')
    args = parser.parse_args()

    directory = os.path.abspath(args.dir)
    hostname = socket.gethostname()
    file_location = f'{hostname}:{directory}'
    subject = args.subject if args.subject else f'Summary for {file_location}'
    usermail = subprocess.run(['git', 'config', 'user.email'], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
    sender = args.sender if args.sender else usermail
    recipients = ', '.join(args.recipients) if args.recipients else usermail

    # Create the message
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['To'] = recipients
    msg['From'] = sender
    msg.preamble = 'You will not see this in a MIME-aware mail reader.\n'

    # Add attachments
    for attachment in args.attachments:
        if not os.path.isfile(attachment):
            print(f'warning: {attachment} is not a file', file=sys.stderr)
            continue
        add_attachment(msg, attachment)

    all_body_content = ''
    # Display the CSVs
    for csv in args.csv:
        csv_name = os.path.basename(csv)[:-4]
        all_body_content += f'<h1>{csv_name}</h1>'
        # Convert to pretty HTML table via Pandas/etc.
        df = pd.read_csv(csv)
        table_out = build_table(df,
                        'blue_dark',
                         font_size='12px',
                         width='100px',
                         text_align='center',
                         padding='1px 1px 1px 1px',
                         )
        all_body_content += table_out

    # Display the text files
    for text in args.text or []:
        text_name = os.path.basename(text)
        all_body_content += f'<h1>{text_name}</h1>'
        all_body_content += file_to_html_str(text)


    # Point out file location
    all_body_content += '<h1>File Location</h1>'
    all_body_content += f'{file_location}<br>'

    # Attach body
    msg.attach(MIMEText(all_body_content, 'html'))

    # Now send or store the message
    if args.output:
        with open(args.output, 'wb') as fp:
            fp.write(msg.as_bytes(policy=SMTP))
    else:
        with smtplib.SMTP('localhost') as s:
            s.send_message(msg)


if __name__ == '__main__':
    main()
