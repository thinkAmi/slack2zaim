""" tools/ の中で使うスクリプト用Zaimラッパー """

import json
import pathlib
import urllib.parse
import webbrowser

import requests
import zaim
from requests_oauthlib import OAuth1


class ZaimClient:
    def __init__(self):
        with pathlib.Path(__file__).parents[1].joinpath('secret.json').open(mode='r') as f:
            secrets = json.load(f)
        self.tokens = secrets['Zaim']

    def get_verified_api(self):
        """ 認証済のAPIクライアントを取得する """
        api = zaim.Api(consumer_key=self.tokens['CONSUMER_KEY'],
                       consumer_secret=self.tokens['CONSUMER_SECRET'],
                       access_token=self.tokens['ACCESS_TOKEN'],
                       access_token_secret=self.tokens['ACCESS_TOKEN_SECRET'])
        api.verify()
        return api

    def update_json_for_category(self):
        """ 環境変数用のカテゴリJSONファイルを更新 """
        response = self.get_categories()
        # 必要なのは、id-nameのdict
        results = {}
        for category in response['categories']:
            results[category['name']] = category['id']

        # キーに日本語が入るため、 ensure_asciiを指定する
        print(json.dumps(results, ensure_ascii=False))

        with pathlib.Path(__file__).parents[1].joinpath('category.json').open(mode='w') as f:
            json.dump(results, f, ensure_ascii=False)

    def get_categories(self):
        """ API経由でZaimのカテゴリを取得する """
        api = self.get_verified_api()
        return api.category()

    def update_json_for_genre(self):
        """ 環境変数用のジャンルJSONファイルを更新 """
        response = self.get_genres()
        results = {}
        for genre in response['genres']:
            results[genre['name']] = {
                'category_id': genre['category_id'],
                'genre_id': genre['id'],
            }

        # キーに日本語が入るため、 ensure_asciiを指定する
        print(json.dumps(results, ensure_ascii=False))

        with pathlib.Path(__file__).parents[1].joinpath('genre.json').open(mode='w') as f:
            json.dump(results, f, ensure_ascii=False)

    def get_genres(self):
        """ API経由でZaimのジャンルを取得する """
        api = self.get_verified_api()
        return api.genre()

    def print_access_token(self):
        """ Zaimのアクセストークンを取得・表示する

        OAuth1.0aの認証方法については、以下の記事を参考に実装
        https://qiita.com/kosystem/items/7728e57c70fa2fbfe47c
        """
        request_token = self._get_request_token()
        access_token = self._get_access_token(request_token)

        # ターミナル上にアクセストークンを表示する。形式は以下の通り
        # {'oauth_token': 'xxx', 'oauth_token_secret': 'yyy'}
        # oauth_token == ACCESS_TOKEN, oauth_token_secret == ACCESS_TOKEN_SECRET
        print(access_token)

    def _get_request_token(self):
        auth = OAuth1(
            self.tokens['CONSUMER_KEY'],
            self.tokens['CONSUMER_SECRET'],
            # CLIからの認証なので、RFC5849のsection-2.1より、 `oob` を指定しておく
            # https://tools.ietf.org/html/rfc5849#section-2.1
            callback_uri='oob')

        r = requests.post(self.tokens['REQUEST_TOKEN_URL'], auth=auth)
        return dict(urllib.parse.parse_qsl(r.text))

    def _get_access_token(self, request_token):
        # ブラウザを起動してOAuth認証確認画面を表示する
        # ユーザーが許可すると、「認証が完了」のメッセージとともにコードが表示される
        webbrowser.open(
            f'{self.tokens["AUTHORIZE_URL"]}?oauth_token={request_token["oauth_token"]}&perms=delete')

        # ターミナル上で、コードの入力を待つ(コード入力後、後続処理が行われる)
        oauth_verifier = input('コードを入力してください: ')

        auth = OAuth1(
            self.tokens['CONSUMER_KEY'],
            self.tokens['CONSUMER_SECRET'],
            request_token['oauth_token'],
            request_token['oauth_token_secret'],
            verifier=oauth_verifier)
        r = requests.post(self.tokens['ACCESS_TOKEN_URL'], auth=auth)

        access_token = dict(urllib.parse.parse_qsl(r.text))
        return access_token
