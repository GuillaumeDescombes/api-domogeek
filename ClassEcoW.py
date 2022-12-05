#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Guillaume Descombes
# 2022.12.04
#

import urllib.request, urllib.error
import sys
import json
import datetime
import syslog

#https://data.rte-france.com/documents/20182/224298/FR_GU_API_Ecowatt_v04.00.01.pdf

class EDFEcoWatt:
    
  def __getColor(self, number):
    if number == 1:
      return "vert"
    if number == 2:
      return "orange"
    if number == 3:
      return "rouge"
    return "non défini"
  

  def EcoWattDate(self, dateEW):
    try:
      req = urllib.request.Request(
        "https://particulier.edf.fr/content/dam/2-Actifs/Scripts/ecowattSignal.json", 
        data=None, 
        headers={
            'User-Agent': 'wget'
        }
      )
      html = urllib.request.urlopen(req)
    except:
      syslog.syslog(syslog.LOG_ERR, "EcoWatt: cannot get EcoWatt data")
      return "non défini"
    try:
      rep = json.load(html)
    except:
      syslog.syslog(syslog.LOG_ERR, "EcoWatt: JSON format is incorrect")
      return "non défini"
    try:
      listEW = rep["signals"]
      for i in listEW:
        dTxt=i["jour"]
        dNorm=datetime.datetime.fromisoformat(dTxt).strftime("%Y-%m-%d")
        EWValue=i["dvalue"]
        syslog.syslog(syslog.LOG_DEBUG, "EcoWatt %s: %s" % (dNorm,EWValue))
        if dNorm == dateEW:
          return self.__getColor(EWValue).title()
    except:
       syslog.syslog(syslog.LOG_ERR, "EcoWatt: data format is incorrect")
       traceback.print_exc()
       pass
    return "non défini"

  def EcoWattToday(self):
    now = datetime.datetime.now()
    today= now.strftime("%Y-%m-%d")
    return self.EcoWattDate(today)
    
  def EcoWattTomorrow(self):
    now = datetime.datetime.now()
    datetomorrow = now + datetime.timedelta(days=1)
    tomorrow = datetomorrow.strftime("%Y-%m-%d")
    return self.EcoWattDate(tomorrow)

