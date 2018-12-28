"""
Zaim上の情報を元に、カテゴリ・ジャンル情報をprintする
printされた情報は、Cloud Functionsの環境変数としてそのまま貼り付けられる

また、category.jsonやgenre.jsonとしても保存される
"""

from zaim_client import ZaimClient


if __name__ == '__main__':
    client = ZaimClient()
    print('-' * 30)
    print('カテゴリ')
    print('-' * 30)
    client.update_json_for_category()
    print('-' * 30)
    print('ジャンル')
    print('-' * 30)
    client.update_json_for_genre()
