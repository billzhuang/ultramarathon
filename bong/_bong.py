#!/usr/bin/env python
# -*- coding: utf-8 -*- 
import json
import urllib
import requests
import types
from decimal import Decimal


class BongAPIError(Exception):
    """Raised if the Bong API returns an error."""
    pass

class BongAPINotModifed(Exception):
    """Raised if the document requested is unmodified. Need the use of etag header"""
    pass

class BongToken(object):
    def __init__(self, uid=None, access_token=None, expires_in=None, 
                refresh_token=None, refresh_token_expiration=None):
        self.uid = uid
        self.access_token = access_token
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        self.refresh_token_expiration = refresh_token_expiration

class BongUser(object):
    def __init__(self, name=None, gender=None, birthday=None, uid=None):
        self.name = name
        self.gender = gender
        self.birthday = birthday
        self.uid = uid

class BongClient(object):
    """OAuth client for the Bong API"""
    api_url = "https://open.bong.cn"
    web_auth_uri = api_url + "/oauth/authorize"
    token_url = api_url + "/oauth/token"
    refresh_url = token_url
    
    
    
    def __init__(self, client_id=None, client_secret=None,
                 access_token=None, use_app=False):

        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.auth_url = self.app_auth_url if use_app else self.web_auth_uri
        self.use_app = use_app
        self._last_headers = None

    def parse_response(self, response):
        """Parse JSON API responses."""

        return json.loads(response.text)

    def build_oauth_url(self, redirect_uri=None, scope=""):
        params = {
            'client_id': self.client_id,
            'scope': scope
        }

        if not self.use_app:
            params['response_type'] = 'code'

        if redirect_uri:
            params['redirect_uri'] = redirect_uri

        # hates +s for spaces, so use %20 instead.
        encoded = urllib.urlencode(params).replace('+', '%20')
        return "%s?%s" % (self.auth_url, encoded)

    def get_oauth_token(self, code, **kwargs):

        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': kwargs.get('grant_type', 'authorization_code')
        }

        if 'redirect_uri' in kwargs:
            params['redirect_uri'] = kwargs['redirect_uri']
        response = requests.post(self.token_url, params=params)
        response = response.json()
        try:
            #return 'heelo'
            return BongToken(response['uid'],
                            response['access_token'],
                            response['expires_in'],
                            response['refresh_token'],
                            response['refresh_token_expiration'])
        except:
            error = "<%(error)s>: %(error_description)s" % response
            raise BongAPIError(error)

    def refresh_token(self, refresh_token, **kwargs):

        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': kwargs.get('grant_type', 'refresh_token'),
            'refresh_token': refresh_token
        }

        response = requests.post(self.refresh_url, params=params)
        response = json.loads(response.content)
        try:
            return BongToken(response['uid'],
                            response['access_token'],
                            response['expires_in'],
                            response['refresh_token'],
                            response['refresh_token_expiration'])
        except:
            error = "<%(error)s>: %(error_description)s" % response
            raise BongAPIError(error)

    def tokeninfo(self):
        
        params = {
            'access_token': self.access_token
        }

        response = requests.get(self.tokeninfo_url, params=params)
        response = json.loads(response.content)
        try:
            return response
        except:
            error = "<%(error)s>: %(error_description)s" % response
            raise BongAPIError(error)


    def api(self, path, method='GET', **kwargs):

        params = kwargs['params'] if 'params' in kwargs else {}
        data = kwargs['data'] if 'data' in kwargs else {}

        if not self.access_token and 'access_token' not in params:
            raise BongAPIError("You must provide a valid access token.")

        url = "%s/%s" % (self.api_url, path)
        if 'access_token' not in params:
            params['access_token'] = self.access_token

        resp = requests.request(method, url,
                                data=data,
                                params=params)
        if str(resp.status_code)[0] not in ('2', '3'):
            raise BongAPIError("Error returned via the API with status code (%s):" %
                                resp.status_code, resp.text)
        if resp.status_code == 304:
            raise BongAPINotModifed("Unmodified")
        
        self._last_headers = resp.headers
        return resp

    def get(self, path, **params):
        return self.parse_response(
            self.api(path, 'GET', params=params))

    def post(self, path, **data):
        return self.parse_response(
            self.api(path, 'POST', data=data))

    def set_first_date(self):
        if not self.first_date:
            response = self.user_profile()
            self.first_date = response['profile']['firstDate']

    def bongday_running(self, duedate, **params):
        detail = self.get('1/bongday/blocks/%s' % duedate, **params)
        running_sum = Decimal('0.0')

        for activity in detail['value']:
                    if activity['type'] == 2 and \
                        activity['subType'] == 4:
                        running_sum += Decimal(activity['distance'])

        return running_sum.quantize(Decimal('0.00'))
        

    def bongday_running_list(self, duedate, num, **params):
        detail = self.get('1/bongday/blocks/%s/%s' % (duedate, num), **params)

        list = []
        for day in detail['value']:
            running_sum = Decimal('0.0')
            for activity in day['blockList']:
                if activity['type'] == 2 and activity['subType'] == 4:
                    running_sum += Decimal(activity['distance'])
            list.append(running_sum.quantize(Decimal('0.00')))

        return list

    def user_info(self, **params):
        if 'access_token' not in params or 'uid' not in params:
            raise BongAPIError('failed to get user info, cuz lack of token and uid')

        profile = self.get('1/userInfo/%s' % params['uid'], access_token=params['access_token'])

        return BongUser(profile['value']['name'],
                        profile['value']['gender'],
                        profile['value']['birthday'],
                        params['uid'])

    def user_avator(self, **params):
        if 'access_token' not in params or 'uid' not in params:
            raise BongAPIError('failed to get user avator, cuz lack of token and uid')

        img = self.get('1/userInfo/avatar/%s' % params['uid'], access_token=params['access_token'])

        return img['value']

    def __getattr__(self, name):
        '''\
Turns method calls such as "bong.foo_bar(...)" into
a call to "bong.api('/foo/bar', 'GET', params={...})"
and then parses the response.
'''
        base_path = name.replace('_', '/')

        # Define a function that does what we want.
        def closure(*path, **params):
            'Accesses the /%s API endpoints.'
            path = list(path)
            path.insert(0, base_path)
            return self.parse_response(
                self.api('/'.join(path), 'GET', params=params)
                )

        # Clone a new method with the correct name and doc string.
        retval = types.FunctionType(
            closure.func_code,
            closure.func_globals,
            name,
            closure.func_defaults,
            closure.func_closure)
        retval.func_doc =  closure.func_doc % base_path

        # Cache it to avoid additional calls to __getattr__.
        setattr(self, name, retval)
        return retval

