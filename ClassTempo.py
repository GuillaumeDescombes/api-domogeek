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

class EDFTempo:

  def TempoDate(self, dateTempo):
    try:
      page = urllib.request.urlopen('https://particulier.edf.fr/services/rest/referentiel/searchTempoStore?dateRelevant='+dateTempo)
    except:
      syslog.syslog(syslog.LOG_ERR, "Tempo: cannot get Tempo data")
      return None
    try:
      response = json.load(page)
    except:
      syslog.syslog(syslog.LOG_ERR, "Tempo: data format is incorrect")
      return "NON_DEFINI"
    try:
      colortoday = response['couleurJourJ']
      return colortoday.replace("TEMPO_","").title()
    except:
      pass
    return "NON_DEFINI"

  def TempoToday(self):
    now = datetime.datetime.now()
    today= now.strftime("%Y-%m-%d")
    return self.TempoDate(today)

  def TempoTomorrow(self):
    now = datetime.datetime.now()
    datetomorrow = now + datetime.timedelta(days=1)
    tomorrow = datetomorrow.strftime("%Y-%m-%d")
    return self.TempoDate(tomorrow)
