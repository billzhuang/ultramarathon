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

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

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

        return redirect(url_for('mystory'))
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
    token = _data.DataLayer().user_token(session['uid'])
    user.avatar = bong.user_avator(uid=token.uid, access_token=token.access_token)
    return render_template('start.html', user=user)

@app.route('/matchpartner')
def matchpartner():
    user = _data.DataLayer().user_info(session['uid'])
    if user.isactive == 0L:
        user.isactive = 1L
        _data.DataLayer().enable_disable_user(user)

    uid = _data.DataLayer().try_match_user(user)

    if uid is None:
        return render_template('nomatch.html')

    return redirect(url_for('mystory'))

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

@app.route('/mystory')
def mystory():
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
        otherInfo.avatar = bong.user_avator(uid=otherInfo.uid, access_token=otherToken.access_token)
    except BongAPIError:
        '''no avator'''
    myinfo = _data.DataLayer().user_info(session['uid'])
    myinfo.name = unicode(myinfo.name, 'utf-8')

    team = _entity.TeamInfo(u'%s和%s的超级马拉松' % (otherInfo.name, myinfo.name))

    msgs = _data.DataLayer().load_msg(partnerinfo.team_id)
    for msg in msgs:
        msg.name = unicode(msg.name, 'utf-8')
        msg.content = unicode(msg.content, 'utf-8')

    return render_template('mystory.html'
        , team=team,canfinish=canfinish
        , showsummary=showsummary
        , teamsummary=teamsummary
        , entries=(otherInfo,)
        , msgs = msgs
        , team_id=partnerinfo.team_id
        , uid = session['uid'])

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

    return redirect(url_for('mystory'))

@app.route("/info")
def show_info():
    token = _data.DataLayer().user_token(session['uid'])
    profile = bong.get('/1/userInfo/%s' % session['uid'], access_token=token.access_token)
    img = bong.user_avator(uid=session['uid'], access_token=token.access_token)
    response = 'User ID: %s<br />First day using bong: %s' % \
        (profile['value']['name'], profile['value']['birthday'])
    response += '<img src="data:image/png;base64,%s" alt="%s" />' %\
        (img, profile['value']['name'])
    return response

@app.route('/add_msg', methods=['GET','POST'])
def add_msg():
    if not session.get('uid'):
        abort(401)

    _data.DataLayer().create_msg(request.form['team_id'], request.form['uid'], request.form['content'])

    return redirect(url_for('mystory'))

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

app.secret_key = _keys.secret_key

if app.debug is not True:   
    import logging
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler('/var/log/ultramarathon/appexception.log', maxBytes=1024 * 1024 * 100, backupCount=20)
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s - %(funcName)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
