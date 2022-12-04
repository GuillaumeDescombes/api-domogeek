#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Gruik coded by GuiguiAbloc
# http://blog.guiguiabloc.fr
# Rewritten by Guillaume Descombes
# 2022.12.04
#

import urllib.request, urllib.error
import sys
import json
import datetime
import syslog

class EDFejp:

  def EJPDate(self, dateEJP):
    try:
      req = urllib.request.Request(
        "https://particulier.edf.fr/services/rest/referentiel/historicEJPStore", 
        data=None, 
        headers={
            'User-Agent': 'wget'
        }
      )
      html = urllib.request.urlopen(req)
    except:
      syslog.syslog(syslog.LOG_ERR, "EJP: cannot get EJP data")
      return None
    try:
      rep = json.load(html)
    except:
      syslog.syslog(syslog.LOG_ERR, "EJP: data format is incorrect")
      return "False"
    try:
      listEjp = rep["listeEjp"]
      for i in listEjp:
        dTS=int (i["dateApplication"] / 1000)
        dEJP=datetime.date.fromtimestamp(dTS).strftime("%Y-%m-%d")
        s=i["statut"]
        syslog.syslog(syslog.LOG_DEBUG, "Historic EJP date: %s" % dEJP)
        if dEJP == dateEJP:
          return "True"
    except:
       syslog.syslog(syslog.LOG_ERR, "EJP: data format is incorrect")
       pass
    return "False"

  def EJPToday(self):
    now = datetime.datetime.now()
    today= now.strftime("%Y-%m-%d")
    return self.EJPDate(today)
    
  def EJPTomorrow(self):
    now = datetime.datetime.now()
    datetomorrow = now + datetime.timedelta(days=1)
    tomorrow = datetomorrow.strftime("%Y-%m-%d")
    return self.EJPDate(tomorrow)

