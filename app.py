import requests
import re
import random
import configparser
from bs4 import BeautifulSoup
from flask import Flask, request, abort, json, jsonify, Response, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import INTEGER
from sqlalchemy import or_, and_
from datetime import datetime
import googlemaps


from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://ytkxgelqgbtrhs:7d8fca1eb91192298d79771d68f05d69b5b35de8abf5ef120269698adeeecde2@ec2-54-243-40-26.compute-1.amazonaws.com:5432/dev2u2c1ds4u50'
db = SQLAlchemy(app)
config = configparser.ConfigParser()
config.read("config.ini")

line_bot_api = LineBotApi(config['line_bot']['Channel_Access_Token'])
handler = WebhookHandler(config['line_bot']['Channel_Secret'])

google_key = "AIzaSyCkXxylSFeJ0Q-vsTIfkC65PkfGIczMEiY"
gmaps = googlemaps.Client(key=google_key)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    # print("body:",body)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'ok'


def pattern_mega(text):
    patterns = [
        'mega', 'mg', 'mu', 'ＭＥＧＡ', 'ＭＥ', 'ＭＵ',
        'ｍｅ', 'ｍｕ', 'ｍｅｇａ', 'GD', 'MG', 'google',
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True


def eyny_movie():
    target_url = 'http://www.eyny.com/forum-205-1.html'
    print('Start parsing eynyMovie....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ''
    for titleURL in soup.select('.bm_c tbody .xst'):
        if pattern_mega(titleURL.text):
            title = titleURL.text
            if '11379780-1-3' in titleURL['href']:
                continue
            link = 'http://www.eyny.com/' + titleURL['href']
            data = '{}\n{}\n\n'.format(title, link)
            content += data
    return content


def apple_news():
    target_url = 'https://tw.appledaily.com/new/realtime'
    print('Start parsing appleNews....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for index, data in enumerate(soup.select('.rtddt a'), 0):
        if index == 5:
            return content
        link = data['href']
        content += '{}\n\n'.format(link)
    return content


def get_page_number(content):
    start_index = content.find('index')
    end_index = content.find('.html')
    page_number = content[start_index + 5: end_index]
    return int(page_number) + 1


def craw_page(res, push_rate):
    soup_ = BeautifulSoup(res.text, 'html.parser')
    article_seq = []
    for r_ent in soup_.find_all(class_="r-ent"):
        try:
            # 先得到每篇文章的篇url
            link = r_ent.find('a')['href']
            if link:
                # 確定得到url再去抓 標題 以及 推文數
                title = r_ent.find(class_="title").text.strip()
                rate = r_ent.find(class_="nrec").text
                url = 'https://www.ptt.cc' + link
                if rate:
                    rate = 100 if rate.startswith('爆') else rate
                    rate = -1 * int(rate[1]) if rate.startswith('X') else rate
                else:
                    rate = 0
                # 比對推文數
                if int(rate) >= push_rate:
                    article_seq.append({
                        'title': title,
                        'url': url,
                        'rate': rate,
                    })
        except Exception as e:
            # print('crawPage function error:',r_ent.find(class_="title").text.strip())
            print('本文已被刪除', e)
    return article_seq


def crawl_page_gossiping(res):
    soup = BeautifulSoup(res.text, 'html.parser')
    article_gossiping_seq = []
    for r_ent in soup.find_all(class_="r-ent"):
        try:
            # 先得到每篇文章的篇url
            link = r_ent.find('a')['href']

            if link:
                # 確定得到url再去抓 標題 以及 推文數
                title = r_ent.find(class_="title").text.strip()
                url_link = 'https://www.ptt.cc' + link
                article_gossiping_seq.append({
                    'url_link': url_link,
                    'title': title
                })

        except Exception as e:
            # print u'crawPage function error:',r_ent.find(class_="title").text.strip()
            # print('本文已被刪除')
            print('delete', e)
    return article_gossiping_seq


def ptt_gossiping():
    rs = requests.session()
    load = {
        'from': '/bbs/Gossiping/index.html',
        'yes': 'yes'
    }
    res = rs.post('https://www.ptt.cc/ask/over18', verify=False, data=load)
    soup = BeautifulSoup(res.text, 'html.parser')
    all_page_url = soup.select('.btn.wide')[1]['href']
    start_page = get_page_number(all_page_url)
    index_list = []
    article_gossiping = []
    for page in range(start_page, start_page - 2, -1):
        page_url = 'https://www.ptt.cc/bbs/Gossiping/index{}.html'.format(page)
        index_list.append(page_url)

    # 抓取 文章標題 網址 推文數
    while index_list:
        index = index_list.pop(0)
        res = rs.get(index, verify=False)
        # 如網頁忙線中,則先將網頁加入 index_list 並休息1秒後再連接
        if res.status_code != 200:
            index_list.append(index)
            # print u'error_URL:',index
            # time.sleep(1)
        else:
            article_gossiping = crawl_page_gossiping(res)
            # print u'OK_URL:', index
            # time.sleep(0.05)
    content = ''
    for index, article in enumerate(article_gossiping, 0):
        if index == 15:
            return content
        data = '{}\n{}\n\n'.format(article.get(
            'title', None), article.get('url_link', None))
        content += data
    return content


def ptt_beauty():
    rs = requests.session()
    res = rs.get('https://www.ptt.cc/bbs/Beauty/index.html', verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    all_page_url = soup.select('.btn.wide')[1]['href']
    start_page = get_page_number(all_page_url)
    page_term = 2  # crawler count
    push_rate = 10  # 推文
    index_list = []
    article_list = []
    for page in range(start_page, start_page - page_term, -1):
        page_url = 'https://www.ptt.cc/bbs/Beauty/index{}.html'.format(page)
        index_list.append(page_url)

    # 抓取 文章標題 網址 推文數
    while index_list:
        index = index_list.pop(0)
        res = rs.get(index, verify=False)
        # 如網頁忙線中,則先將網頁加入 index_list 並休息1秒後再連接
        if res.status_code != 200:
            index_list.append(index)
            # print u'error_URL:',index
            # time.sleep(1)
        else:
            article_list = craw_page(res, push_rate)
            # print u'OK_URL:', index
            # time.sleep(0.05)
    content = ''
    for article in article_list:
        data = '[{} push] {}\n{}\n\n'.format(article.get('rate', None), article.get('title', None),
                                             article.get('url', None))
        content += data
    return content


def ptt_hot():
    target_url = 'http://disp.cc/b/PttHot'
    print('Start parsing pttHot....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for data in soup.select('#list div.row2 div span.listTitle'):
        title = data.text
        link = "http://disp.cc/b/" + data.find('a')['href']
        if data.find('a')['href'] == "796-59l9":
            break
        content += '{}\n{}\n\n'.format(title, link)
    return content


def movie():
    target_url = 'http://www.atmovies.com.tw/movie/next/0/'
    print('Start parsing movie ...')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for index, data in enumerate(soup.select('ul.filmNextListAll a')):
        if index == 20:
            return content
        title = data.text.replace('\t', '').replace('\r', '')
        link = "http://www.atmovies.com.tw" + data['href']
        content += '{}\n{}\n'.format(title, link)
    return content


def technews():
    target_url = 'https://technews.tw/'
    print('Start parsing movie ...')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""

    for index, data in enumerate(soup.select('article div h1.entry-title a')):
        if index == 12:
            return content
        title = data.text
        link = data['href']
        content += '{}\n{}\n\n'.format(title, link)
    return content


def panx():
    target_url = 'https://panx.asia/'
    print('Start parsing ptt hot....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for data in soup.select('div.container div.row div.desc_wrap h2 a'):
        title = data.text
        link = data['href']
        content += '{}\n{}\n\n'.format(title, link)
    return content


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)

    if event.message.text == "eyny":
        content = eyny_movie()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "蘋果即時新聞":
        content = apple_news()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "PTT 表特版 近期大於 10 推的文章":
        content = ptt_beauty()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "近期熱門廢文":
        content = ptt_hot()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "即時廢文":
        content = ptt_gossiping()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "近期上映電影":
        content = movie()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "觸電網-youtube":
        target_url = 'https://www.youtube.com/user/truemovie1/videos'
        rs = requests.session()
        res = rs.get(target_url, verify=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        seqs = ['https://www.youtube.com{}'.format(data.find('a')['href'])
                for data in soup.select('.yt-lockup-title')]
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(text=seqs[random.randint(0, len(seqs) - 1)]),
                TextSendMessage(text=seqs[random.randint(0, len(seqs) - 1)])
            ])
        return 0
    if event.message.text == "科技新報":
        content = technews()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "PanX泛科技":
        content = panx()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "目錄":
        buttons_template = TemplateSendMessage(
            alt_text='目錄 template',
            template=ButtonsTemplate(
                title='選擇服務',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/xQF5dZT.jpg',
                actions=[
                    MessageTemplateAction(
                        label='新聞',
                        text='新聞'
                    ),
                    MessageTemplateAction(
                        label='電影',
                        text='電影'
                    ),
                    MessageTemplateAction(
                        label='看廢文',
                        text='看廢文'
                    ),
                    # MessageTemplateAction(
                    #     label='正妹',
                    #     text='正妹'
                    # ),
                    MessageTemplateAction(
                        label='記帳內容',
                        text='記帳內容'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "新聞":
        buttons_template = TemplateSendMessage(
            alt_text='新聞 template',
            template=ButtonsTemplate(
                title='新聞類型',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/vkqbLnz.png',
                actions=[
                    MessageTemplateAction(
                        label='蘋果即時新聞',
                        text='蘋果即時新聞'
                    ),
                    MessageTemplateAction(
                        label='科技新報',
                        text='科技新報'
                    ),
                    MessageTemplateAction(
                        label='PanX泛科技',
                        text='PanX泛科技'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "電影":
        buttons_template = TemplateSendMessage(
            alt_text='電影 template',
            template=ButtonsTemplate(
                title='服務類型',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/sbOTJt4.png',
                actions=[
                    MessageTemplateAction(
                        label='近期上映電影',
                        text='近期上映電影'
                    ),
                    MessageTemplateAction(
                        label='eyny',
                        text='eyny'
                    ),
                    MessageTemplateAction(
                        label='觸電網-youtube',
                        text='觸電網-youtube'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "看廢文":
        buttons_template = TemplateSendMessage(
            alt_text='看廢文 template',
            template=ButtonsTemplate(
                title='你媽知道你在看廢文嗎',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/ocmxAdS.jpg',
                actions=[
                    MessageTemplateAction(
                        label='近期熱門廢文',
                        text='近期熱門廢文'
                    ),
                    MessageTemplateAction(
                        label='即時廢文',
                        text='即時廢文'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "正妹":
        buttons_template = TemplateSendMessage(
            alt_text='正妹 template',
            template=ButtonsTemplate(
                title='選擇服務',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/qKkE2bj.jpg',
                actions=[
                    MessageTemplateAction(
                        label='PTT 表特版 近期大於 10 推的文章',
                        text='PTT 表特版 近期大於 10 推的文章'
                    ),
                    URITemplateAction(
                        label='正妹牆',
                        uri='https://ptt-beauty-infinite-scroll.herokuapp.com/'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "記帳內容":
        buttons_template = TemplateSendMessage(
            alt_text='記帳 template',
            template=ButtonsTemplate(
                title='記帳內容',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/YSJayCb.png',
                actions=[
                    MessageTemplateAction(
                        label='成員花錢統計',
                        text='成員花錢統計'
                    ),
                    MessageTemplateAction(
                        label='重新統計',
                        text='重新統計'
                    ),
                    MessageTemplateAction(
                        label='刪除全部紀錄',
                        text='刪除全部紀錄'
                    ),
                    # URITemplateAction(
                    #     label='花錢詳細',
                    #     uri='https://intense-sierra-14037.herokuapp.com/index'
                    # )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0

    #######記帳功能########

    if event.message.text == "肥豬滾":
        if event.source.type == "room":
            print("event.source.roomid", event.source)
            room_id = event.source.room_id
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="掰掰"))
            line_bot_api.leave_room(room_id)
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="才不要"))

    if event.message.text.find('記帳') != -1:
        ary = event.message.text.split()
        if len(ary) == 3:

            # 聊天室
            if isinstance(event.source, SourceRoom):
                room_id = event.source.room_id
                user_id = event.source.user_id
                profile = line_bot_api.get_room_member_profile(
                    room_id, user_id)

                title = profile.display_name
                money = int(ary[1])
                content = ary[2]

                if (linePost(title, money, content, user_id, room_id)):
                    sum = getRoomMoney(user_id, room_id)
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text="記帳成功\n你已花了 {} 元".format(sum)))
                    return 0
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text="老娘罷工拉！！！！"))
                    return 0
            # 單人
            elif isinstance(event.source, SourceUser):
                profile = line_bot_api.get_profile(event.source.user_id)
                title = profile.display_name
                money = int(ary[1])
                content = ary[2]
                if (linePost(title, money, content, profile.user_id, "")):
                    sum = getMoney(profile.user_id)
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text="記帳成功\n你已花了 {} 元".format(sum)))
                    return 0
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text="老娘罷工拉！！！！"))
                    return 0
    if event.message.text == '成員花錢統計':
        s = ""
        userAry = []

        # 聊天室
        if isinstance(event.source, SourceRoom):
            room_id = event.source.room_id
            user_id = event.source.user_id
            profile = line_bot_api.get_room_member_profile(room_id, user_id)
            title = profile.display_name

            postlist = post.query.filter_by(roomid=room_id).all()

            if len(postlist) <= 0:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="沒有任何記錄"))
                return

            for i in postlist:
                try:
                    userAry.index(i.title)
                except:
                    userAry.append(i.title)

            sumAry = [0]*len(userAry)
            for i in postlist:
                index = userAry.index(i.title)
                sumAry[index] += i.money
            for i in range(len(userAry)):
                s += "{} 花了 {} 元\n".format(userAry[i], sumAry[i])

            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=s[:-1]))
            return 0
        # 單人
        elif isinstance(event.source, SourceUser):
            user_id = event.source.user_id
            profile = line_bot_api.get_profile(user_id)
            title = profile.display_name
            postlist = post.query.filter_by(userid=user_id, roomid="").all()

            if len(postlist) <= 0:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="沒有任何記錄"))
                return

            sum = 0
            for i in postlist:
                sum += i.money
            s += "你花了 {} 元".format(sum)

            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=s))
            return 0
    if event.message.text == '重新統計':
        confirm_template = TemplateSendMessage(
            alt_text='確認 template',
            template=ConfirmTemplate(
                title='選擇服務',
                text='確定要重新統計嗎？',
                thumbnail_image_url='https://i.imgur.com/cliDn19.jpg',
                actions=[
                    MessageTemplateAction(
                        label='確定',
                        text='快點刪掉紀錄拉'
                    ),
                    MessageTemplateAction(
                        label='取消',
                        text='我不要了'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, confirm_template)
        return 0

    if event.message.text == '刪除全部紀錄':
        confirm_template = TemplateSendMessage(
            alt_text='確認 template',
            template=ConfirmTemplate(
                title='選擇服務',
                text='確定要全部刪除嗎？',
                thumbnail_image_url='https://i.imgur.com/cliDn19.jpg',
                actions=[
                    MessageTemplateAction(
                        label='確定',
                        text='把我的紀錄全部刪光光吧'
                    ),
                    MessageTemplateAction(
                        label='取消',
                        text='我不要了'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, confirm_template)
        return 0

    if event.message.text == "把我的紀錄全部刪光光吧":
        user_id = event.source.user_id
        profile = line_bot_api.get_profile(user_id)
        title = profile.display_name
        postlist = post.query.filter_by(userid=user_id).delete()
        db.session.commit()
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="{} 的紀錄全刪光光了".format(title)))
        return 0
    if event.message.text == "快點刪掉紀錄拉":
        if isinstance(event.source, SourceRoom):
            room_id = event.source.room_id
            user_id = event.source.user_id
            profile = line_bot_api.get_room_member_profile(room_id, user_id)
            title = profile.display_name
            postlist = post.query.filter_by(
                userid=user_id, roomid=event.source.room_id).delete()
            db.session.commit()
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="{} 刪除此聊天室的紀錄了".format(title)))
            return 0
        elif isinstance(event.source, SourceUser):
            user_id = event.source.user_id
            profile = line_bot_api.get_profile(user_id)
            title = profile.display_name
            postlist = post.query.filter_by(userid=user_id, roomid="").delete()
            db.session.commit()
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="全刪光光了"))
            return 0
    if event.message.text == "附近餐廳":
        data = getNear()
        colAry = []
        if len(data) > 10:
            colAry = []
            for i in range(10):
                c = CarouselColumn(
                    title = data[i]['name'],
                    text = data[i]['addr'],
                    thumbnail_image_url=data[i]['phtoUrl'],
                    actions=[
                        MessageTemplateAction(
                            label = data[i]['phone'],
                            text = data[i]['phone']
                        ),
                        URITemplateAction(
                            label='網頁',
                            uri=data[i]['web']
                        ),
                        URITemplateAction(
                            label='地圖',
                            uri=data[i]['url']
                        )
                    ]
                )
                colAry.append(c)
            print(colAry)
            Carousel_template = TemplateSendMessage(
                alt_text='Carousel template',
                template=CarouselTemplate(
                    columns=colAry
                )
            )

            line_bot_api.reply_message(event.reply_token, Carousel_template)
            return 0

        for i in data:
            c = CarouselColumn(
                title = i['name'],
                text = i['addr'],
                thumbnail_image_url='https://i.imgur.com/cliDn19.jpg',
                actions=[
                    MessageTemplateAction(
                        label = i['phone'],
                        text = i['phone']
                    ),
                    URITemplateAction(
                        label='網頁',
                        uri=i['web']
                    ),
                    URITemplateAction(
                        label='地圖',
                        uri=i['url']
                    )
                ]
            )
            colAry.append(c)
        print(colAry)
        

        Carousel_template = TemplateSendMessage(
            alt_text='Carousel template',
            template=CarouselTemplate(
                columns=colAry
            )
        )
        
        line_bot_api.reply_message(event.reply_token, Carousel_template)
        return 0

class post(db.Model):
    # __table__name = 'user_table'，若不寫則看 class name
    # 設定 primary_key
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    content = db.Column(db.String)
    money = db.Column(db.Integer)
    date = db.Column(db.Date)
    roomid = db.Column(db.String)
    userid = db.Column(db.String)

    def __init__(self, title, content, money, roomid, userid):
        self.title = title
        self.content = content
        self.money = money
        self.date = str(datetime.now())
        self.roomid = roomid
        self.userid = userid

    def __repr__(self):
        return "Title:{} Content:{} Money:{} Data:{}".format(self.title, self.content, self.money, self.date)
        # return '<Todo %r>' % self.content


def linePost(title, money, content, userid, roomid):
    p = post(title=title, content=content,
             money=money, userid=userid, roomid=roomid)
    db.session.add(p)
    db.session.commit()
    return True


# @app.route("/post", methods=['POST'])
# def postMethod():
#     data = request.form
#     print(data)
#     p = post(title=data['title'], content=data['content'], money=data['money'])
#     db.session.add(p)
#     db.session.commit()
#     return json.dumps({"status": 200, "comment": "Add Success"})


# @app.route("/postByJson", methods=['POST'])
# def postByJson():
#     data = request.get_json()
#     p = post(title=data['title'], content=data['content'],
#              money=int(data['money']))
#     db.session.add(p)
#     db.session.commit()
#     return json.dumps({"status": 200, "comment": "Add Success"})


@app.route("/index")
def index():
    mypost = post.query.all()
    return render_template('index.html', mypost=mypost)


@app.route("/self")
def getself(title):
    mypost = post.query.filter_by(title=title)
    return render_template('index.html', mypost=mypost)


@app.route("/postdata")
def postview():
    return render_template('post.html')


@app.route("/noWeb")
def noWeb():
    return render_template('noWeb.html')

def getMoney(userid):
    data = post.query.filter_by(userid=userid, roomid="")
    print(data)
    sum = 0
    for i in data:
        sum += i.money
    print("Sum", sum)
    return sum


def getRoomMoney(userid, roomid):
    data = post.query.filter_by(userid=userid, roomid=roomid)
    print(data)
    sum = 0
    for i in data:
        sum += i.money
    print("Sum", sum)
    return sum

def getloc():
    print("-----------------Start Get Location------------------")
    loc = gmaps.geolocate()['location']
    return loc


@app.route("/getPlace", methods=['GET'])
def getPlace():
    loc = getloc()
    gresult = gmaps.places(query="餐廳", location=(
        loc['lat'], loc['lng']), radius=1000, language="zh-TW")['results']
    placeAry = []
    baseUrl = "https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={}&key={}"
    for i in gresult:
        result = gmaps.place(i['place_id'])['result']
        refer = i['photos'][0]['photo_reference']
        url = baseUrl.format(refer, google_key)
        resturant = {
            'addr': i['formatted_address'],
            'phone': result['formatted_phone_number'],
            'id': result['id'],
            'name': result['name'],
            'place_id': result['place_id'],
            'rating': result['rating'],
            'url': result['url'],
            # 'web' : result['website'],
            'phtoUrl': url
        }
        placeAry.append(resturant)
    return jsonify(placeAry)


@app.route("/getNear", methods=['GET'])
def getNear():
    #loc = getloc()
    24.992573, 121.463511
    print("-----------------Start Get Resturant------------------")
    aa = gmaps.places_nearby(keyword="餐廳", location=(
        "24.992573", "121.463511"), language="zh-TW", radius=1000)['results']
    nearAry = []
    baseUrl = "https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={}&key={}"
    imgurl = ""
    for i in aa:
        result = gmaps.place(i['place_id'])['result']
        if 'photos' in i:
            refer = i['photos'][0]['photo_reference']
            imgurl = baseUrl.format(refer, google_key)
        addr = i['vicinity'] if 'vicinity' in i else ""
        phone = result['formatted_phone_number'] if 'formatted_phone_number' in result else "懶得寫電話"
        rating = result['rating'] if 'rating' in result else ""
        url = result['url'] if 'url' in result else "懶得輸網址"
        web = result['website'] if 'website' in result else "https://intense-sierra-14037.herokuapp.com/noWeb"
        phtoUrl = imgurl

        resturant = {
            'addr': addr,
            'phone': phone,
            'name': i['name'],
            'rating': rating,
            'url': result['url'],
            'web': web,
            'phtoUrl': imgurl
        }

        nearAry.append(resturant)

    print("-----------------End Get Resturant------------------")

    return nearAry


if __name__ == '__main__':
    app.debug = True
    app.run()
