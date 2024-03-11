import base64
import email
import logging
import os.path
import pickle

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

LOG = logging.getLogger("mc_donald")
# 如果修改了 SCOPES，删除 token.pickle 文件
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
creds = None
# token.pickle 存储了用户的访问令牌和刷新令牌，由第一次运行脚本创建
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# 如果没有有效的凭证，让用户登录
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # 保存凭证以备下次运行
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
service = build('gmail', 'v1', credentials=creds)


def refresh_mail(messages):
    if not messages:
        LOG.info('No new messages.')
    else:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='raw').execute()
            msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
            mime_msg = email.message_from_bytes(msg_str)

            try:
                if mime_msg.is_multipart():
                    for part in mime_msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/html":
                            return part.get_payload(decode=True).decode()
                else:
                    if mime_msg.get_content_type() == "text/html":
                        return mime_msg.get_payload(decode=True).decode()
            finally:
                mark_message_as_read(message['id'])


def get_mail():
    # 调用Gmail API
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
    messages = results.get('messages', [])
    return refresh_mail(messages)


def find_verify_email_link():
    html_content = get_mail()
    if html_content:
        soup = BeautifulSoup(html_content, 'lxml')
        a_tags = soup.find_all('a')
        for tag in a_tags:
            if 'Verify Email' in tag.text:
                return tag['href']
    return None


def mark_message_as_read(message_id):
    """
    将指定的邮件标记为已读。
    :param user_id: 用户的邮箱地址或者特殊值'me'，代表当前授权用户。
    :param message_id: 要标记为已读的邮件的ID。
    """
    try:
        # 使用users.messages.modify API方法移除'UNREAD'标签
        service.users().messages().modify(userId='me', id=message_id, body={'removeLabelIds': ['UNREAD']}).execute()
        LOG.info(f"Message {message_id} marked as read.")
    except Exception as error:
        LOG.error(f"An error occurred: {error}")


if __name__ == '__main__':
    print(find_verify_email_link())
