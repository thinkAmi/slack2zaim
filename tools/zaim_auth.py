"""
Zaimのアクセストークンを取得する
"""

from zaim_client import ZaimClient


if __name__ == '__main__':
    client = ZaimClient()
    client.print_access_token()
