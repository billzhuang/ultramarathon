#!/usr/bin/env python
# -*- coding: utf-8 -*- 
import _entity

class DataLayer(object):
	def __init__(self, db):
		self.db = db

	def user_token(self, uid):
		c = self.db.cursor()
		c.execute('select * from token where uid=%s', uid)

		exists = c.cowcount != 0L
		row = c.fetchone()
		c.close()

		if row is None:
			return _entity.TokenInfo(exists=exists)

		return _entity.TokenInfo(exists,
						row['uid'],
						row['access_token'],
						row['expires_in'],
						row['refresh_token'],
						row['updatedate'])

	def update_token(self, token):
		c = self.db.cursor()
		c.execute('''update token set access_token=%s
					, expires_in=%s
					, refresh_token=%s
					, updatedate=now() 
					where uid=%s'''
				, (token.access_token, token.expires_in, token.refresh_token, token.uid))

		c.close()

	def user_info(self, uid):
		c = self.db.cursor()
		c.execute('select * from member where uid=%s', uid)

		exists = c.cowcount != 0L
		row = c.fetchone()
		c.close()

		if row is None:
			return _entity.UserInfo(exists=exists)

		return _entity.UserInfo(exists,
						row['name'],
						row['gender'],
						row['birthday'],
						row['avator'],
						row['isactive'])

	def create_user_info(self, user):
		c = self.db.cursor()
		c.execute('''insert member(uid,name,gender,birthday,avator,isactive)
					values(%s,%s,%s,%s,%s,0)'''
				, (user.uid, user.name, user,gender, user.birthday, user.avator))

		c.close()

	def update_user_info(self, user):
		c = self.db.cursor()
		c.execute('''update member set name=%s
					, gender=%s
					, birthday=%s
					, avator=%s
					, updatedate=now() 
					where uid=%s'''
				, (user.name, user,gender, user.birthday, user.avator, user.uid))

		c.close()