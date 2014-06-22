select * from bong.member

select m.* from bong.member m
where m.uid not in
(
select l.uid from bong.team_member_lnk as l
where l.isactive = 1
)
and m.uid != '46731907030707230026'
and m.isactive =1

ALTER TABLE `bong`.`member` 
CHANGE COLUMN `name` `name` VARCHAR(45)  character set utf8 NOT NULL ;

select tml2.team_id, tml2.uid from bong.team_member_lnk tml2
where tml2.team_id in(
select tml.team_id from bong.team_member_lnk tml
where tml.uid= '14889209967394997743' and tml.isactive=1)
and tml2.uid != '14889209967394997743'


            insert into bong.team_member_lnk(uid,status,team_id,isactive)
            values('14889209967394997743','accept',1,1)
            insert into bong.team_member_lnk(uid,status,team_id,isactive)
            values('46731907030707230026','accept',1,1)
            
	


#delete from bong.team where id !=1

select * from bong.team;
select * from bong.team_member_lnk

select * from bong.token
select uid,access_token,expires_in,refresh_token,updatedate from bong.token
 where uid='46731907030707230026'

delete from bong.activity where uid != '3'

 
#IF exists (select uid from bong.activity where uid='14889209967394997743' and dueday='2014-05-20') THEN
select * from bong.activity
group by dueday

select current_date()

select t.startdate, a.dueday, sum(a.distance) 
from bong.team_member_lnk tml
join bong.activity a
	on tml.uid = a.uid
join bong.team t
	on t.id = tml.team_id
where team_id=16 and a.dueday >= t.startdate
group by t.startdate, a.dueday;

select a.startdate, max(a.dueday) as syncdate, avg(a.distance) as avg1, sum(a.distance) as sum1
from(
select t.startdate, a.dueday, sum(a.distance) as distance
from bong.team_member_lnk tml 
left join bong.activity a
	on tml.uid = a.uid
join bong.team t
	on t.id = tml.team_id
where tml.team_id=16 and a.dueday >= t.startdate
group by t.startdate, a.dueday)a
group by a.startdate


update bong.team
set status='finished', enddate=current_date()
where id=55;

update bong.team_member_lnk
set isactive=0, updatedate=now()
where team_id=55;

select distinct uid from bong.team_member_lnk tml
#where tml.isactive = 1
order by id ASC

