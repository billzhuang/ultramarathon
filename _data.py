#!/usr/bin/env python
# -*- coding: utf-8 -*- 
import _entity
import _keys
import MySQLdb
from decimal import Decimal

class DataLayer(object):
	def __init__(self):
		'''self.db = MySQLdb.connect(_keys.mysql_host, _keys.mysql_user, _keys.mysql_passwd,
                           _keys.mysql_db, port=int(_keys.mysql_port))
		self.db.set_character_set('utf8')
		self.db.autocommit(True)'''

	def reinitdb(self):
		self.db = MySQLdb.connect(_keys.mysql_host, _keys.mysql_user, _keys.mysql_passwd,
                           _keys.mysql_db, port=int(_keys.mysql_port))
		self.db.set_character_set('utf8')
		self.db.autocommit(True)

	def user_token(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute('select uid,access_token,expires_in,refresh_token,updatedate from bong.token where uid=%s', uid)
		#self.db.commit()
		row = c.fetchone()
		c.close()
		self.db.close()

		if row is None:
			return None

		return _entity.TokenInfo(
						row[0],
						row[1],
						row[2],
						row[3],
						row[4])

	def create_token(self, token):
		self.reinitdb()
		c = self.db.cursor()
		try:
			c.execute('''insert into bong.token
					(uid, access_token,expires_in,refresh_token) 
					values(%s,%s,%s,%s)'''
					, (token.uid, token.access_token, token.expires_in, token.refresh_token))
			#self.db.commit()
		except MySQLdb.Error, e:
		    try:
		        print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
		    except IndexError:
		        print "MySQL Error: %s" % str(e)
		c.close()
		self.db.close()

	def update_token(self, token):
		self.reinitdb()
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
		self.reinitdb()
		c = self.db.cursor()
		c.execute('select name,gender,birthday,isactive,updatedate,uid from bong.member where uid=%s', uid)
		#self.db.commit()
		row = c.fetchone()
		c.close()
		self.db.close()

		if row is None:
			return None

		return _entity.UserInfo(
						row[0],
						row[1],
						row[2],
						row[3],
						row[4],
						row[5])

	def create_user_info(self, user):
		self.reinitdb()
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
		self.reinitdb()
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
		self.reinitdb()
		c = self.db.cursor()
		c.execute('''update bong.member set isactive=%s
					, updatedate=now() 
					where uid=%s'''
				, (user.isactive, user.uid))
		#self.db.commit()

		c.close()
		self.db.close()

	def finish(self, team_id):
		self.reinitdb()
		c = self.db.cursor()
		c.execute('''
				update bong.team
				set status='finished', enddate=current_date()
				where id=%s;

				update bong.team_member_lnk
				set isactive=0, updatedate=now()
				where team_id=%s;
					'''
				, (team_id, team_id))
		#self.db.commit()

		c.close()
		self.db.close()

	def reject(self, team_id, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute('''
				update bong.team
				set status='failed', enddate=current_date()
				where id=%s;

				update bong.team_member_lnk
				set isactive=0, updatedate=now()
				where team_id=%s;

				update bong.team_member_lnk
				set status = 'rejected'
				where team_id=%s and uid = %s;
					'''
				, (team_id, team_id, team_id, uid))
		#self.db.commit()

		c.close()
		self.db.close()

	def try_match_user(self, user):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.uid,m.name,m.gender,m.birthday from bong.member m
		where m.uid not in
		(
		select l.uid from bong.team_member_lnk as l
		where l.isactive = 1
		)
		and m.uid not in
		(
		select distinct l3.uid from bong.team_member_lnk l2
		join bong.team_member_lnk l3
			on l2.team_id = l3.team_id and l3.uid != l2.uid
		where l2.uid = %s and l2.status='rejected' and TIMESTAMPDIFF(HOUR,l2.updatedate ,now()) <  48
		)
		and m.uid != %s
		and m.isactive =1
		''', (user.uid, user.uid))
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
			insert into bong.team(name,status,startdate) values(%s,%s,current_date());
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
		rowcount2 = c2.rowcount
		c2.close()
		self.db.close()

		if rowcount2 != 2L:
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
		self.reinitdb()
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

	def team_summary(self, team_id):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select a.startdate, max(a.dueday) as syncdate, avg(a.distance) as avg1, sum(a.distance) as sum1
		from(
		select t.startdate, a.dueday, sum(a.distance) as distance
		from bong.team_member_lnk tml 
		left join bong.activity a
			on tml.uid = a.uid
		join bong.team t
			on t.id = tml.team_id
		where tml.team_id=%s and a.dueday >= t.startdate
		group by t.startdate, a.dueday)a
		group by a.startdate
		'''
		, team_id)

		row = c.fetchone()
		c.close()
		self.db.close()

		if row is None:
			return None

		return _entity.TeamSummary(row[0], row[1], Decimal(row[2]).quantize(Decimal('0.00')), Decimal(row[3]).quantize(Decimal('0.00')))


	def save_activity(self, uid, num, daylist, distancelist):
		for i in range(num):
			self.reinitdb()
			c = self.db.cursor()
			c.execute(
			'''
			select uid from bong.activity where uid=%s and dueday=%s
			''', (uid, daylist[i]))
			rowcount = c.rowcount
			c.close()
			self.db.close()

			if rowcount != 0L:
				self.reinitdb()
				c = self.db.cursor()
				c.execute(
				'''
				update bong.activity set distance=%s,updatedate=now() where uid=%s and dueday=%s
				''', (distancelist[i], uid, daylist[i]))

				c.close()
				self.db.close()
			else:
				self.reinitdb()
				c = self.db.cursor()
				c.execute(
				'''
				insert into bong.activity(uid, dueday, distance, updatedate) values(%s, %s, %s, now())
				''', (uid, daylist[i], distancelist[i]))

				c.close()
				self.db.close()

	def batch_uids(self, page):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
			'''
			select distinct uid from bong.team_member_lnk tml
			where tml.isactive = 1
			order by id ASC
			''')
		rows = c.fetchall()
		c.close()
		self.db.close()

		list = []
		for row in rows:
			list.append(row[0])

		start = page * 15
		end = (page + 1) * 15

		return list[start:end]

	def load_msg(self, team_id):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.name, ms.content, ms.insertdate from bong.team_msg ms
		join bong.member m
			on ms.send_uid = m.uid
		where ms.team_id = %s
		order by ms.id desc 
		limit 0, 5
		''', team_id)

		rows = c.fetchall()
		c.close()
		self.db.close()

		msgs = []

		for row in rows:
			msgs.append(_entity.TeamMsg(row[0], row[1], row[2]))

		return msgs

	def create_msg(self, team_id, uid, content):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		insert into bong.team_msg
		(team_id, send_uid, content, insertdate) 
		values(%s, %s, %s, now())
		''', (team_id, uid, content))

		c.close()
		self.db.close()

	def create_visit(self, pagename, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		insert into bong.pagevisit
		(pagename, uid, insertdate) 
		values(%s, %s, now())
		''', (pagename, uid))

		c.close()
		self.db.close()


	def load_dream(self, uid, gender):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select uid from bong.member m
		where uid != %s and gender != %s
		and uid not in
		(
		select v.touid from bong.vote v
		where v.fromuid = %s
		)
		ORDER BY RAND()
		limit 1
		''', (uid, gender, uid))

		row = c.fetchone()
		c.close()
		self.db.close()

		if row is None:
			return None

		return row[0]

	def check_dream(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select p.insertdate from bong.pagevisit p
		where p.pagename='dream' and p.uid=%s
		order by p.id desc
		limit 1
		'''
		, uid)

		row = c.fetchone()
		c.close()
		self.db.close()

		if row is None:
			return None

		return row[0]

	def create_like(self, fromuid, touid, up):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		insert into bong.vote
		(fromuid, touid, up) 
		values(%s, %s, %s)
		''', (fromuid, touid, up))

		c.close()
		self.db.close()

	def my_fans(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.name,m.uid from bong.vote v
		join bong.member m
			on v.fromuid = m.uid
		where v.touid=%s
		union
		select m.name,m.uid from bong.member m
		where m.uid in ('77985753343930907800','51057590773664947750','43516437263501434011')
		''', uid)

		rows = c.fetchall()
		c.close()
		self.db.close()

		msgs = []

		for row in rows:
			msgs.append(_entity.Fans(row[0], row[1]))

		return msgs

	def create_question(self, fromuid, touid, content):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		insert into bong.msg
		(parent_id, fromuid, touid, content)
		values(-1, %s, %s, %s)
		''', (fromuid, touid, content))

		c.close()
		self.db.close()

	def reply_question(self, q_id, fromuid, touid, content):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		update bong.msg
		set isread =1, updatedate=now()
		where (parent_id=%s or id=%s) and isread=0;

		insert into bong.msg
		(parent_id, fromuid, touid, content)
		values(%s, %s, %s, %s)
		''', (q_id, q_id, q_id, fromuid, touid, content))

		c.close()
		self.db.close()

	def close_question(self, q_id):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		update bong.msg
		set isread =1, updatedate=now()
		where (parent_id=%s or id=%s) and isread=0;
		''', (q_id, q_id))

		c.close()
		self.db.close()

	def pick_question(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.id from bong.msg m
		where m.parent_id = -1 and m.fromuid != %s and m.touid = -1
		ORDER BY RAND()
		''', (uid,))

		rows = c.fetchall()
		c.close()
		self.db.close()

		for row in rows:
			if self.confirm_question(uid, row[0]):
				return row[0]

		return None

	def confirm_question(self, uid, q_id):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		update bong.msg
		set touid=%s, updatedate = now()
		where id = %s and isread=0 and touid = -1
		''', (uid, q_id))

		rowcount = c.rowcount
		c.close()
		self.db.close()

		if rowcount == -1:
			return False

		return True

	def load_question(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.id, m.parent_id from bong.msg m
		where m.touid=%s and isread=0
		limit 1
		''', (uid,))

		row = c.fetchone()
		c.close()
		self.db.close()

		if row is not None:
			if row[1] == -1L:
				return row[0]
			return row[1]

		return None

	def load_questionfeed(self, q_id):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.fromuid, m.content, m.insertdate from bong.msg m
		where m.id = %s or m.parent_id = %s
		order by m.id desc
		limit 10
		''', (q_id, q_id))

		rows = c.fetchall()
		c.close()
		self.db.close()

		list = []
		for row in rows:
			list.append(_entity.Answer(row[0], row[1], row[2]))

		return list

	def question_no(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.id from bong.msg m
		where m.parent_id = -1 and m.fromuid != %s and m.touid = -1
		''', (uid,))

		rowcount = c.rowcount
		c.close()
		self.db.close()

		return rowcount

	def answer_no(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.id from bong.msg m
		where m.touid=%s and isread=0
		''', (uid,))

		rowcount = c.rowcount
		c.close()
		self.db.close()

		return rowcount

	def new_reply(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select mem.name,m.fromuid, m.id, m.parent_id from bong.msg m
		join bong.member mem
			on m.fromuid = mem.uid
		where m.touid=%s and isread=0
		limit 10
		''', (uid,))

		rows = c.fetchall()
		c.close()
		self.db.close()

		dmlist = []
		for row in rows:
			question_id = 0L
			if row[3] == -1L:
				question_id = row[2]
			else:
				question_id = row[3]

			dmlist.append(_entity.DirectMessage(row[0], row[1], question_id))

		return dmlist

	def my_idols(self, uid):
		self.reinitdb()
		c = self.db.cursor()
		c.execute(
		'''
		select m.name, m.uid, m.gender from bong.member m
		where m.uid in 
		(
		select distinct(v.touid) from bong.vote v
		where v.fromuid=%s and v.up=1
		)
		order by rand()
		limit 5
		''', uid)

		rows = c.fetchall()
		c.close()
		self.db.close()

		idols = []

		for row in rows:
			idols.append(_entity.Idol(row[0], row[1], row[2]))

		return idols