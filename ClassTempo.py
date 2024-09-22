#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Gruik coded by GuiguiAbloc
# http://blog.guiguiabloc.fr
# Rewritten by Guillaume Descombes
# V1 2022.12.04
# V2 2024.09.22 - new url https://www.domotique-fibaro.fr/topic/16022-quickapp-suivi-abonnement-tempo-edf/page/4/

import requests
import sys
import json
import datetime
import time
import syslog

class EDFTempo:

  def __init__(self):
    self.EDFoptions = {
            'verify': False,
            'timeout': 5,
            'headers': {
                'Host': 'api-commerce.edf.fr',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
                'Referer': 'https://particulier.edf.fr/',
                'content-type': 'application/json',
                'Situation-Usage': 'Jours Effacement',
                'Application-Origine-Controlee': 'site_RC',
                'Origin': 'https://particulier.edf.fr',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'same-site',
                'Connection': 'keep-alive',
                'TE': 'trailers',
                'Priority': 'u=4',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache'
            }
    }
    requests.packages.urllib3.disable_warnings()

  def __getTempoDate(self, dateTempo):
    try:
      # Current time
      self.EDFoptions['headers']['X-Request-Id'] = str(int(time.time())) + '460'
      sDate2 = (dateTempo + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
      sDate1 = (dateTempo).strftime("%Y-%m-%d")
      #Create URL
      url = f"https://api-commerce.edf.fr/commerce/activet/v1/calendrier-jours-effacement?option=TEMPO&dateApplicationBorneInf={sDate1}"
      url = url + f"&dateApplicationBorneSup={sDate2}&identifiantConsommateur=src"
      response = requests.get(url, **self.EDFoptions)
    except:
      syslog.syslog(syslog.LOG_ERR, "Tempo: cannot get Tempo data")
      return ["ERROR", ""]
    try:
      webData = response.json()
    except:
      syslog.syslog(syslog.LOG_ERR, "Tempo: JSON format is incorrect")
      return ["ERROR", ""]
    try:
      calendarTempo = webData['content']['options'][0]['calendrier']
      for dateTempo in calendarTempo:
        if dateTempo['dateApplication'] == sDate1:
          colorDate = dateTempo['statut']
          colorDate = colorDate.replace("TEMPO_","").title()
          return ["OK", colorDate]
    except:
      return ["ERROR", ""]
    return ["UNDEFINED", ""]

  def getToday(self):
    today = datetime.datetime.now()
    return self.__getTempoDate(today)

  def getTomorrow(self):
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    return self.__getTempoDate(tomorrow)


if __name__ == "__main__":
  #Test for today
  tempoRequest = EDFTempo()
  tempoResponse=tempoRequest.getToday()
  print(f"Today - response: {tempoResponse}")
  #Test for tomorow
  tempoResponse=tempoRequest.getTomorrow()
  print(f"Tomorrow - response: {tempoResponse}")
