#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from flask import Flask, url_for, request, session, redirect, g, render_template
from werkzeug.contrib.fixers import ProxyFix
from bong import BongClient, BongAPIError
from datetime import datetime, timedelta
from decimal import Decimal
import _keys
import _data
import _entity
#import pygal
#from pygal.style import LightColorizedStyle
import sae

app = Flask(__name__)
#app.wsgi_app = ProxyFix(app.wsgi_app)
app.debug = True

bong = BongClient(_keys.client_id, _keys.client_secret)

@app.route("/")
def index():
    try:
        '''first enter in app'''
        if 'uid' not in session:
            uid = request.args.get('uid', '')
            if uid == '' :
                oauth_return_url = url_for('oauth_return', _external=True)
                auth_url = bong.build_oauth_url(oauth_return_url)
                return redirect(auth_url)

            '''check if already cache the token'''
            token = _data.DataLayer().user_token(uid)

            '''new user first install'''
            if token is None:
                oauth_return_url = url_for('oauth_return', _external=True)
                auth_url = bong.build_oauth_url(oauth_return_url)
                return redirect(auth_url)

            '''check token valid or not, if then refresh Token'''
            token = _tryRefreshToken(token)
            session['token'] = token.access_token
            session['uid'] = token.uid

        '''check token again'''
        token = _data.DataLayer().user_token(session['uid'])
        '''why???'''
        if token is None:
            oauth_return_url = url_for('oauth_return', _external=True)
            auth_url = bong.build_oauth_url(oauth_return_url)
            return redirect(auth_url)

        token = _tryRefreshToken(token)
        session['token'] = token.access_token
        session['uid'] = token.uid
        '''get user information'''
        user = _data.DataLayer().user_info(session['uid'])
        if user is None:
            user = bong.user_info(uid=session['uid'], access_token=token.access_token)
            _data.DataLayer().create_user_info(user)
            user = _data.DataLayer().user_info(session['uid'])

        '''check user info expired need refresh'''
        if (datetime.now() - user.last_request_time) >= timedelta(seconds = 180):
            user2 = bong.user_info(uid=session['uid'], access_token=token.access_token)
            _data.DataLayer().update_user_info(user2)
            user = _data.DataLayer().user_info(session['uid'])
        #print('lol:%s', user.isactive)
        if user.isactive == 0L:
            return redirect(url_for('start'))        

        return redirect(url_for('feed'))
    except BongAPIError:
        oauth_return_url = url_for('oauth_return', _external=True)
        auth_url = bong.build_oauth_url(oauth_return_url)
        return redirect(auth_url)

def _tryRefreshToken(oldtoken, forcerefresh=False):
    #print('hello%s' % oldtoken is None)
    if oldtoken is not None:
        expiredate = oldtoken.last_request_time + timedelta(seconds=oldtoken.expires_in)
        #print('expire:%s' % expiredate)
        if (forcerefresh or (expiredate - datetime.now()) <= timedelta(hours = 6)):
            token = bong.refresh_token(oldtoken.refresh_token)
            _data.DataLayer().update_token(token)
            return token
        return oldtoken

@app.route("/oauth_return")
def oauth_return():
    error = request.values.get('error', None)
    if error is not None:
        return error
    oauth_return_url = url_for('oauth_return', _external=True)
    code = request.args.get("code")
    token = bong.get_oauth_token(code, redirect_uri=oauth_return_url)
    '''check if already cache the token'''
    oldtoken = _data.DataLayer().user_token(token.uid)

    '''new user first install'''
    if oldtoken is None:
        _data.DataLayer().create_token(token)
    else:
        _data.DataLayer().update_token(token)

    session['token'] = token.access_token
    session['uid'] = token.uid
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(exception):
    app.logger.exception(exception)
    return render_template('500.html'), 500

@app.route('/logout')
def logout():
    if 'token' in session:
        del(session['token'])
        del(session['uid'])
    return redirect(url_for('index'))

@app.route('/start')
def start():
    user = _data.DataLayer().user_info(session['uid'])
    user.name = unicode(user.name, 'utf-8')
    return render_template('_start.html', user=user)

@app.route('/matchpartner')
def matchpartner():
    user = _data.DataLayer().user_info(session['uid'])
    if user.isactive == 0L:
        user.isactive = 1L
        _data.DataLayer().enable_disable_user(user)

    uid = _data.DataLayer().try_match_user(user)

    if uid is None:
        return render_template('_nomatch.html')

    return redirect(url_for('feed'))

@app.route('/deactive')
def deactive():
    '''clear my partner'''
    partnerinfo = _data.DataLayer().partner_info(session['uid'])
    if partnerinfo is not None:
        _data.DataLayer().reject(partnerinfo.team_id, session['uid'])

    user = _data.DataLayer().user_info(session['uid'])
    user.isactive = 0L
    _data.DataLayer().enable_disable_user(user)

    return u"谢谢你的使用，想完成一次超级马拉松随时再来。"

@app.route("/finish")
def finish():
    partnerinfo = _data.DataLayer().partner_info(session['uid'])
    _data.DataLayer().finish(partnerinfo.team_id)
    return render_template('nextaction.html')

@app.route("/change")
def change():
    partnerinfo = _data.DataLayer().partner_info(session['uid'])
    if partnerinfo is not None:
        _data.DataLayer().reject(partnerinfo.team_id, session['uid'])

    return redirect(url_for('feed'))

@app.route('/add_msg', methods=['GET','POST'])
def add_msg():
    if not session.get('uid'):
        abort(401)

    _data.DataLayer().create_msg(request.form['team_id'], request.form['uid'], request.form['content'])

    return redirect(url_for('feed'))



@app.route('/close_question', methods=['POST'])
def close_question():
    if not session.get('uid'):
        abort(401)

    _data.DataLayer().close_question(request.form['q_id'])

    return redirect(url_for('load_question'))

@app.route("/dayrun/<page>")
def show_dayrun(page=0):
    todo = _data.DataLayer().batch_uids(int(page))
    response = ''
    for uid in todo:
        try:
            response += uid
            token = _data.DataLayer().user_token(uid)
            token = _tryRefreshToken(token)
            fivedayago = (datetime.now() - timedelta(days=2)).strftime('%Y%m%d')
            fivedayagodate = datetime.strptime(fivedayago, '%Y%m%d')
            daylist = [(fivedayagodate + timedelta(days=x)).strftime('%Y%m%d') for x in range(3)]
            running_data = bong.bongday_running_list(fivedayago, 3, uid=token.uid, access_token=token.access_token)
            _data.DataLayer().save_activity(uid, 3, daylist, running_data)
            response += u' run: %s 米</br>' % running_data
        except BongAPIError:
            try:
                token = _tryRefreshToken(token, True)
            except:
                response += '%s refresh_token error' % uid

            response += '%s cannot refresh data' % uid
    return response

@app.route("/list_message")
def list_message():
    _data.DataLayer().create_visit('dm', session['uid'])
    msgList = _data.DataLayer().new_reply(session['uid'])
    for item in msgList:
        item.sender = unicode(item.sender, 'utf-8')

    return render_template('_message.html', entries=msgList)

@app.route('/feed')
def feed():
    if 'uid' not in session:
        oauth_return_url = url_for('oauth_return', _external=True)
        auth_url = bong.build_oauth_url(oauth_return_url)
        return redirect(auth_url)

    _data.DataLayer().create_visit('feed', session['uid'])
    partnerinfo = _data.DataLayer().partner_info(session['uid'])
    if partnerinfo is None:
        return redirect(url_for('matchpartner'))

    teamsummary = _data.DataLayer().team_summary(partnerinfo.team_id)
    showsummary = False
    canfinish = False
    if not teamsummary is None:
        showsummary = True
        canfinish = (100000 <= teamsummary.sumdistance)
        if teamsummary.avgdistance != Decimal('0.00'):
            teamsummary.leftday = int((100000 - teamsummary.sumdistance) / teamsummary.avgdistance)
        else:
            teamsummary.leftday = 100
    try:
        otherInfo = _data.DataLayer().user_info(partnerinfo.friend_uid)
        otherInfo.name = unicode(otherInfo.name, 'utf-8')
        otherToken = _data.DataLayer().user_token(otherInfo.uid)
        otherToken = _tryRefreshToken(otherToken)
        img = bong.user_avatar(uid=otherInfo.uid, access_token=otherToken.access_token)
        if img == '' or img is None:
            img = _keys.default_avatar
        otherInfo.avatar = img
    except BongAPIError:
        otherInfo.avatar = _keys.default_avatar
        '''no avatar'''
    myinfo = _data.DataLayer().user_info(session['uid'])
    myinfo.name = unicode(myinfo.name, 'utf-8')

    team = _entity.TeamInfo(u'%s和%s的超级马拉松' % (otherInfo.name, myinfo.name))

    fans = _data.DataLayer().my_fans(session['uid'])
    for item in fans:
        item.name = unicode(item.name, 'utf-8')

    return render_template('_feed.html'
        , team=team,canfinish=canfinish
        , showsummary=showsummary
        , teamsummary=teamsummary
        , entry=otherInfo
        , team_id=partnerinfo.team_id
        , fans = fans
        , uid = session['uid'])

@app.route("/profile/<uid>")
def profile(uid=None):
    if uid is not None:
        _data.DataLayer().create_visit('profile', session['uid'])
        userInfo = _data.DataLayer().user_info(uid)
        userInfo.name = unicode(userInfo.name, 'utf-8')
        token = _data.DataLayer().user_token(uid)
        try:
            img = bong.user_avatar(uid=uid, access_token=token.access_token)
            if img == '' or img is None:
                img = _keys.default_avatar
            userInfo.avatar = img
        except BongAPIError:
            userInfo.avatar = _keys.default_avatar
            '''no avatar'''

        return render_template('_profile.html', userInfo=userInfo)

@app.route('/send_dm', methods=['GET','POST'])
def send_dm():
    if not session.get('uid'):
        abort(401)

    _data.DataLayer().create_question(session['uid'], request.form['touid'], request.form['content'])

    return redirect(url_for('feed'))

@app.route('/dream2')
def dream2():
    _data.DataLayer().create_visit('trydream2', session['uid'])
    lastdreamtime = _data.DataLayer().check_dream(session['uid'])
    canAccess = False

    if lastdreamtime is None:
        canAccess = True
    else:
        cTime = datetime.now().replace(minute=0, second=0, microsecond=0)
        lTime = datetime.strptime(lastdreamtime, '%Y-%m-%d %H:%M:%S').replace(minute=0, second=0, microsecond=0)

        if cTime - lTime >= timedelta(minutes=30):
            canAccess = True
            if 'times' not in session:
                session['times'] = 1
            else:
                session['times'] = int(session['times']) + 1

            if int(session['times'] >= 6):
                session['times'] = 0
                _data.DataLayer().create_visit('dream', session['uid'])
                return redirect(url_for('feed'))
        else:
            return render_template('_dreamfull.html')

    if canAccess:
        userInfo = _data.DataLayer().user_info(session['uid'])
        dream_uid = _data.DataLayer().load_dream(userInfo.uid, userInfo.gender)

        if dream_uid is None:
            return render_template('_dreamfull.html')
        try:
            otherInfo = _data.DataLayer().user_info(dream_uid)
            otherInfo.name = unicode(otherInfo.name, 'utf-8')
            otherToken = _data.DataLayer().user_token(otherInfo.uid)
            otherToken = _tryRefreshToken(otherToken)
            img = bong.user_avatar(uid=otherInfo.uid, access_token=otherToken.access_token)
            if img == '' or img is None:
                img = _keys.default_avatar
            otherInfo.avatar = img
        except BongAPIError:
            otherInfo.avatar = _keys.default_avatar
            '''no avatar'''

    return render_template('_dream.html', otherInfo=otherInfo)

@app.route("/zan/<uid>/<en>")
def zan(uid=None, en=None):
    if uid is not None:
        _data.DataLayer().create_like(session['uid'], uid, en)
    return redirect(url_for('dream2'))

@app.route("/dm_detail/<q_id>")
def dm_detail(q_id=None):
    answerlist = _data.DataLayer().load_questionfeed(q_id)
    touid = ''
    for answer in answerlist:
        answer.name = u'我'
        if answer.fromuid != session['uid']:
            answer.name = 'TA'
            touid = answer.fromuid
        answer.content = unicode(answer.content, 'utf-8')
    if touid == '':
        # send to himself
        touid = answer.fromuid
    return render_template('_dmcontext.html'
                            , q_id = q_id
                            , touid = touid
                            , answerlist = answerlist)

@app.route('/reply', methods=['POST'])
def reply_dm():
    if not session.get('uid'):
        abort(401)

    _data.DataLayer().reply_question(request.form['q_id'], session['uid'], request.form['touid'], request.form['content'])

    return redirect(url_for('list_message'))

@app.route("/list_idols")
def list_idols():
    _data.DataLayer().create_visit('list_idols', session['uid'])
    idols = _data.DataLayer().my_idols(session['uid'])
    for item in idols:
        item.name = unicode(item.name, 'utf-8')

    return render_template('_idols.html', entries=idols)

'''@app.route("/report")
def report():
    _data.DataLayer().create_visit('report', session['uid'])
    base = datetime.today()
    date_list = [(base - timedelta(days=x)).strftime('%m%d') for x in range(0, 7)]
    date_list = date_list[::-1]

    #line_chart = pygal.Line()
    line_chart = pygal.Bar(style=LightColorizedStyle)
    line_chart.title = u'两个人的跑步数据'
    line_chart.x_labels = date_list
    
    dataDicta = _data.DataLayer().my_data(session['uid'])
    lista = []
    for date in date_list:
        if dataDicta.has_key(date):
            lista.append(dataDicta[date])
        else:
            lista.append(0)
    line_chart.add(u'我', lista)
    
    partnerinfo = _data.DataLayer().partner_info(session['uid'])
    if partnerinfo is not None:
        dataDictb = _data.DataLayer().my_data(partnerinfo.friend_uid)
        listb = []
        for date in date_list:
            if dataDictb.has_key(date):
                listb.append(dataDictb[date])
            else:
                listb.append(0)
        line_chart.add('TA', listb)
    
    svgdata = unicode(line_chart.render(), 'utf-8')

    return render_template('_report.html', svgdata=svgdata)'''

app.secret_key = _keys.secret_key

'''
if app.debug is not True:   
    import logging
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler('/var/log/ultramarathon/appexception.log', maxBytes=1024 * 1024 * 100, backupCount=20)
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s - %(funcName)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

if __name__ == "__main__":
    app.run(host='0.0.0.0')'''
