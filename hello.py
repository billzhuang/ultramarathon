#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from flask import Flask, url_for, request, session, redirect, g
from bong import BongClient
from datetime import datetime, timedelta
import _keys
import MySQLdb
import _data
import _entity

app = Flask(__name__)

bong = BongClient(_keys.client_id, _keys.client_secret)

@app.before_request
def before_request():
    g.db = MySQLdb.connect(_keys.mysql_host, _keys.mysql_user, _keys.mysql_passwd,
                           _keys.mysql_db, port=int(_keys.mysql_port))
    g.data = _data.DataLayer(g.db)

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'cur'): g.cur.close()
    if hasattr(g, 'db'): g.db.close()

@app.route("/")
def index():
    '''first enter in app'''
    if 'token' not in session:
        uid = request.args.get('uid', '')
        if uid == '' :
            return 'Please close and reenter in the app'

        '''check if already cache the token'''
        token = g.data.user_token(uid)

        '''new user first install'''
        if not token.exists:
            oauth_return_url = url_for('oauth_return', _external=True)
            auth_url = bong.build_oauth_url(oauth_return_url)
            return redirect(auth_url)

        '''//TODO:check token valid or not, if then refresh Token'''
        token = bong.refresh_token(token.refresh_token)
        g.data.update_token(token)
        session['token'] = token.access_token
        session['uid'] = token.uid

    '''get user information'''
    user = g.data.user_info(session['uid'])
    if not user.exists:
        user = bong.user_info(session['uid'])
        g.data.create_user_info(user)

    '''//TODO:check user info expired need refresh'''
    user2 = bong.user_info(session['uid'])
    g.data.update_user_info(user2)
    user = g.data.user_info(session['uid'])

    if user.isactive:
        return redirect(url_for('show_info'))        

    return redirect(url_for('show_info'))


@app.route("/oauth_return")
def oauth_return():
    error = request.values.get('error', None)
    if error is not None:
        return error
    oauth_return_url = url_for('oauth_return', _external=True)
    code = request.args.get("code")
    token = bong.get_oauth_token(code, redirect_uri=oauth_return_url)
    session['token'] = token.access_token
    session['uid'] = token.uid
    return redirect(url_for('show_info'))


@app.route('/logout')
def logout():
    if 'token' in session:
        del(session['token'])
        del(session['uid'])
    return redirect(url_for('index'))


@app.route("/info")
def show_info():
    profile = bong.get('/1/userInfo/%s' % session['uid'], access_token=session['token'])
    img = bong.get('/1/userInfo/avatar/%s' % session['uid'], access_token=session['token'])
    response = 'User ID: %s<br />First day using bong: %s' % \
        (profile['value']['name'], profile['value']['birthday'])
    response += '<img src="data:image/png;base64,%s" alt="%s" />' %\
        (img['value'], profile['value']['name'])
    return response + "<br /><a href=\"%s\">Info for today</a>" % url_for('show_dayrun') + \
        "<br /><a href=\"%s\">Logout</a>" % url_for('logout')

@app.route("/dayrun")
def show_dayrun():
    today = datetime.now().strftime('%Y%m%d')
    running_data = bong.bongday_running(today, uid=session['uid'], access_token=session['token'])
    response = u'Today run: %s 米' % running_data
    return response + "<br /><a href=\"%s\">Info for today</a>" % url_for('today') + \
        "<br /><a href=\"%s\">Logout</a>" % url_for('logout')



@app.route("/today")
def today():
    today = datetime.now().strftime('%Y%m%d')
    info = bong.user_summary_daily(today, access_token=session['token'])
    res = ''
    for activity in info[0]['summary']:
        if activity['activity'] == 'wlk':
            res += 'Walking: %d steps<br />' % activity['steps']
        elif activity['activity'] == 'run':
            res += 'Running: %d steps<br />' % activity['steps']
        elif activity['activity'] == 'cyc':
            res += 'Cycling: %dm' % activity['distance']
    return res


@app.route("/expanded-summary")
def expanded_summary():
    today = datetime.now().strftime('%Y%m%d')
    info = bong.user_summary_daily(today, access_token=session['token'])
    res = ''
    for activity in info[0]['summary']:
        res = activities_block(activity, res)
        if activity['activity'] == 'wlk':
            res += 'Walking: %d steps<br />' % activity['steps']
            res += 'Walking: %d calories<br />' % activity['calories']
            res += 'Walking: %d distance<br />' % activity['distance']
            res += 'Walking: %d duration<br /><br />' % activity['duration']
        elif activity['activity'] == 'run':
            res += 'Running: %d steps<br />' % activity['steps']
            res += 'Running: %d calories<br />' % activity['calories']
            res += 'Running: %d distance<br />' % activity['distance']
            res += 'Running: %d duration<br /><br />' % activity['duration']
        elif activity['activity'] == 'cyc':
            res += 'Cycling: %dm<br />' % activity['distance']
            res += 'Cycling: %d calories<br />' % activity['calories']
            res += 'Cycling: %d distance<br />' % activity['distance']
            res += 'Cycling: %d duration<br />' % activity['duration']
    return res


@app.route("/activities")
def activities():
    today = datetime.now().strftime('%Y%m%d')
    info = bong.user_activities_daily(today, access_token=session['token'])
    res = ''
    for segment in info[0]['segments']:
        if segment['type'] == 'move':
            res += 'Move<br />'
            res = segment_start_end(segment, res)
            for activity in segment['activities']:
                res += 'Activity %s<br />' % activity['activity']
                res = activity_start_end(activity, res)
                res += 'Duration: %d<br />' % activity['duration']
                res += 'Distance: %dm<br />' % activity['distance']
            res += '<br />'
        elif segment['type'] == 'place':
            res += 'Place<br />'
            res = segment_start_end(segment, res)
            for activity in segment['activities']:
                res += 'Activity %s<br />' % activity['activity']
                res = activity_start_end(activity, res)
                res += 'Duration: %d<br />' % activity['duration']
                res += 'Distance: %dm<br />' % activity['distance']
            res += '<br />'
    return res


@app.route("/places")
def places():
    today = datetime.now().strftime('%Y%m%d')
    info = bong.user_places_daily(today, access_token=session['token'])
    res = ''
    for segment in info[0]['segments']:
        res = place(segment, res)
    return res


@app.route("/storyline")
def storyline():
    today = datetime.now().strftime('%Y%m%d')
    info = bong.user_storyline_daily(today, trackPoints={'true'}, access_token=session['token'])
    res = ''
    for segment in info[0]['segments']:
        if segment['type'] == 'place':
            res = place(segment, res)
        elif segment['type'] == 'move':
            res = move(segment, res)
        res += '<hr>'
    return res


def segment_start_end(segment, res):
    res += 'Start Time: %s<br />' % segment['startTime']
    res += 'End Time: %s<br />' % segment['endTime']
    return res


def activity_start_end(activity, res):
    res += 'Start Time: %s<br />' % activity['startTime']
    res += 'End Time: %s<br />' % activity['endTime']
    return res


def place_block(segment, res):
    res += 'ID: %d<br />' % segment['place']['id']
    res += 'Name: %s<br />' % segment['place']['name']
    res += 'Type: %s<br />' % segment['place']['type']
    if segment['place']['type'] == 'foursquare':
        res += 'Foursquare ID: %s<br />' % segment['place']['foursquareId']
    res += 'Location<br />'
    res += 'Latitude: %f<br />' % segment['place']['location']['lat']
    res += 'Longitude: %f<br />' % segment['place']['location']['lon']
    return res


def trackPoint(track_point, res):
    res += 'Latitude: %f<br />' % track_point['lat']
    res += 'Longitude: %f<br />' % track_point['lon']
    res += 'Time: %s<br />' % track_point['time']
    return res


def activities_block(activity, res):
    res += 'Activity: %s<br />' % activity['activity']
    res = activity_start_end(activity, res)
    res += 'Duration: %d<br />' % activity['duration']
    res += 'Distance: %dm<br />' % activity['distance']
    if activity['activity'] == 'wlk' or activity['activity'] == 'run':
        res += 'Steps: %d<br />' % activity['steps']
    if activity['activity'] != 'trp':
        res += 'Calories: %d<br />' % activity['calories']
    if 'trackPoints' in activity:
        for track_point in activity['trackPoints']:
            res = trackPoint(track_point, res)
    return res


def place(segment, res):
    res += 'Place<br />'
    res = segment_start_end(segment, res)
    res = place_block(segment, res)
    if 'activities' in segment:
        for activity in segment['activities']:
            res = activities_block(activity, res)
    res += '<br />'
    return res


def move(segment, res):
    res += 'Move<br />'
    res = segment_start_end(segment, res)
    for activity in segment['activities']:
        res = activities_block(activity, res)
    res += '<br />'
    return res

app.secret_key = _keys.secret_key

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)