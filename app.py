# DBは全データはBQ　画像はGCS

from fileinput import filename
import imghdr
import re
import base64
from sqlite3 import Timestamp
from typing import AsyncIterable
from flask import Flask, render_template, session, request, jsonify, redirect, make_response, send_file
# sessionでcookieに引っかかったみたい？
from itsdangerous import base64_decode
import numpy as np
import json

from pytz import timezone
import plotly
import plotly.express as px
import pandas as pd
from pandas.core.arrays import period
import matplotlib.pyplot as plt

from google.oauth2 import service_account
from google.cloud import language_v1
from google.cloud.bigquery import Client
from flask_login import LoginManager,  logout_user, logout_user, login_required
from flask_bootstrap import Bootstrap
from google.cloud import storage as gcs

from werkzeug.security import generate_password_hash, check_password_hash
import os

import datetime

import base64
# from PIL import Image
from io import BytesIO
from google.cloud import vision
import io

app = Flask(__name__)
credentials_path = 'kaitemite-6661bf07da7c.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
# app.config['GOOGLE_APPLICATION_CREDENTIALS'] = 'sqlite:///blog.db'
app.config['SECRET_KEY'] = os.urandom(24)
# db = SQLAlchemy(app)

bootstrap = Bootstrap(app)

client = Client()

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_name):
  query = f"select * from `kaitemite.user_table.user` where user_name = '{user_name}'"
  result = client.query(query)
  df = result.to_dataframe()
  dict = df.to_dict()
  return dict

#トップページ　全データ取得
@app.route('/', methods=['GET', 'POST'])
def index():
  if (session):
    if request.method== 'GET':

      query = f"select * from `kaitemite.user_table.data` order by created_at desc "
      result = client.query(query)
      df = result.to_dataframe()
      dict = df.to_dict()
      data = dict

      listOfDataImg = data['img_url'].values()
      listOfDataImg = list(listOfDataImg)

      listOfText = data['text'].values()
      listOfText = list(listOfText)

      listOfEmotion = data['sentiment'].values()
      listOfEmotion = list(listOfEmotion)
      
      listOfCreatedAt = data['created_at'].values()
      listOfCreatedAt = list(listOfCreatedAt)
      
      listOfUpdatedAt = data['updated_at'].values()
      listOfUpdatedAt = list(listOfUpdatedAt)

      posts = []

      # 数の分だけ出したいけど何回回せばいいん？？for文？
      # print(len(df))
      for index in range(len(df)):
        posts.append({'data_img': listOfDataImg[index], 'text': listOfText[index], 'emotion': listOfEmotion[index], 'created_at': listOfCreatedAt[index], 'updated_at': listOfUpdatedAt[index]})

      return render_template('index.html', posts=posts)
    
  else:
    return render_template('login.html')

# 新規登録　パスワード・名前登録
@app.route('/signup', methods=['GET', 'POST'])
def signup():
  if request.method == 'POST':
    user_name = str(request.form.get('user_name'))
    password = request.form.get('password')

    query = f"select * from `kaitemite.user_table.user`"

    result = client.query(query)
    df = result.to_dataframe()
    dict = df.to_dict()
    listOfValues = dict['user_name'].values()
    listOfValues = list(listOfValues)
    dict['password'][5]

    for value in listOfValues:
      if value == user_name:
        return render_template('signup.html', message = 'このユーザー名は既に使われています')

    # ユーザー登録の時の'created_at': datetime.now
    # print(datetime.now(pytz.timezone('Asia/Tokyo')))
    rows_to_insert = [{'user_name': user_name, 'password': password, 'created_at': datetime.datetime.now()}]


    table = client.get_table('kaitemite.user_table.user')
    errors = client.insert_rows(table, rows_to_insert)
    if errors == []:
      print('Success!')

    return redirect('/login')
  else:
    return render_template('signup.html')

# ログイン　パスワード・名前取得
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    password = request.form.get('password')
    user_name = str(request.form.get('user_name'))

    query = f"select * from `kaitemite.user_table.user` where user_name = '{user_name}'"

    result = client.query(query)
    df = result.to_dataframe()
    dict = df.to_dict()

    if int(password) == dict['password'][0]:
      session.permanent = True
      session['user'] = dict
      return redirect('/')
    else:
      return render_template('login.html', message='再度ログイン　または　新規登録してください')


  else:
    return render_template('login.html')

# ログアウト　
@app.route('/logout')
def logout():
    if logout_user():
     return redirect('/login')
    
# トップ画面で全情報を取得
@app.route('/create', methods=['GET', 'POST'])
def create():
  if request.method == "POST":
    img_str = re.search(r'base64,(.*)', request.json['img']).group(1)
    #エンコードされている
    # img = request.json['img']
    nparr = np.fromstring(base64.b64decode(img_str), np.uint8)
    s = base64.b64encode(nparr)
    r = base64.decodebytes(s)    
    ans =  detect_text(r)
    # 毎回フォルダが変わるようにユニーク（データの中で変わっていくやつを付け加える）
    # 手書きページの時のGCSに名前をつけるために代入？
    filename = datetime.datetime.now().strftime('%Y%m%d_%H%M_%S.png')

    svimg(r, filename)
    senti_res = sample_analyze_sentiment(ans)

    tokyo = datetime.datetime.now() 
    # print(pytz.timezone('Asia/Tokyo'))
    print(tokyo)
    # BQにデータを代入
    rows_to_insert = [{'img_url': 'https://storage.cloud.google.com/kaitemite.appspot.com//image/kaitemite' + filename, 'text': ans, 'sentiment': senti_res, 'created_at': tokyo, 'updated_at': tokyo}]

    table = client.get_table('kaitemite.user_table.data')
    errors = client.insert_rows(table, rows_to_insert)

    if errors == []:
      print('Success!')
    else:
      print(errors)

  #保存する部分　”20220408094716”こうゆう日付が入ってる　ここわからん
  #書いてAPIに飛ばした時間をtsに代入
    ts = datetime.datetime.now().strftime(format='%Y%m%d%H%M%S')
  # svimgにr＝画像を入れる？持っていく？
    svimg(r, ts)
    
    print(ts)  
    print(ans)
    return make_response({'ans': f'手書き文字認識の結果は : {ans}       ' + f'\t感情分析の結果は : {senti_res}'})
  else :
    return render_template('create.html')
     
# GCSに画像保存する関数
def svimg(image, filename): 
    credentials = service_account.Credentials.from_service_account_file('kaitemite-6661bf07da7c.json')
    project_id = "kaitemite"
    gcs_client = gcs.Client(project_id, credentials=credentials)
    bucket_name = "kaitemite.appspot.com"
    gcs_path = "/image/kaitemite{}".format(filename)  # 自分でファイル名決めてOK →　BQにこのアドレス保存すべし
    bucket = gcs_client.get_bucket(bucket_name)
    blob_gcs = bucket.blob(gcs_path)
    blob_gcs.upload_from_string(data=image, content_type="image/png")

# テキスト変換
def detect_text(content):
    """Detects text in the file."""
    
    credentials = service_account.Credentials.from_service_account_file('kaitemite-6661bf07da7c.json')
    client = vision.ImageAnnotatorClient(credentials=credentials)
    image = vision.Image(content=content)

    response = client.text_detection(image=image)
    texts = response.text_annotations
    if len(texts) > 0:
        out = re.sub('\n', '', [text.description for text in texts][0])
    else:
        out ='error'
    return out

    if response.error.message:
      raise Exception(
      '{}\nFor more info on error messages, check: '
      'https://cloud.google.com/apis/design/errors'.format(response.error.message))

# 感情分析
def sample_analyze_sentiment(text_content):
    """
    Analyzing Sentiment in a String

    Args:
      text_content The text content to analyze
    """
    credentials = service_account.Credentials.from_service_account_file('kaitemite-6661bf07da7c.json')
    client = language_v1.LanguageServiceClient(credentials=credentials)

    # text_content = 'I am so happy and joyful.'

    # Available types: PLAIN_TEXT, HTML
    type_ = language_v1.Document.Type.PLAIN_TEXT

    # Optional. If not specified, the language is automatically detected.
    # For list of supported languages:
    # https://cloud.google.com/natural-language/docs/languages
    language = "ja"
    document = {"content": text_content, "type_": type_, "language": language}

    # Available values: NONE, UTF8, UTF16, UTF32
    encoding_type = language_v1.EncodingType.UTF8

    response = client.analyze_sentiment(request = {'document': document, 'encoding_type': encoding_type})
    # Get overall sentiment of the input document
    print()
    return response.document_sentiment.score
    
@app.route('/sentiment')
def plot():
  
  df = pd.DataFrame({
    "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
    "Amount": [4, 1, 2, 2, 4, 5],
    "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
  })

  # dateidx = pd.date_range(start="2021-04-01", periods=365, freq='D' )
  # val1 = np.random.randint(low=-1, high=1, size=365)
  # df_timeseries_toyexample = pd.DataFrame({'date':dateidx, 'val1':val1,})
  # df_timeseries_toyexample.head()

  fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")
  # fig.show(plot)

  graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  header="Fruit in North America"
  description = """
  A academic study of the number of apples, oranges and bananas in the cities of
  San Francisco and Montreal would probably not come up with this chart.
  """
  return render_template('sentiment.html', graphJSON=graphJSON, header=header,description=description)



  # plt.figure(figsize=(12,6))
  # plt.plot(df_timeseries_toyexample['date'], df_timeseries_toyexample['val1'])
  # plt.show()

  # graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  # header="Fruit in North America"
  # description = """
  # A academic study of the number of apples, oranges and bananas in the cities of
  # San Francisco and Montreal would probably not come up with this chart.
  # """
  return render_template('login.html')

if __name__ == "__main__":
      app.run()