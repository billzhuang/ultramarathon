#!/usr/bin/env python
# -*- coding: utf-8 -*- 

class TokenInfo(object):
	def __init__(self, exists=None, uid=None, access_token=None,
				expires_in=None, refresh_token=None, last_request_time=None):
		self.exists = exists
		self.uid = uid
		self.access_token = access_token
		self.expires_in = expires_in
		self.refresh_token = refresh_token
		self.last_request_time = last_request_time

class UserInfo(object):
	def __init__(self, exists=None, name=None, gender=None,
				birthday=None, isactive=0,
				 last_request_time=None, uid=None):
		self.exists = exists
		self.name = name
		self.gender = gender
		self.birthday = birthday
		self.isactive = isactive
		self.last_request_time = last_request_time
		self.uid = uid

class TeamMember(object):
	def __init__(self, team_id=None, friend_uid=None):
		self.team_id = team_id
		self.friend_uid = friend_uid

class TeamInfo(object):
	def __init__(self, name=None):
		self.name = name