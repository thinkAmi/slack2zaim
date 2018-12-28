""" GCP Cloud Functions を使って、SlackからZaimへデータをPostするためのスクリプト """

import json
import logging
import os
import unicodedata
from datetime import datetime
from threading import Thread

import zaim
from slackclient import SlackClient


def background(request_data):
    """ Cloud Functionsの別スレッドで動作する関数 """

    # 登録可能なジャンルを知りたい場合
    has_genre_response = response_all_genre(request_data)
    if has_genre_response:
        return

    # Zaimへ登録するためのフォーマットを知りたい場合
    has_format_response = response_format(request_data)
    if has_format_response:
        return

    error_msg, zaim_data = create_zaim_data(request_data)

    if zaim_data:
        error_msg = post_zaim(zaim_data)

    client = SlackClient(os.environ['SLACK_TOKEN'])
    if error_msg:
        # 念のため、ログにもエラーメッセージを出力しておく
        logging.debug(error_msg)

        # エラーの場合、NGリアクションとスレッドにエラーメッセージをポスト
        client.api_call(
            'reactions.add',
            name='man-gesturing-no',
            channel=request_data['channel_id'],
            timestamp=request_data['timestamp'],
        )
        client.api_call(
            'chat.postMessage',
            channel=request_data['channel_id'],
            thread_ts=request_data['timestamp'],
            text=error_msg,
        )
    else:
        client.api_call(
            'reactions.add',
            name='man-gesturing-ok',
            channel=request_data['channel_id'],
            timestamp=request_data['timestamp'],
        )


def response_all_genre(request_data):
    """ ジャンルを知りたい場合は、環境変数にあるジャンル一覧をスレッドとして返信する """
    text = request_data.get('text')
    if text != 'ジャンル':
        return False

    genre = load_genre()
    all_genre = ', '.join(genre.keys())

    client = SlackClient(os.environ['SLACK_TOKEN'])

    client.api_call(
        'reactions.add',
        name='book',
        channel=request_data['channel_id'],
        timestamp=request_data['timestamp'],
    )

    client.api_call(
        'chat.postMessage',
        channel=request_data['channel_id'],
        thread_ts=request_data['timestamp'],
        text=all_genre,
    )
    return True


def response_format(request_data):
    """ Zaimへ投稿するフォーマットを知りたい場合は、環境変数にあるジャンル一覧をスレッドとして返信する """
    text = request_data.get('text')
    if text not in ('書式', 'フォーマット'):
        return False

    text = '日付(yyyy/mm/dd or mm/dd) ジャンル名 金額 コメント ' \
           '(4項目は順不同、区切りはスペース(全角/半角どちらでも可))'

    client = SlackClient(os.environ['SLACK_TOKEN'])

    client.api_call(
        'reactions.add',
        name='memo',
        channel=request_data['channel_id'],
        timestamp=request_data['timestamp'],
    )

    client.api_call(
        'chat.postMessage',
        channel=request_data['channel_id'],
        thread_ts=request_data['timestamp'],
        text=text,
    )
    return True


def create_zaim_data(request_data):
    """ Zaimデータを作成する

    :param request_data: リクエストされたデータ
    :return: エラーメッセージ, Zaimデータ
    :rtype: str, dict
    """
    text = request_data.get('text')
    if not text:
        return '登録データがありません', None

    zaim_data = parse_zaim_data(text)
    if len(zaim_data.keys()) != 5:
        return f'登録するための項目が不足しています :{zaim_data}', None

    return None, zaim_data


def parse_zaim_data(text):
    """ SlackのポストをZaimデータにparseする

    :param text: Slackのポスト
    :return: Zaimデータ
    :rtype: dict
    """

    # Slackポストのフォーマット
    # 項目：日付、ジャンル名、金額、コメント (順不同、区切りはスペース(全角/半角どちらでも可))
    # 各項目や区切り文字は全角/半角のどちらでも可とするため、内部では正規化して処理する
    text_normalized = unicodedata.normalize('NFKC', text)

    # 入力項目ごとに区切る
    words = text_normalized.split()

    results = {}
    genre = load_genre()
    for word in words:
        if '/' in word:
            results['date'] = get_date(word)
        elif word.isdigit():
            results['amount'] = int(word)
        elif word in genre:
            category_id, genre_id = get_ids(word)
            if category_id and genre_id:
                results['category_id'], results['genre_id'] = category_id, genre_id
        else:
            today = datetime.today()
            results['comment'] = f'{word} (Slack登録: {today.year}/{today.month}/{today.day})'

    return results


def get_ids(word):
    """ カテゴリID、ジャンルIDを取得する

    :param word: ジャンルっぽい文字列
    :return: カテゴリID, ジャンルID (存在しない場合: None, None)
    :rtype: str, str
    """
    genres = load_genre()
    genre = genres.get(word)
    if genre:
        return genre['category_id'], genre['genre_id']
    return None, None


def load_genre():
    """ 環境変数からジャンルを取得し、Pythonオブジェクト化する """
    genre = os.environ.get('ZAIM_GENRE')
    if not genre:
        return

    return json.loads(genre)


def get_date(date_text):
    """ スラッシュ区切りで日付を指定

    01/01 -> 同年の1/1
    1/1 -> 同上
    2018/1/1 -> 年数も考慮
    それ以外 -> 判断つかないので、本日とする
    """
    date_list = date_text.split('/')
    if len(date_list) == 2:  # 月日のみ
        str_date = f'{datetime.today().year}{date_list[0].zfill(2)}{date_list[1].zfill(2)}'
        return datetime.strptime(str_date, '%Y%m%d')

    if len(date_list) == 3:  # 年月日
        str_date = f'{date_list[0]}{date_list[1].zfill(2)}{date_list[2].zfill(2)}'
        return datetime.strptime(str_date, '%Y%m%d')

    return datetime.today()


def post_zaim(zaim_data):
    """ Zaim APIにポストする

    :param zaim_data: Zaimにポストするためのデータ
    :return: 正常の場合はNone、エラーがある場合はエラーメッセージ
    :rtype: None or str
    """
    try:
        api = zaim.Api(consumer_key=os.environ['CONSUMER_KEY'],
                       consumer_secret=os.environ['CONSUMER_SECRET'],
                       access_token=os.environ['OAUTH_TOKEN'],
                       access_token_secret=os.environ['OAUTH_TOKEN_SECRET'])
        api.verify()

        # api.payment()の戻り値は以下の通り。そのため、戻り値を使って何かする、ということは無い
        # 正常：レスポンスのJSON内容が返ってくる
        # エラー：例外が出る
        api.payment(
            # 存在しないcategory_idでPOSTすると、「振替」だけれど変なデータができてしまうが、OKで通る
            # ただし、数字のところに文字列を入れると、例外が発生する
            # category_id="101xx",
            category_id=zaim_data['category_id'],
            genre_id=zaim_data['genre_id'],
            amount=zaim_data['amount'],
            date=zaim_data['date'],
            comment=zaim_data['comment']
        )
        return None
    except Exception as e:
        return str(e)


def main(request):
    """ Cloud Functions 呼ばれるメインの関数 """
    # Outgoing WebHooks App からは、POSTしかデータ送信されない前提なので、.formを使う
    # クエリストリングも同時に取得したい場合は .values を使う
    # 毎回 reqest.formと書くのが手間なので、変数に入れておく
    request_data = request.form

    # Outgoing Webhooks アプリだと、本来のアプリの他に、1,2回アクセスがある
    # この場合、request.formは空になっている
    if not request_data:
        logging.info(f'empty form data:{request_data}')
        return ''

    # Outgoing WebHooks アプリからの送信かどうかのバリデーション
    if request_data.get('token') != os.environ['SLACK_OUTGOING_WEBHOOKS_TOKEN']:
        logging.warning(f'not slack access, data: {request_data}')
        return ''

    # Botの場合に返信してしまうと、無限ループになるため除外する
    if request_data.get('user_name') == 'slackbot':
        logging.info(f'bot access data:{request_data.get("text")}')
        return ''

    # Slackの3秒ルールがあるため、リクエストが届いたということを通知するために
    # メイン処理は別スレッドに流して、ここは HTTP 200 をすぐに返す
    t = Thread(target=background, kwargs={'request_data': request_data})
    t.start()
    return ''
