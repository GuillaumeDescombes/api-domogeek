#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Gruik coded by GuiguiAbloc
# http://blog.guiguiabloc.fr
# http://api.domogeek.fr
#
# update by GDE (python 3)

import web, sys, time
from wsgilog import WsgiLog
import json,hashlib,socket
from datetime import datetime,date,timedelta
import urllib.request, urllib.error
from Daemon import Daemon
from xml.dom.minidom import parseString
import syslog
import configparser
import Holiday
import ClassTempo
import ClassSchoolCalendar
import ClassVigilance
import ClassGeoLocation
import ClassDawnDusk
import ClassWeather
import ClassEJP
import ClassEcoW


#***************#
# log           #
#***************#
syslog.openlog("apidomogeek", syslog.LOG_PID)

#***************#
# configuration #
#***************#
configFileName = "/etc/apidomogeek.conf"
config = configparser.ConfigParser()
try:
  with open(configFileName) as stream:
    config.read_string("[nosection]\n" + stream.read())  # This line does the trick.
  syslog.syslog(syslog.LOG_INFO,"reading configuration file '%s' w/o any section" % configFileName)    
except configparser.DuplicateSectionError as e:
  with open(configFileName) as configfile:
    config.read_file(configfile)
  syslog.syslog(syslog.LOG_INFO,"reading configuration file '%s'" % configFileName)    
except FileNotFoundError as e:
  #default settings
  syslog.syslog(syslog.LOG_ERR,"cannot read configuration file '%s'" % configFileName)
  config["nosection"] = {"debug": True,
                         "timeout": 10,
                         "listenip": "127.0.0.1",
                         "listenport": 8080,
                         "googleapikey": "",
                         "bingmapapikey": "",
                         "geonameskey": "",
                         "worldweatheronlineapikey": "",
                         "openweathermapapikey":"",
                         "meteofranceapikey":"",
                         "useredis": True,
                         "redis_host": "127.0.0.1",
                         "redis_port": 6379
                        }
  try:
    with open(configFileName, 'w') as configfile:
      config.write(configfile)
    syslog.syslog(syslog.LOG_INFO,"writing default configuration file '%s'" % configFileName)    
  except:
    syslog.syslog(syslog.LOG_ERR,"cannot write default configuration file '%s'" % configFileName)

if config.getboolean("nosection","debug", fallback=True):
  syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))
  syslog.syslog(syslog.LOG_INFO, "Debug mode")
else:
  syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_INFO))  

#************#
# Cache      #
#************#

uselocalcache = config.getboolean("nosection", "uselocalcache", fallback=False)
if uselocalcache:
  try:
    config.add_section('cache')
    syslog.syslog(syslog.LOG_INFO,"adding cache section in configuration file '%s'" % configFileName)
  except:
    syslog.syslog(syslog.LOG_INFO,"Already a cache section in configuration file '%s'" % configFileName)

#***************#
# initialidation#
#***************#

# socket timeout in seconds
socket.setdefaulttimeout(config.getint("nosection","timeout", fallback=10))

school = ClassSchoolCalendar.schoolcalendar()
dayrequest = Holiday.jourferie()
temporequest = ClassTempo.EDFTempo()
geolocationrequest = ClassGeoLocation.geolocation()
dawnduskrequest = ClassDawnDusk.sunriseClass()
weatherrequest = ClassWeather.weather()
ejprequest = ClassEJP.EDFEJP()
ecowattrequest = ClassEcoW.EDFEcoWatt()

#local api url
localapiurl= "http://" + config.get("nosection", "listenip", fallback="127.0.0.1") + ":" + str(config.getint("nosection", "listenport",fallback=8080))
syslog.syslog(syslog.LOG_INFO, "local API URL: %s" % localapiurl)

#api key
googleapikey = config.get("nosection", "googleapikey", fallback='')
syslog.syslog(syslog.LOG_INFO, "googleapikey: %s" % googleapikey)

bingmapapikey = config.get("nosection", "bingmapapikey", fallback='')
syslog.syslog(syslog.LOG_INFO, "bingmapapikey: %s" % bingmapapikey)

geonameskey = config.get("nosection", "geonameskey", fallback='')
syslog.syslog(syslog.LOG_INFO, "geonameskey: %s" % geonameskey)

worldweatheronlineapikey = config.get("nosection", "worldweatheronlineapikey", fallback='')
syslog.syslog(syslog.LOG_INFO, "worldweatheronlineapikey: %s" % worldweatheronlineapikey)

openweathermapapikey = config.get("nosection", "openweathermapapikey", fallback='')
syslog.syslog(syslog.LOG_INFO, "openweathermapapikey: %s" % openweathermapapikey)

meteofranceapikey = config.get("nosection", "meteofranceapikey", fallback='')
syslog.syslog(syslog.LOG_INFO, "meteofranceapikey: %s" % meteofranceapikey)
vigilancerequest = ClassVigilance.MeteoFranceVigilance(meteofranceapikey)

##############
# REDIS      #
##############
rc = None
if config.getboolean("nosection", "useredis", fallback=True):
  try:
    import redis
  except:
    syslog.syslog(syslog.LOG_ERR,"No Redis module : https://pypi.python.org/pypi/redis/")
    sys.exit(1)
  redis_host = config.get("nosection", "redis_host", fallback="127.0.0.1")
  redis_port = config.getint("nosection", "redis_port", fallback=6379)
  rc= redis.Redis(host=redis_host, port=redis_port)
  rc.ping()
  rc.set("test", "ok")
  rc.expire("test" ,10)
  value = rc.get("test")
  syslog.syslog(syslog.LOG_INFO,"Connected to redis server")
  if value is None:
    syslog.syslog(syslog.LOG_ERR, "Could not connect to Redis host '%s' on port '%d'" % (redis_host, redis_port))
    sys.exit(1)

#***************#
# WEB           #
#***************#

web.config.debug = False
urls = (
  '/holiday/(.*)', 'holiday',
  '/tempoedf/(.*)', 'tempoedf',
  '/ejpedf/(.*)', 'ejpedf',
  '/schoolholiday/(.*)', 'schoolholiday',
  '/weekend/(.*)', 'weekend',
  '/holidayall/(.*)', 'holidayall',
  '/vigilance/(.*)', 'vigilance',
  '/geolocation/(.*)', 'geolocation',
  '/sun/(.*)', 'dawndusk',
  '/weather/(.*)', 'weather',
  '/season(.*)', 'season',
  '/myip(.*)', 'myip',
  '/feastedsaint/(.*)', 'feastedsaint',
  '/ecowattedf/(.*)', 'ecowattedf',
  '/(.*)', 'index'
)

class webLog(WsgiLog):
  def __init__(self, application):
    WsgiLog.__init__(
        self,
        application,
        logformat = '[%(asctime)s][%(name)s]: %(message)s',
        debug = False,
        tostream = True
        )

  def __call__(self, environ, start_response):
    def hstart_response(status, response_headers, *args):
      out = start_response(status, response_headers, *args)
      try:
        logline=environ["REMOTE_ADDR"]+" \""+environ["SERVER_PROTOCOL"]+" "+environ["REQUEST_METHOD"]+" "+environ["REQUEST_URI"]+"\" - "+status
      except err:
        logline="Could not log <%s> due to err <%s>" % (str(environ), err)
      syslog.syslog(syslog.LOG_INFO, logline)        
      return out
    return super(webLog, self).__call__(environ, hstart_response)

app = web.application(urls, globals())

class index:
    def GET(self, uri):
      # redirect to the static file ...
      request = uri.split('/')
      if request == ['']:      
        raise web.seeother('/static/index.html')
      else:
        raise web.seeother("/static/" + request[0])


"""
@api {get} /holiday/:date/:responsetype Holiday Status Request
@apiName GetHoliday
@apiGroup Domogeek
@apiDescription Ask to know if :date is a holiday
@apiParam {String} now  Ask for today.
@apiParam {String} tomorrow  Ask for tomorrow.
@apiParam {String} all  Ask for all entry.
@apiParam {Datetime} D-M-YYYY  Ask for specific date.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     Jour de Noel

     HTTP/1.1 200 OK
     no

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/holiday/now
     curl http://api.domogeek.fr/holiday/now/json
     curl http://api.domogeek.fr/holiday/all
     curl http://api.domogeek.fr/holiday/25-12-2014/json

"""
class holiday:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /holiday/{now|tomorrow|date(D-M-YYYY)}\n"
      try:
        format = request[1]
      except:
        format = None
      if request[0] == "now":
        syslog.syslog(syslog.LOG_DEBUG,"request holiday %s" % request[0])
        datenow = datetime.now()
        year = datenow.year
        month = datenow.month
        day = datenow.day 
        result = dayrequest.estferie([day,month,year])
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"holiday": result})
        else:
          return result
      if request[0] == "tomorrow":
        syslog.syslog(syslog.LOG_DEBUG,"request holiday %s" % request[0])
        datenow = datetime.now()
        datetomorrow = datenow + timedelta(days=1)
        year = datetomorrow.year
        month = datetomorrow.month
        day = datetomorrow.day
        result = dayrequest.estferie([day,month,year])
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"holiday": result})
        else:
          return result
      if request[0] == "all":
        syslog.syslog(syslog.LOG_DEBUG,"request holiday %s" % request[0])
        datenow = datetime.now()
        year = datenow.year
        listvalue = []
        F, J, L = dayrequest.joursferies(year,1,'/')
        for i in range(0,len(F)):
          result = F[i], "%10s" % (J[i]), L[i]
          listvalue.append(result)
          response = json.dumps(listvalue)
        return response

      if request[0] != "now" and request[0] != "all" and request[0] != "tomorrow":
        try:
          daterequest = request[0]
          result = daterequest.split('-') 
        except:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        try:
          day = int(result[0])
          month = int(result[1])
          year = int(result[2])
        except:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        if day > 31 or month > 12:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        syslog.syslog(syslog.LOG_DEBUG,"request holiday %s" % request[0])
        result = dayrequest.estferie([day,month,year])
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"holiday": result})
        else:
          return result


"""
@api {get} /weekend/:daterequest/:responsetype Week-end Status Request
@apiName GetWeekend
@apiGroup Domogeek
@apiDescription Ask to know if :daterequest is a week-end day
@apiParam {String} daterequest Ask for specific date {now | tomorrow | D-M-YYYY}.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     True

     HTTP/1.1 200 OK
     False

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/weekend/now
     curl http://api.domogeek.fr/weekend/tomorrow
     curl http://api.domogeek.fr/weekend/now/json
     curl http://api.domogeek.fr/weekend/16-07-2014/json

"""
class weekend:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /weekend/{now|tomorrow|date(D-M-YYYY)}\n"
      try:
        format = request[1]
      except:
        format = None
      if request[0] == "now":
        syslog.syslog(syslog.LOG_DEBUG,"request weekend %s" % request[0])        
        datenow = datetime.now()
        daynow = datetime.now().weekday()
        day = datenow.day
        if daynow == 5 or daynow == 6:
          result = "True"
        else:
          result = "False"
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"weekend": result})
        else:
          return result
      if request[0] == "tomorrow":
        syslog.syslog(syslog.LOG_DEBUG,"request weekend %s" % request[0])        
        today = date.today()
        datetomorrow = today + timedelta(days=1)
        day = datetomorrow.weekday()
        if day == 5 or day == 6:
          result = "True"
        else:
          result = "False"
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"weekend": result})
        else:
          return result
      if request[0] != "now" and request[0] != "tomorrow":
        try:
          daterequest = request[0]
          day,month,year = daterequest.split('-')
        except:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        try:
          int(day)
          int(month)
          int(year)
        except:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        syslog.syslog(syslog.LOG_DEBUG,"request weekend %s" % request[0])        
        requestday = date(int(year),int(month),int(day)).weekday()
        if requestday == 5 or requestday == 6:
          result = "True"
        else:
          result = "False"
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"weekend": result})
        else:
          return result

"""
@api {get} /holidayall/:zone/:daterequest All Holidays Status Request
@apiName GetHolidayall
@apiGroup Domogeek
@apiDescription Ask to know if :daterequest is a holiday, school holiday and week-end day
@apiParam {String} zone  School Zone (A, B or C).
@apiParam {String} daterequest Ask for specific date {now | tomorrow | D-M-YYYY}.
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     {"holiday": "False", "weekend": "False", "schoolholiday": "Vacances de printemps - Zone A"}


@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/holidayall/A/now
     curl http://api.domogeek.fr/holidayall/A/tomorrow
     curl http://api.domogeek.fr/holidayall/B/25-02-2014
"""
class holidayall:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /holidayall/{zone}/{now|tomorrow|date(D-M-YYYY)}\n"
      try:
        zone = request[0]
      except:
        return "Incorrect request : /holidayall/{zone}/{now|tomorrow|date(D-M-YYYY)}\n"
      try:
        zoneok = str(zone.upper())
      except:
        return "Wrong Zone (must be A, B or C)"
      if len(zoneok) > 1:
        return "Wrong Zone (must be A, B or C)"
      if zoneok not in ["A","B","C"]:
        return "Incorrect request : /holidayall/{zone}/{now|tomorrow|date(D-M-YYYY)}\n"
      try:
        daterequest = request[1]
      except:
        return "Incorrect request : /holidayall/{zone}/{now|tomorrow|date(D-M-YYYY)}\n"
      if request[1] == "now":
        syslog.syslog(syslog.LOG_DEBUG,"request holidayall %s" % request[1])        
        try:
          responseholiday = urllib.request.urlopen(localapiurl+'/holiday/now')
          responseschoolholiday = urllib.request.urlopen(localapiurl+'/schoolholiday/'+zoneok+'/now')
          responseweekend = urllib.request.urlopen(localapiurl+'/weekend/now')
          resultholiday = responseholiday.read().decode('UTF-8')
          resultschoolholiday = responseschoolholiday.read().decode('UTF-8')
          resultweekend = responseweekend.read().decode('UTF-8')
        except:
          return "no data available"
        web.header('Content-Type', 'application/json')
        return json.dumps({"holiday": resultholiday, "schoolholiday": resultschoolholiday, "weekend": resultweekend}, ensure_ascii=False).encode('utf8')
      if request[1] == "tomorrow":
        syslog.syslog(syslog.LOG_DEBUG,"request holidayall %s" % request[1])        
        try:
          responseholiday = urllib.request.urlopen(localapiurl+'/holiday/tomorrow')
          responseschoolholiday = urllib.request.urlopen(localapiurl+'/schoolholiday/'+zoneok+'/tomorrow')
          responseweekend = urllib.request.urlopen(localapiurl+'/weekend/tomorrow')
          resultholiday = responseholiday.read().decode('utf-8')
          resultschoolholiday = responseschoolholiday.read().decode('utf-8')
          resultweekend = responseweekend.read().decode('utf-8')
        except:
          return "no data available"
        web.header('Content-Type', 'application/json')
        return json.dumps({"holiday": resultholiday, "schoolholiday": resultschoolholiday, "weekend": resultweekend}, ensure_ascii=False).encode('utf8')
      
      if request[1] != "now" and request[1] != "tomorrow":
        try:
          daterequest = request[1]
          day,month,year = daterequest.split('-')
        except:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        try:
          int(day)
          int(month)
          int(year)
        except:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        syslog.syslog(syslog.LOG_DEBUG,"request holidayall %s" % request[1])        
        try:
          responseholiday = urllib.request.urlopen(localapiurl+'/holiday/'+daterequest)
          responseschoolholiday = urllib.request.urlopen(localapiurl+'/schoolholiday/'+zoneok+'/'+daterequest)
          responseweekend = urllib.request.urlopen(localapiurl+'/weekend/'+daterequest)
          resultholiday = responseholiday.read().decode('utf-8')
          resultschoolholiday = responseschoolholiday.read().decode('utf-8')
          resultweekend = responseweekend.read().decode('utf-8')
        except:
          return "no data available"
        web.header('Content-Type', 'application/json')
        return json.dumps({"holiday": resultholiday, "schoolholiday": resultschoolholiday, "weekend": resultweekend}, ensure_ascii=False).encode('utf8')


"""
@api {get} /tempoedf/:date/:responsetype Tempo EDF color Request
@apiName GetTempo
@apiGroup Domogeek
@apiDescription Ask the EDF Tempo color
@apiParam {String} now  Ask for today.
@apiParam {String} tomorrow Ask for tomorrow.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
HTTP/1.1 200 OK
Content-Type: application/json
Transfer-Encoding: chunked
Date: Thu, 03 Jul 2014 17:16:47 GMT
Server: localhost
{"tempocolor": "bleu"}

@apiErrorExample Error-Response:
HTTP/1.1 400 Bad Request
400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/tempoedf/now
     curl http://api.domogeek.fr/tempoedf/now/json
     curl http://api.domogeek.fr/tempoedf/tomorrow
     curl http://api.domogeek.fr/tempoedf/tomorrow/json

"""

class tempoedf:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /tempoedf/{now | tomorrow}\n"
      try:
        format = request[1]
      except:
        format = None
      if request[0] == "now" or request[0] == "tomorrow":
        syslog.syslog(syslog.LOG_DEBUG,f"request tempoedf {request[0]}")
        tempoRedis = None
        key=f"tempo{request[0]}"
        redisKey =  hashlib.md5(key.encode('utf-8')).hexdigest()
        if not rc is None:
          tempoRedis = rc.get(redisKey)
        if tempoRedis is None:
          if request[0] == "now":
            result = temporequest.getToday()
          elif request[0] == "tomorrow":
            result = temporequest.getTomorrow()
          else:
            result = ["ERROR",""]
          if not rc is None and result[0] == "OK":
            rc.set(redisKey, result[1], 1800)
            rc.expire(redisKey,1800)
            syslog.syslog(syslog.LOG_DEBUG,f"Set '{key}' in REDIS: '{result[1]}'")
        else:
          result = ["OK",""]
          result [1] = tempoRedis.decode("UTF-8")
          syslog.syslog(syslog.LOG_DEBUG,f"Found '{key}' in REDIS: 'result[1]'")
        if format == "json":
          web.header('Content-Type', 'application/json')
          if result[0] == "OK":
            return json.dumps({"tempocolor": result[1]})
          else:
            return json.dumps({"tempocolor": result[0]})
        else:
          if result[0] == "OK":
            return result[1]
          else:
            return result[0]
      # Other case
      web.badrequest()
      return "Incorrect request : /tempoedf/{now | tomorrow}\n"


"""
@api {get} /schoolholiday/:zone/:daterequest/:responsetype School Holiday Status Request
@apiName GetSchoolHoliday
@apiGroup Domogeek
@apiDescription Ask to know if :daterequest is a school holiday (UTF-8 response)
@apiParam {String} zone  School Zone (A, B or C).
@apiParam {String} daterequest Ask for specific date {now | all | D-M-YYYY}.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     Vacances de la Toussaint 

     HTTP/1.1 200 OK
     False

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/schoolholiday/A/now
     curl http://api.domogeek.fr/schoolholiday/A/now/json
     curl http://api.domogeek.fr/schoolholiday/A/all
     curl http://api.domogeek.fr/schoolholiday/A/25-12-2014/json

"""

class schoolholiday:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /schoolholiday/{zone}/{now|tomorrow|all|date(D-M-YYYY)}\n"
      try:
        zone = request[0]
      except:
        return "Incorrect request : /schoolholiday/{zone}/{now|tomorrow|all|date(D-M-YYYY)}\n"
      try:
        zoneok = str(zone.upper())
      except:
        return "Wrong Zone (must be A, B or C)"
      if len(zoneok) > 1:
        return "Wrong Zone (must be A, B or C)"

      if zoneok not in ["A","B","C"]:
        return "Incorrect request : /schoolholiday/{zone}/{now|tomorrow|all|date(D-M-YYYY)}\n"
      try:
        daterequest = request[1]
      except:
        return "Incorrect request : /schoolholiday/{zone}/{now|tomorrow|all|date(D-M-YYYY)}\n"
      try:
        format = request[2]
      except:
        format = None
      datenow = datetime.now()
      year = datenow.year
      month = datenow.month
      day = datenow.day

      if daterequest == "now":
        #try:
        syslog.syslog(syslog.LOG_DEBUG,"request schoolholiday %s" % daterequest)
        getschoolholidaynow = None
        if not rc is None:
          key="schoolholidaynow"+zoneok
          rediskeyschoolholidaynow =  hashlib.md5(key.encode('utf-8')).hexdigest()
          getschoolholidaynow = rc.get(rediskeyschoolholidaynow)
        if getschoolholidaynow is None:
          result = school.isschoolcalendar(zoneok,day,month,year)
          if result is None or result == "None":
            result = "False"
          if not rc is None:
            key="schoolholidaynow"+zoneok
            rediskeyschoolholidaynow =  hashlib.md5(key.encode('utf-8')).hexdigest()
            rc.set(rediskeyschoolholidaynow, result, 1800)
            rc.expire(rediskeyschoolholidaynow ,1800)
            syslog.syslog(syslog.LOG_DEBUG,"SET SCHOOL HOLIDAY "+zoneok+ " NOW IN REDIS: '%s'" % result)
        else:
          result = getschoolholidaynow.decode('utf-8')
          syslog.syslog(syslog.LOG_DEBUG,"FOUND SCHOOL HOLIDAY "+zoneok+" NOW IN REDIS: '%s'" % result)
        #except:
        #   result = school.isschoolcalendar(zoneok,day,month,year)
        #if result is None or result == "None":
        #  result = "False"
        try:
          description = result.decode('utf-8')
        except:
          description = result
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"schoolholiday": description}, ensure_ascii=False).encode('utf8')
        else:
          return description

      if daterequest == "tomorrow":
        syslog.syslog(syslog.LOG_DEBUG,"request schoolholiday %s" % daterequest)
        datenow = datetime.now()
        datetomorrow = datenow + timedelta(days=1)
        yeartomorrow = datetomorrow.year
        monthtomorrow = datetomorrow.month
        daytomorrow = datetomorrow.day
        #try:
        getschoolholidaytomorrow = None
        if not rc is None:
          key="schoolholidaytomorrow"+zoneok
          rediskeyschoolholidaytomorrow =  hashlib.md5(key.encode('utf-8')).hexdigest()
          getschoolholidaytomorrow = rc.get(rediskeyschoolholidaytomorrow)
        if getschoolholidaytomorrow is None:
          result = school.isschoolcalendar(zoneok,daytomorrow,monthtomorrow,yeartomorrow)
          if not rc is None:
            key="schoolholidaytomorrow"+zoneok
            rediskeyschoolholidaytomorrow =  hashlib.md5(key.encode('utf-8')).hexdigest()
            rc.set(rediskeyschoolholidaytomorrow, result, 1800)
            rc.expire(rediskeyschoolholidaytomorrow ,1800)
            syslog.syslog(syslog.LOG_DEBUG,"SET SCHOOL HOLIDAY "+zoneok+ " TOMORROW IN REDIS: %s" % result)
        else:
          result = getschoolholidaytomorrow
          syslog.syslog(syslog.LOG_DEBUG,"FOUND SCHOOL HOLIDAY "+zoneok+" TOMORROW IN REDIS: %s" % result)
        #except:
        #   result = school.isschoolcalendar(zoneok,daytomorrow,monthtomorrow,yeartomorrow)
        if result is None or result == "None":
          result = "False"
        try:
          description = result.decode('utf-8')
        except:
          description = result
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"schoolholiday": description}, ensure_ascii=False).encode('utf8')
        else:
          return description

      if daterequest == "all":
        syslog.syslog(syslog.LOG_DEBUG,"request schoolholiday %s" % daterequest)
        result = school.getschoolcalendar(zone)
        try:
          description = result.decode('unicode_escape')
        except:
          description = result
        web.header('Content-Type', 'application/json')
        return description
      if daterequest != "now" and daterequest != "all" and daterequest != "tomorrow":
        try:
          result = daterequest.split('-')
        except:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        try:
          day = int(result[0])
          month = int(result[1])
          year = int(result[2])
        except:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        if day > 31 or month > 12:
          web.badrequest()
          return "Incorrect date format : D-M-YYYY\n"
        syslog.syslog(syslog.LOG_DEBUG,"request schoolholiday %s" % daterequest)
        result = school.isschoolcalendar(zoneok,day,month,year)
        if result is None or result == "None":
          result = "False"
        try:
          description = result.decode('utf-8')
        except:
          description = result
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"schoolholiday": description}, ensure_ascii=False).encode('utf8')
        else:
          return description


"""
@api {get} /vigilance/:department/:vigilancerequest/:responsetype Vigilance MeteoFrance 
@apiName GetVigilance
@apiGroup Domogeek
@apiDescription Ask Vigilance MeteoFrance for :department
@apiParam {String} department Department number (France Metropolitan).
@apiParam {String} vigilancerequest Vigilance request {color|risk|flood|storm|all}.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     {"vigilanceflood": "jaune", "vigilancecolor": "orange", "vigilancerisk": "orages"}

     HTTP/1.1 200 OK
     vert 

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/vigilance/29/color
     curl http://api.domogeek.fr/vigilance/29/color/json
     curl http://api.domogeek.fr/vigilance/29/risk/json
     curl http://api.domogeek.fr/vigilance/29/all

"""
class vigilance:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /vigilance/{department}/{color|risk|flood|storm|all}\n"
      try:
        dep = request[0]
      except:
        web.badrequest()
        return "Incorrect request : /vigilance/{department}/{color|risk|flood|storm|all}\n"
      try:
        vigilancequery = request[1]
      except:
        web.badrequest()
        return "Incorrect request : /vigilance/{department}/{color|risk|flood|storm|all}\n"
      try:
        format = request[2]
      except:
        format = None
      if len(dep) > 2:
        web.badrequest()
        return "Incorrect request : /vigilance/{department number}/{color|risk|flood|storm|all}\n"
      if vigilancequery not in ["color","risk","flood","storm","all"]: 
        web.badrequest()
        return "Incorrect request : /vigilance/{department}/{color|risk|flood|storm|all}\n"
      if dep == "20":
        dep = "2A"
      syslog.syslog(syslog.LOG_DEBUG,"request vigilance %s" % dep)
      vigilanceRedis = None
      key=dep+"vigilance"
      redisKey =  hashlib.md5(key.encode('utf-8')).hexdigest()
      if not rc is None:
        vigilanceRedis = rc.get(redisKey)
      if vigilanceRedis is None:
        result = vigilancerequest.getVigilance(dep)
        if not rc is None:
          data = "(" + ",".join(result) + ")"
          rc.set(redisKey, data, 1800)
          rc.expire(redisKey ,1800)
          syslog.syslog(syslog.LOG_DEBUG, f"Set Vigilance {dep} in Redis: '{data}'")
      else:
        data = getvigilance.decode("UTF-8")
        tr1 = data.replace("(","")
        tr2 = tr1.replace(")","")
        tr3 = tr2.replace("'","")
        tr4 = tr3.replace(" ","")
        result = tr4.split(',')
        syslog.syslog(syslog.LOG_DEBUG,f"Found VIgilance {dep} in Redis: '{data}'")
      riskName = result[1]
      globalColor = result[2]
      floodColor = result[3]
      stormColor = result[4]
      if vigilancequery == "color":
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"vigilancecolor": globalColor})
        else:
          return globalColor
      if vigilancequery == "risk":
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"vigilancerisk": riskName})
        else:
          return riskName
      if vigilancequery == "flood":
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"vigilanceflood": floodColor})
        else:
          return floodColor
      if vigilancequery == "storm":
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"vigilancestorm": stormColor})
        else:
          return stormColor
      if vigilancequery == "all":
        web.header('Content-Type', 'application/json')
        return json.dumps({"vigilancecolor": globalColor, "vigilancerisk": riskName, "vigilanceflood": floodColor, "vigilancestorm": stormColor})
      # Other case
      web.badrequest()
      return "Incorrect request : /vigilance/{department}/{color|risk|flood|storm|all}\n"

"""
@api {get} /geolocation/:city/:country City, Country Geolocation 
@apiName GetGeolocation
@apiGroup Domogeek
@apiDescription Ask geolocation (latitude/longitude) :city :country
@apiParam {String} city City name (avoid accents, no space).
@apiParam {String} country Country name (France by default).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     {"latitude": 48.390394000000001, "longitude": -4.4860759999999997}

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/geolocation/brest
"""
class geolocation:
    def GET(self,uri):
      checkgoogle = False
      checkbing = False
      checkgeonames = False
      inredis = False
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /geolocation/{city} or /geolocation/{city}/{country}\n"
      try:
        city = request[0]
      except:
        return "Incorrect request : /geolocation/{city} or /geolocation/{city}/{country}\n"
      try:
        country = request[1]
      except:
        country="France"
        pass
      syslog.syslog(syslog.LOG_DEBUG,"request geolocation %s, %s" % (city, country))                
      getlocation = None
      if not rc is None:
        #trying in REDIS cache (if enabled)
        key=city+", "+country
        rediskey = hashlib.md5(key.encode('utf-8')).hexdigest()
        getlocation = rc.get(rediskey).decode("UTF-8")
      if not getlocation is None:
        syslog.syslog(syslog.LOG_DEBUG,"FOUND LOCATION IN REDIS: %s" % getlocation)
        tr1 = getlocation.replace("(","")
        tr2 = tr1.replace(")","")
        data = tr2.split(',')
        lat=float(data[0])
        lng=float(data[1])
      #trying in local cache 
      if uselocalcache and getlocation is None:
        key="geolocation|" + city + "|" + country
        getlocation = config.get("cache", key, fallback=None)
        if not getlocation is None:
          syslog.syslog(syslog.LOG_DEBUG,"FOUND LOCATION IN LOCAL CACHE: %s" % getlocation)
          tr1 = getlocation.replace("(","")
          tr2 = tr1.replace(")","")
          data = tr2.split(',')
          lat=float(data[0])
          lng=float(data[1])

      #either in REDIS or LOCAL CACHE
      if not getlocation is None:
        web.header('Content-Type', 'application/json')
        return json.dumps({"latitude": lat, "longitude": lng})        
      
      #trying googleAPI
      if googleapikey != '' and getlocation is None:
        try:
          syslog.syslog(syslog.LOG_DEBUG,"Request Google Geolocation")
          data = geolocationrequest.geogoogle(city+", "+country, googleapikey)
        except Exception as e:
          syslog.syslog(syslog.LOG_ERR, 'Google Geolocation - An exception occurred: {}'.format(e))
          data= False
        if not data :
          syslog.syslog(syslog.LOG_DEBUG,"NO GEO DATA FROM GOOGLE")
        else:
          lat=data[0]
          lng=data[1]
          getlocation = "(" + str(lat) + "," + str(lng) + ")"
          syslog.syslog(syslog.LOG_DEBUG,"GEO DATA FROM GOOGLE: %s " % getlocation)

      #try bingApi
      if bingmapapikey != '' and getlocation is None:
        try:
          syslog.syslog(syslog.LOG_DEBUG,"Request Bing Geolocation")
          data = geolocationrequest.geobing(city+", "+country, bingmapapikey)
        except Exception as e:
          syslog.syslog(syslog.LOG_ERR, 'Bing Geolocation - An exception occurred: {}'.format(e))
          data= False
        if not data:
          syslog.syslog(syslog.LOG_DEBUG,"NO GEO DATA FROM BING")
        else:
          lat=data[0]
          lng=data[1]
          getlocation = "(" + str(lat) + "," + str(lng) + ")"          
          syslog.syslog(syslog.LOG_DEBUG,"GEO DATA FROM BING: %s " % getlocation)

      #try geonames
      if geonameskey != '' and getlocation is None:
        try:
          syslog.syslog(syslog.LOG_DEBUG,"Request GEONAMES Geolocation")
          data = geolocationrequest.geonames(city+", "+country, geonameskey)
        except Exception as e:
          syslog.syslog(syslog.LOG_ERR, 'GEONAMES Geolocation - An exception occurred: {}'.format(e))
          data= False
        if not data :
          syslog.syslog(syslog.LOG_DEBUG,"NO GEO DATA FROM GEONAMES")
        else:
          lat=data[0]
          lng=data[1]
          getlocation = "(" + str(lat) + "," + str(lng) + ")"
          syslog.syslog(syslog.LOG_DEBUG,"GEO DATA FROM GEONAMES: %s " % getlocation)
            
      if getlocation is None:
        syslog.syslog(syslog.LOG_DEBUG,"NO GEOLOCATION DATA AVAILABLE for %s, %s" % (city, country))
        return "NO GEOLOCATION DATA AVAILABLE\n"
      else:
        if not rc is None:
          key=city+", "+country
          rediskey =  hashlib.md5(key.encode('utf-8')).hexdigest()
          rc.set(rediskey, getlocation )
          syslog.syslog(syslog.LOG_DEBUG, "SET GEOLOCATION "+city+", "+country+" IN REDIS: (%s, %s)'" % (str(lat), str(lng)))            
        if uselocalcache:
          key="geolocation|" + city + "|" + country
          config.set("cache", key, getlocation)  
          syslog.syslog(syslog.LOG_DEBUG, "SET GEOLOCATION "+city+", "+country+" IN LOCAL CACHE: (%s, %s)'" % (str(lat), str(lng)))            
          try:
            with open(configFileName, 'w') as configfile:
              config.write(configfile)
              syslog.syslog(syslog.LOG_INFO,"writing configuration file '%s'" % configFileName)    
          except:
            pass          
        web.header('Content-Type', 'application/json')
        return json.dumps({"latitude": lat, "longitude": lng})
         

"""
@api {get} /sun/:city/:sunrequest/:date/:responsetype Sun Status Request 
@apiName GetSun
@apiGroup Domogeek
@apiDescription Ask to know sunrise, sunset, zenith, day duration for :date in :city (France)
@apiParam {String} city City name (avoid accents, no space, France Metropolitan).
@apiParam {String} sunrequest  Ask for {sunrise | sunset | zenith | dayduration | all}.
@apiParam {String} date  Date request {now | tomorrow}.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     {"sunset": "20:59"}

     HTTP/1.1 200 OK
     {"dayduration": "15:06", "sunset": "21:18", "zenith": "13:44", "sunrise": "6:11"}

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/sun/brest/all/now
     curl http://api.domogeek.fr/sun/bastia/sunset/now/json
     curl http://api.domogeek.fr/sun/strasbourg/sunrise/tomorrow

"""
class dawndusk:
    def GET(self,uri):
      getutc = float(time.strftime("%z")[:3])
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /sun/city/{sunrise|sunset|zenith|dayduration|all}/{now|tomorrow}\n"
      try:
        city = request[0]
      except:
        web.badrequest()
        return "Incorrect request : /sun/city/{sunrise|sunset|zenith|dayduration|all}/{now|tomorrow}\n"
      if len(city) < 1:
          web.badrequest()
          return "Incorrect request : /sun/city/{sunrise|sunset|zenith|dayduration|all}/{now|tomorrow}\n"
      try:
        testUnicode=str(city)
      except UnicodeEncodeError:
        web.badrequest()
        return "Incorrect city format : /sun/city/{sunrise|sunset|zenith|dayduration|all}/{now|tomorrow}\n"
      try:
        dawnduskrequestelement = request[1]
      except:
        web.badrequest()
        return "Incorrect request : /sun/city/{sunrise|sunset|zenith|dayduration|all}/{now|tomorrow}\n"
      try:
        daterequest = request[2]
      except:
       web.badrequest()
       return "Incorrect request : /sun/city/{sunrise|sunset|zenith|dayduration|all}/{now|tomorrow}\n"
      try:
        format = request[3]
      except:
        format = None
      if dawnduskrequestelement not in ["sunrise", "sunset", "zenith", "dayduration", "all"]:
        return "Incorrect request : /sun/city/{sunrise|sunset|zenith|dayduration|all}/{now|tomorrow}\n"
      syslog.syslog(syslog.LOG_DEBUG,"request dawndusk (sun) %s" % request[2])  
      try:
        getlocation = None
        if not rc is None:
          key=city
          rediskey =  hashlib.md5(key.encode('utf-8')).hexdigest()
          getlocation = rc.get(rediskey)
        if getlocation is None:
          syslog.syslog(syslog.LOG_DEBUG,"GET GEODATA for '%s'" % city)
          responsegeolocation = urllib.request.urlopen(localapiurl+'/geolocation/'+city)
          resultgeolocation = json.load(responsegeolocation)
          latitude =  resultgeolocation["latitude"]
          longitude =  resultgeolocation["longitude"]
        else:
          syslog.syslog(syslog.LOG_DEBUG,"FOUND GEODATA IN REDIS for '%s'" % city)
          tr1 =  getlocation.decode("UTF-8").replace("(","")
          tr2 = tr1.replace(")","")
          data = tr2.split(',')
          latitude = float(data[0])
          longitude = float(data[1])
      except:
        return "no GEO data available"
      if request[2] == "now":
        today=date.today()
      elif request[2] == "tomorrow":
        today = date.today() + timedelta(days=1)
      else:
        return "Incorrect request : /sun/city/{sunrise|sunset|zenith|dayduration|all}/{now|tomorrow}\n"
      dawnduskrequest.setNumericalDate(today.day,today.month,today.year)
      dawnduskrequest.setLocation(latitude, longitude)
      dawnduskrequest.calculateWithUTC(getutc)
      sunrise = dawnduskrequest.sunriseTime
      zenith = dawnduskrequest.meridianTime
      sunset = dawnduskrequest.sunsetTime
      dayduration =dawnduskrequest.durationTime
      if request[2] == "now" and dawnduskrequestelement == "all" :
          web.header('Content-Type', 'application/json')
          return json.dumps({"sunrise": sunrise, "zenith": zenith, "sunset": sunset, "dayduration": dayduration})
      if request[2] == "now" and dawnduskrequestelement == "sunrise" :
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"sunrise": sunrise})
          else:
            return sunrise
      if request[2] == "now" and dawnduskrequestelement == "sunset" :
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"sunset": sunset})
          else:
            return sunset
      if request[2] == "now" and dawnduskrequestelement == "zenith" :
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"zenith": zenith})
          else:
            return zenith
      if request[2] == "now" and dawnduskrequestelement == "dayduration" :
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"dayduration": dayduration})
          else:
            return dayduration
      if request[2] == "tomorrow" and dawnduskrequestelement == "all" :
          web.header('Content-Type', 'application/json')
          return json.dumps({"sunrise": sunrise, "zenith": zenith, "sunset": sunset, "dayduration": dayduration})
      if request[2] == "tomorrow" and dawnduskrequestelement == "sunrise" :
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"sunrise": sunrise})
          else:
            return sunrise
      if request[2] == "tomorrow" and dawnduskrequestelement == "sunset" :
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"sunset": sunset})
          else:
            return sunset
      if request[2] == "tomorrow" and dawnduskrequestelement == "zenith" :
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"zenith": zenith})
          else:
            return zenith
      if request[2] == "tomorrow" and dawnduskrequestelement == "dayduration" :
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"dayduration": dayduration})
          else:
            return dayduration

"""
@api {get} /weather/:city/:weatherrequest/:date/:responsetype Weather Status Request
@apiName GetWeather
@apiGroup Domogeek
@apiDescription Ask for weather (temperature, humidity, pressure, windspeed...) for :date in :city (France)
@apiParam {String} city City name (avoid accents, no space, France Metropolitan).
@apiParam {String} weatherrequest  Ask for {temperature|humidity[pressure|windspeed|weather|rain|all}.
@apiParam {String} date  Date request {today | tomorrow}.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     {u'min': 15.039999999999999, u'max': 20.34, u'eve': 19.989999999999998, u'morn': 20.34, u'night': 15.039999999999999, u'day': 20.34}

     HTTP/1.1 200 OK
     {"pressure": 1031.0799999999999}

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/weather/brest/all/today
     curl http://api.domogeek.fr/weather/brest/pressure/today/json
     curl http://api.domogeek.fr/weather/brest/weather/tomorrow
     curl http://api.domogeek.fr/weather/brest/rain/today

"""

class weather:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /weather/city/{temperature|humidity|pressure|weather|windspeed|rain|all}/{today|tomorrow}\n"
      try:
        city = request[0]
      except:
        return "Incorrect request : /weather/city/{temperature|humidity|pressure|weather|windspeed|rain|all}/{today|tomorrow}\n"
      try:
        weatherrequestelement = request[1]
      except:
        return "Incorrect request : /weather/city/{temperature|humidity|pressure|weather|windspeed|rain|all}/{today|tomorrow}\n"
      try:
        daterequest = request[2]
      except:
        return "Incorrect request : /weather/city/{temperature|humidity|pressure|weather|windspeed|rain|all}/{today|tomorrow}\n"
      try:
        format = request[3]
      except:
        format = None
      if weatherrequestelement not in ["temperature", "humidity", "pressure", "weather", "windspeed", "rain", "all"]:
        return "Incorrect request : /weather/city/{temperature|humidity|pressure|weather|windspeed|rain|all}/{today|tomorrow}\n"
      syslog.syslog(syslog.LOG_DEBUG,"request weather %s %s " % (request[0],request[2]))  
      try:
        getlocation = None
        if not rc is None:
          key=city
          rediskey =  hashlib.md5(key.encode('utf-8')).hexdigest()
          getlocation = rc.get(rediskey)
        if getlocation is None:
          syslog.syslog(syslog.LOG_DEBUG,"GET GEODATA for '%s'" % city)
          responsegeolocation = urllib.request.urlopen(localapiurl+'/geolocation/'+city)
          resultgeolocation = json.load(responsegeolocation)
          latitude =  resultgeolocation["latitude"]
          longitude =  resultgeolocation["longitude"]
        else:
          syslog.syslog(syslog.LOG_DEBUG,"FOUND GEODATA IN REDIS for '%s'" % city)
          tr1 =  getlocation.decode("UTF-8").replace("(","")
          tr2 = tr1.replace(")","")
          data = tr2.split(',')
          latitude = float(data[0])
          longitude = float(data[1])
      except:
        return "no GEO data available"
      if request[2] == "today":
        todayweather = weatherrequest.todayopenweathermap(latitude, longitude, weatherrequestelement, openweathermapapikey)
        datenow = datetime.now()
        datetoday = datenow.strftime('%Y-%m-%d')
#        try:
        gettodayrain=None
        if not rc is None:
          key=str(latitude)+str(longitude)+str(datetoday)
          rediskeytodayrain = hashlib.md5(key.encode('utf-8')).hexdigest()
          gettodayrain = rc.get(rediskeytodayrain)
        if gettodayrain is None:
          todayrain = weatherrequest.getrain(latitude, longitude, worldweatheronlineapikey, datetoday)
          if not rc is None:
            key=str(latitude)+str(longitude)+str(datetoday)
            rediskeytodayrain = hashlib.md5(key.encode('utf-8')).hexdigest()
            rc.set(rediskeytodayrain, todayrain)
            rc.expire(rediskeytodayrain, 3600)
            syslog.syslog(syslog.LOG_DEBUG,"SET WEATHER RAIN NOW IN REDIS")
        else:
          todayrain = gettodayrain
          syslog.syslog(syslog.LOG_DEBUG,"FOUND WEATHER RAIN NOW IN REDIS")
 #       except:
  #        todayrain = weatherrequest.getrain(latitude, longitude, worldweatheronlineapikey, datetoday)
        if weatherrequestelement != "all" or weatherrequestelement != "temperature" or weatherrequestelement != "weather":
          if format == "json":
              web.header('Content-Type', 'application/json')
              if weatherrequestelement == "humidity":
                return json.dumps({"humidity": todayweather})
              if weatherrequestelement == "pressure":
                return json.dumps({"pressure": todayweather})
              if weatherrequestelement == "windspeed":
                return json.dumps({"windspeed": todayweather})
              if weatherrequestelement == "rain":
                return json.dumps({"rain": todayrain})
          else:
             if weatherrequestelement == "rain":
               return todayrain
             else:
               return todayweather
        else:
            return todayweather
 
      if request[2] == "tomorrow":
        tomorrowweather = weatherrequest.tomorrowopenweathermap(latitude, longitude, weatherrequestelement, openweathermapapikey)
        datenow = datetime.now()
        tomorrow =  datenow + timedelta(days=1)
        datetomorrow = tomorrow.strftime('%Y-%m-%d')
        #try:
        gettomorowrain=None
        if not rc is None:
          key=str(latitude)+str(longitude)+str(datetomorrow)
          rediskeytomorrowrain = hashlib.md5(key.encode('utf-8')).hexdigest()
          gettomorrowrain = rc.get(rediskeytomorrowrain)
        if gettomorrowrain is None:
          tomorrowrain = weatherrequest.getrain(latitude, longitude, worldweatheronlineapikey, datetomorrow)
          if not rc is None:
            key=str(latitude)+str(longitude)+str(datetomorrow)
            rediskeytomorrowrain = hashlib.md5(key.encode('utf-8')).hexdigest()
            rc.set(rediskeytomorrowrain, tomorrowrain)
            rc.expire(rediskeytomorrowrain, 3600)
            syslog.syslog(syslog.LOG_DEBUG,"SET WEATHER RAIN TOMOROW IN REDIS")
        else:
          tomorrowrain = gettomorrowrain
          syslog.syslog(syslog.LOG_DEBUG,"FOUND WEATHER RAIN TOMOROW IN REDIS")
       # except:
       #   tomorrowrain = weatherrequest.getrain(latitude, longitude, worldweatheronlineapikey, datetomorrow)
        if weatherrequestelement != "all" or weatherrequestelement != "temperature" or weatherrequestelement != "weather":
          if format == "json":
              web.header('Content-Type', 'application/json')
              if weatherrequestelement == "humidity":
                return json.dumps({"humidity": tomorrowweather})
              if weatherrequestelement == "pressure":
                return json.dumps({"pressure": tomorrowweather})
              if weatherrequestelement == "windspeed":
                return json.dumps({"windspeed": tomorrowweather})
              if weatherrequestelement == "rain":
                return json.dumps({"rain": tomorrowrain})
          else:
            if weatherrequestelement == "rain":
              return tomorrowrain
            else:
              return tomorrowweather
        else:
           return tomorrowweather

"""
@api {get} /myip/:responsetype Display Public IP
@apiName GetMyPublicIP
@apiGroup Domogeek
@apiDescription Display your public IP
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     {"myip": "1.1.1.1"}

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/myip
     curl http://api.domogeek.fr/myip/json
"""
class myip:
  def GET(self,uri,ip=None):
    try:
      request = uri.split('/')
    except:
      pass
    try:
      format = request[1]
    except:
      format = None
    syslog.syslog(syslog.LOG_DEBUG,"request myip")  
    ip = web.ctx.env.get('HTTP_X_FORWARDED_FOR', web.ctx.get('ip', ''))
    for ip in ip.split(','):
      ip = ip.strip()
      try:
        socket.inet_aton(ip)
        if format == "json":
          web.header('Cache-control', 'public,max-age=0')
          web.header('Content-Type', 'application/json')
          return json.dumps({"myip": ip})
        else:
          web.header('Cache-control', 'public,max-age=0')
          return ip
      except socket.error:
        web.badrequest()
        pass

"""
@api {get} /season/:responsetype Display Current Season
@apiName GetSeason
@apiGroup Domogeek
@apiDescription Display current season 
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     {"season": "winter"}

@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/season
     curl http://api.domogeek.fr/season/json
"""
class season:
  def GET(self,uri):
    try:
      request = uri.split('/')
    except:
      pass
    try:
      format = request[1]
    except:
      format = None
    syslog.syslog(syslog.LOG_DEBUG,"request season")        
    today = datetime.today().timetuple().tm_yday
    spring = range(80, 172)
    summer = range(172, 264)
    autumn = range(264, 355)
    if today in spring:
      season = 'spring'
    elif today in summer:
      season = 'summer'
    elif today in autumn:
      season = 'autumn'
    else:
      season = 'winter'
    if format == "json":
      web.header('Content-Type', 'application/json')
      return json.dumps({"season": season})
    else:
      return season


"""
@api {get} /ejpedf/:date/:responsetype EJP EDF Status Request
@apiName GetEJP
@apiGroup Domogeek
@apiDescription Ask for EJP EDF Status
@apiParam {String} date  Ask for today or tomorrow {now|tomorrow}
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
HTTP/1.1 200 OK
{"ejp": "False"}

Return "True" : EJP day
Return "False": No EJP day
Return "ND"   : Non Specified

@apiErrorExample Error-Response:
HTTP/1.1 400 Bad Request
400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/ejpedf/now
     curl http://api.domogeek.fr/ejpedf/tomorrow
     curl http://api.domogeek.fr/ejpedf/now/json
"""
class ejpedf:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /ejpedf/{now | tomorrow}\n"
      try:
        format = request[1]
      except:
        format = None
      if request[0] == "now" or request[0] == "tomorrow":
        syslog.syslog(syslog.LOG_DEBUG,f"request ejpedf {request[0]}")
        EJPRedis = None
        key=f"ejp{request[0]}"
        redisKey =  hashlib.md5(key.encode('utf-8')).hexdigest()
        if not rc is None:
          EJPRedis = rc.get(redisKey)
        if EJPRedis is None:
          if request[0] == "now":
            result = ejprequest.getToday()
          elif request[0] == "tomorrow":
            result = ejprequest.getTomorrow()
          else:
            result = ["ERROR",""]
          if not rc is None and result[0] == "OK":
            rc.set(redisKey, result[1], 1800)
            rc.expire(redisKey,1800)
            syslog.syslog(syslog.LOG_DEBUG,f"Set '{key}' in REDIS: '{result[1]}'")
        else:
          result = ["OK",""]
          result [1] = EJPRedis.decode("UTF-8")
          syslog.syslog(syslog.LOG_DEBUG,f"Found '{key}' in REDIS: 'result[1]'")
        if format == "json":
          web.header('Content-Type', 'application/json')
          if result[0] == "OK":
            return json.dumps({"ejp": result[1]})
          else:
            return json.dumps({"ejp": result[0]})
        else:
          if result[0] == "OK":
            return result[1]
          else:
            return result[0]
      # Other case
      web.badrequest()
      return "Incorrect request : /ejpedf/{now | tomorrow}\n"


"""
@api {get} /feastedsaint/:date/:responsetype Feasted Day of Saint Request
@apiName GetFeastedSaintDay
@apiGroup Domogeek
@apiDescription Ask to know feasted Saint for :date or date for :name
@apiParam {String} now  Ask for today.
@apiParam {String} tomorrow  Ask for tomorrow.
@apiParam {String} name  Search feasted saint day for name.
@apiParam {Datetime} D-M  Ask for specific date.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
     HTTP/1.1 200 OK
     Guillaume
     10-1
@apiErrorExample Error-Response:
     HTTP/1.1 400 Bad Request
     400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/feastedsaint/guillaume
     curl http://api.domogeek.fr/feastedsaint/now
     curl http://api.domogeek.fr/feastedsaint/now/json
     curl http://api.domogeek.fr/feastedsaint/1-5
     curl http://api.domogeek.fr/feastedsaint/2-12/json

"""
class feastedsaint:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /feastedsaint/{now|tomorrow|date(D-M)|name}\n"
      try:
        format = request[1]
      except:
        format = None
      if request[0] == "now":
        syslog.syslog(syslog.LOG_DEBUG,"request feastedsaint %s " % request[0])  
        datenow = datetime.now()
        month = datenow.month
        day = datenow.day
        result=None
        #try REDIS
        if not rc is None:
          todayrequest = str(day)+"-"+str(month)
          key=todayrequest+"feastedsaint"
          rediskeyfeastedsaint = hashlib.md5(key.encode('utf-8')).hexdigest()
          result = rc.get(rediskeyfeastedsaint).decode("UTF-8")
        #try local cache
        if uselocalcache and result is None:
          todayrequest = str(day)+"-"+str(month)
          key="feastedsaint|"+todayrequest
          result = config.get("cache", key, fallback=None)
        if result is None:
          result = "N/A"
        result=result.replace(",", ", ").replace("  "," ")
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"feastedsaint": result})
        else:
          return result
      if request[0] == "tomorrow":
        syslog.syslog(syslog.LOG_DEBUG,"request feastedsaint %s " % request[0])  
        datenow = datetime.now()
        datetomorrow = datenow + timedelta(days=1)
        month = datetomorrow.month
        day = datetomorrow.day
        result=None
        #try redis
        if not rc is None:
          todayrequest = str(day)+"-"+str(month)
          key=todayrequest+"feastedsaint"
          rediskeyfeastedsaint = hashlib.md5(key.encode('utf-8')).hexdigest()
          result = rc.get(rediskeyfeastedsaint).decode("UTF-8")
        #try local cache
        if uselocalcache and result is None:
          todayrequest = str(day)+"-"+str(month)
          key="feastedsaint|"+todayrequest
          result = config.get("cache", key, fallback=None)          
        if result is None:
          result = "N/A"          
        result=result.replace(",", ", ").replace("  "," ")  
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"feastedsaint": result})
        else:
          return result

      if request[0] != "now" and request[0] != "tomorrow":
        try:
          daterequest = request[0]
          result = daterequest.split('-')
          day = int(result[0])
          month = int(result[1])
        except:
          syslog.syslog(syslog.LOG_DEBUG,"request feastedsaint %s" % request[0])  
          namerequest = request[0]
          namesearch = namerequest.lower()
          result=None
          if not rc is None:
            key=namesearch+"feastedsaint"
            rediskeynamefeastedsaint = hashlib.md5(key.encode('utf-8')).hexdigest()
            result = rc.get(rediskeynamefeastedsaint).decode("UTF-8")
          if result is None or result == "None":
            result = "no name found (%s)" % namesearch
          if format == "json":
            web.header('Content-Type', 'application/json')
            return json.dumps({"feastedsaint": result})
          else:
            return result
        if day > 31 or month > 12:
          web.badrequest()
          return "Incorrect date format : D-M\n"
        todayrequest = str(day)+"-"+str(month)
        syslog.syslog(syslog.LOG_DEBUG,"request feastedsaint %s" % todayrequest)  
        result=None
        if not rc is None:
          key=todayrequest+"feastedsaint"
          rediskeyfeastedsaint = hashlib.md5(key.encode('utf-8')).hexdigest()
          result = rc.get(rediskeyfeastedsaint).decode("UTF-8")
        if result is None or result == "None":
          result = "N/A"
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"feastedsaint": result})
        else:
          return result

"""
@api {get} /ecowattedf/:date/:responsetype Ecowatt EDF color Request
@apiName GetEcoWatt
@apiGroup Domogeek
@apiDescription Ask the EDF EcoWatt color
@apiParam {String} now Ask for today.
@apiParam {String} tomorrow Ask for tomorrow.
@apiParam {String} [responsetype]  Specify Response Type (raw by default or specify json, only for single element).
@apiSuccessExample Success-Response:
HTTP/1.1 200 OK
Content-Type: application/json
Transfer-Encoding: chunked
Date: Thu, 03 Jul 2014 17:16:47 GMT
Server: localhost
{"color": "Vert"}

@apiErrorExample Error-Response:
HTTP/1.1 400 Bad Request
400 Bad Request

@apiExample Example usage:
     curl http://api.domogeek.fr/ecowattedf/now
     curl http://api.domogeek.fr/ecowattedf/now/json
     curl http://api.domogeek.fr/ecowattedf/tomorrow
     curl http://api.domogeek.fr/ecowattedf/tomorrow/json

"""

class ecowattedf:
    def GET(self,uri):
      request = uri.split('/')
      if request == ['']:
        web.badrequest()
        return "Incorrect request : /ecowattedf/{now | tomorrow}\n"
      try:
        format = request[1]
      except:
        format = None
      if request[0] == "now":
        syslog.syslog(syslog.LOG_DEBUG,"request ecowattedf %s" % request[0])
        getecowattnow = None
        if not rc is None:
          key="ecowattnow"
          rediskeyecowattnow =  hashlib.md5(key.encode('utf-8')).hexdigest()
          getecowattnow = rc.get(rediskeyecowattnow)          
        if getecowattnow is None:
          result = ecowattrequest.EcoWattToday()
          if not rc is None:
            key="ecowattnow"
            rediskeyecowattnow =  hashlib.md5(key.encode('utf-8')).hexdigest()
            rc.set(rediskeyecowattnow, result, 1800)
            rc.expire(rediskeyecowattnow ,1800)
            syslog.syslog(syslog.LOG_DEBUG,"SET ECOWATT NOW IN REDIS: '%s'" % result)
        else:
          result = getecowattnow.decode("UTF-8")
          syslog.syslog(syslog.LOG_DEBUG,"FOUND ECOWATT NOW IN REDIS: '%s'" % result)
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"color": result})
        else:
          return result
      if request[0] == "tomorrow":
        syslog.syslog(syslog.LOG_DEBUG,"request ecowattedf %s" % request[0])
        getecowatttomorrow = None
        if not rc is None:
          key="ecowatttomorrow"
          rediskeyecowatttomorrow =  hashlib.md5(key.encode('utf-8')).hexdigest()
          getecowatttomorrow = rc.get(rediskeyecowatttomorrow)
        if getecowatttomorrow is None:
          result = ecowattrequest.EcoWattTomorrow()
          if not rc is None:
            key="ecowatttomorrow"
            rediskeyecowatttomorrow =  hashlib.md5(key.encode('utf-8')).hexdigest()
            rc.set(rediskeyecowatttomorrow, result, 1800)
            rc.expire(rediskeyecowatttomorrow ,1800)
            syslog.syslog(syslog.LOG_DEBUG,"SET ECOWATT TOMORROW IN REDIS: '%s'" % result)
        else:
          result = getecowatttomorrow.decode("UTF-8")
          syslog.syslog(syslog.LOG_DEBUG,"FOUND ECOWATT TOMORROW IN REDIS: '%s'" % result)
        if format == "json":
          web.header('Content-Type', 'application/json')
          return json.dumps({"color": result})
        else:
          return result
      web.badrequest()
      return "Incorrect request : /ecowattedf/{now | tomorrow}\n"


class MyDaemon(Daemon):
    def run(self):
      syslog.syslog(syslog.LOG_INFO, "APIDOMOGEEK app listening on %s" % sys.argv[1])
      app.run(webLog)
      
if __name__ == "__main__":
  service = MyDaemon('/tmp/apidomogeek.pid')
  listenip = config.get("nosection", "listenip", fallback="192.168.130.1")
  listenport = config.getint("nosection", "listenport", fallback=8080)
  if len(sys.argv) >= 2:
    if 'start' == sys.argv[1]:
      syslog.syslog(syslog.LOG_INFO, "Starting apidomogeek deamon...")
      sys.argv[1] =  listenip+':'+str(listenport)
      service.start()
    elif 'stop' == sys.argv[1]:
      syslog.syslog(syslog.LOG_INFO, "Stoping apidomogeek deamon...")
      service.stop()
    elif 'restart' == sys.argv[1]:
      syslog.syslog(syslog.LOG_INFO, "Restarting apidomogeek deamon...")
      service.restart()
    elif 'console' == sys.argv[1]:
      syslog.syslog(syslog.LOG_INFO, "Starting apidomogeek in console mode...")
      sys.argv[1] =  listenip+':'+str(listenport)
      service.console()
    elif 'test' == sys.argv[1]:  
      if len(sys.argv) == 2:
        print ("usage: %s test EJPToday|EJPTomorrow|TempoToday|TempoTomorow|Vigilance xx|EcoWattToday" % sys.argv[0])
        sys.exit(2)
      print("MODE TEST: %s" % sys.argv[2])
      if 'EJPToday' == sys.argv[2]:  
        print(ejprequest.getToday())
      elif 'EJPTomorrow' == sys.argv[2]:  
        print(ejprequest.getTomorrow())        
      elif 'TempoToday' == sys.argv[2]:  
        print(temporequest.getToday())        
      elif 'TempoTomorow' == sys.argv[2]:  
        print(temporequest.getTomorrow())        
      elif 'Vigilance' == sys.argv[2]:  
        print(vigilancerequest.getVigilance(sys.argv[3]))          
      elif 'EcoWattToday' == sys.argv[2]:  
        print(ecowattrequest.EcoWattToday())          
    else:
      print ("%s: Unknown command" % (sys.argv[1]))
      sys.exit(2)
  else:
    print ("usage: %s start|stop|restart|console|test" % sys.argv[0])
    sys.exit(2)
    
   
