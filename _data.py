#!/usr/bin/env python
# -*- coding: utf-8 -*- 
import _entity
import _keys
import MySQLdb

class DataLayer(object):
	def __init__(self):
		self.db = MySQLdb.connect(_keys.mysql_host, _keys.mysql_user, _keys.mysql_passwd,
                           _keys.mysql_db, port=int(_keys.mysql_port))
		self.db.set_character_set('utf8')
		self.db.autocommit(True)

	def reinitdb(self):
		self.db = MySQLdb.connect(_keys.mysql_host, _keys.mysql_user, _keys.mysql_passwd,
                           _keys.mysql_db, port=int(_keys.mysql_port))
		self.db.set_character_set('utf8')
		self.db.autocommit(True)

	def user_token(self, uid):
		c = self.db.cursor()
		c.execute('select uid,access_token,expires_in,refresh_token,updatedate from bong.token where uid=%s', uid)
		#self.db.commit()

		exists = c.rowcount != 0L
		row = c.fetchone()
		c.close()
		self.db.close()

		if row is None:
			return _entity.TokenInfo(exists=exists)

		return _entity.TokenInfo(exists,
						row[0],
						row[1],
						row[2],
						row[3],
						row[4])

	def update_token(self, token):
		c = self.db.cursor()
		c.execute('''update bong.token set access_token=%s
					, expires_in=%s
					, refresh_token=%s
					, updatedate=now() 
					where uid=%s'''
				, (token.access_token, token.expires_in, token.refresh_token, token.uid))
		#self.db.commit()

		c.close()
		self.db.close()

	def user_info(self, uid):
		c = self.db.cursor()
		c.execute('select name,gender,birthday,isactive,updatedate,uid from bong.member where uid=%s', uid)
		#self.db.commit()

		exists = c.rowcount != 0L
		row = c.fetchone()
		c.close()
		self.db.close()

		if row is None:
			return _entity.UserInfo(exists=exists)

		return _entity.UserInfo(exists,
						row[0],
						row[1],
						row[2],
						row[3],
						row[4],
						row[5])

	def create_user_info(self, user):
		c = self.db.cursor()
		try:
			c.execute('insert into bong.member(uid,name,gender,birthday,isactive) values(%s,%s,%s,%s,0)'
					, (user.uid, user.name, user.gender, user.birthday))
			#self.db.commit()
		except MySQLdb.Error, e:
		    try:
		        print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
		    except IndexError:
		        print "MySQL Error: %s" % str(e)
		c.close()
		self.db.close()

	def update_user_info(self, user):
		c = self.db.cursor()
		c.execute('''update bong.member set name=%s
					, gender=%s
					, birthday=%s
					, updatedate=now() 
					where uid=%s'''
				, (user.name, user.gender, user.birthday, user.uid))
		#self.db.commit()

		c.close()
		self.db.close()

	def enable_disable_user(self, user):
		c = self.db.cursor()
		c.execute('''update bong.member set isactive=%s
					, updatedate=now() 
					where uid=%s'''
				, (user.isactive, user.uid))
		#self.db.commit()

		c.close()
		self.db.close()

	def try_match_user(self, user):
		c = self.db.cursor()
		c.execute(
		'''
		select m.uid,m.name,m.gender,m.birthday from bong.member m
		where m.uid not in
		(
		select l.uid from bong.team_member_lnk as l
		where l.isactive = 1
		)
		and m.uid != %s
		and m.isactive =1''', user.uid)
		#self.db.commit()

		rows = c.fetchall()
		c.close()
		self.db.close()

		sg = []
		dg = []

		for row in rows:
			if row[2] == user.gender:
				sg.append(row[0])
			else:
				dg.append(row[0])

		for item in dg:
			if self.match_user(user.uid, item):
				return item

		for item in sg:
			if self.match_user(user.uid, item):
				return item

		return None

	def match_user(self, uid1, uid2):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
			'''
			insert into bong.team(name,status) values(%s,%s);
			''', ('', 'new'))
		#self.db.commit()
		c.close()
		self.db.close()

		lastid = c.lastrowid
		self.reinitdb()
		c1 = self.db.cursor()
		c1.execute(
			'''
			insert into bong.team_member_lnk(uid,status,team_id,isactive)
			values(%s,'accept',%s,1);
			insert into bong.team_member_lnk(uid,status,team_id,isactive)
			values(%s,'accept',%s,1);
			''', (uid1,lastid, uid2, lastid))
		#self.db.commit()
		c1.close()
		self.db.close()

		self.reinitdb()
		c2 = self.db.cursor()
		c2.execute(
			'''
			select uid from bong.team_member_lnk 
			where uid in (%s,%s) and isactive=1;
			''', (uid1, uid2))
		#self.db.commit()
		c2.close()
		self.db.close()

		if c2.rowcount != 2L:
			self.reinitdb()
			c3 = self.db.cursor()
			c3.execute(
			'''
			delete from bong.team_member_lnk 
			where uid in (%s,%s) and team_id=%s;

			delete from bong.team
			where id=%s;
			''', (uid1, uid2, lastid, lastid))
			#self.db.commit()
			c3.close()
			self.db.close()

			return False
		else:
			return True

	def partner_info(self, uid):
		c = self.db.cursor()
		c.execute(
		'''
		select tml2.team_id, tml2.uid from bong.team_member_lnk tml2
		where tml2.team_id in (
		select tml.team_id from bong.team_member_lnk tml
		where tml.uid= %s and tml.isactive=1)
		and tml2.uid != %s;
		''', (uid, uid))
		#self.db.commit()

		row = c.fetchone()
		c.close()
		self.db.close()

		if row is None:
			return None

		return _entity.TeamMember(row[0], row[1])