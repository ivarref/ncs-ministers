#!/usr/bin/python
# -*- coding: utf-8 -*-

import locale
import time
import sys
import datetime
from datetime import timedelta
from decimal import Decimal
import codecs

# notes: All dates stored here have month (January) which start at 01

locale.setlocale(locale.LC_ALL, 'en_US')

def get_url(url, filename):
  import urllib2
  import os

  if not os.path.exists('cache'):
    os.makedirs('cache')

  if not os.path.isfile(filename):
    with codecs.open(filename, encoding='utf-8', mode='w') as fd:
      print "Creating cache %s for %s ..." % (filename, url)
      response = urllib2.urlopen(url)
      fd.write(response.read().decode('utf-8-sig'))
      print "Created cache %s for %s" % (filename, url)
  
  with open(filename, 'r') as fd:
    return fd.read().decode('utf-8')

def verify_and_assign(values, data):
  if data[0] != values:
    print "Failure. Expected %s, but got %s.\nCSV format must have changed!" % (values, data)
    sys.exit(-1)
  return tuple([idx for (idx, x) in enumerate(values.split(","))])

timeformat = '%d %B %Y'

#TODO maybe parse http://en.wikipedia.org/wiki/List_of_heads_of_government_of_Norway ?

date_to_ministers = {}
minister_to_reserve = {}

def define(who, periods):
  who = who.split('/')[-1].replace('_', ' ')
  sep = ' – '
  periods = [x.strip() for x in periods.split('\n') if x.strip()!='']
  if who not in minister_to_reserve:
    minister_to_reserve[who] = { 'gas' : Decimal(0), 'oe' : Decimal(0), 'oil' : Decimal(0), 'days_ruling' : 0 }

  for x in periods:
    parts = x.split(sep)
    if len(parts) != 2:
      print "Bad data. Period was: "
      print x
      sys.exit(-1)
    else:
      dato = datetime.datetime.strptime(parts[0], timeformat)
      stopperiod = datetime.datetime.strptime(parts[1], timeformat)
      if stopperiod <= dato:
        print "Shouldn't happen."
        sys.exit(-1)

      while dato <= stopperiod:
        datestr = dato.strftime("%Y-%m")
        minister_to_reserve[who]['days_ruling'] += 1

        if datestr not in date_to_ministers:
          date_to_ministers[datestr] = []
        if who not in date_to_ministers[datestr]:
          date_to_ministers[datestr].append(who)
        dato = dato + timedelta(days=1)
  pass

import ministers
ministers.add_ministers(define)

def npdid_to_reserves():
  reserves_url_csv = 'http://factpages.npd.no/ReportServer?/FactPages/TableView/field_reserves&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&rs:Format=CSV&Top100=false&IpAddress=84.208.160.74&CultureCode=en'
  reserves = [x.strip() for x in get_url(reserves_url_csv, 'cache/reserves.csv').split("\n") if x.strip() != ""]
  values = "fldName,fldRecoverableOil,fldRecoverableGas,fldRecoverableNGL,fldRecoverableCondensate,fldRecoverableOE,fldRemainingOil,fldRemainingGas,fldRemainingNGL,fldRemainingCondensate,fldRemainingOE,fldDateOffResEstDisplay,fldNpdidField,DatesyncNPD"
  if reserves[0] != values:
    print "CSV format changed."
    sys.exit(-1)
  (fldName,fldRecoverableOil,fldRecoverableGas,fldRecoverableNGL,fldRecoverableCondensate,fldRecoverableOE,fldRemainingOil,fldRemainingGas,fldRemainingNGL,fldRemainingCondensate,fldRemainingOE,fldDateOffResEstDisplay,fldNpdidField,DatesyncNPD) = tuple([idx for (idx, x) in enumerate("fldName,fldRecoverableOil,fldRecoverableGas,fldRecoverableNGL,fldRecoverableCondensate,fldRecoverableOE,fldRemainingOil,fldRemainingGas,fldRemainingNGL,fldRemainingCondensate,fldRemainingOE,fldDateOffResEstDisplay,fldNpdidField,DatesyncNPD".split(","))])
  reserves = [x.split(",") for x in reserves[1:] if x.strip() != ""]
  reserves_map = {}
  for reserve in reserves:
    oil = Decimal(reserve[fldRecoverableOil])
    gas = Decimal(reserve[fldRecoverableGas])
    ngl = Decimal(reserve[fldRecoverableNGL])
    con = Decimal(reserve[fldRecoverableCondensate])
    oe = oil + gas + ngl + con
    reserves_map[reserve[fldNpdidField]] = (oil, gas, oe)
  return reserves_map

def npdid_to_start_production_date():
  # Field -> Production -> Monthly by field
  data = [x.strip() for x in get_url('http://factpages.npd.no/ReportServer?/FactPages/TableView/field_production_monthly&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&rs:Format=CSV&Top100=false&IpAddress=84.208.153.159&CultureCode=en', 'cache/field_production_monthly_by_field.csv').split('\n') if x.strip() != '']
  firstline = "prfInformationCarrier,prfYear,prfMonth,prfPrdOilNetMillSm3,prfPrdGasNetBillSm3,prfPrdNGLNetMillSm3,prfPrdCondensateNetMillSm3,prfPrdOeNetMillSm3,prfPrdProducedWaterInFieldMillSm3,prfNpdidInformationCarrier"
  (prfInformationCarrier,prfYear,prfMonth,prfPrdOilNetMillSm3,prfPrdGasNetBillSm3,prfPrdNGLNetMillSm3,prfPrdCondensateNetMillSm3,prfPrdOeNetMillSm3,prfPrdProducedWaterInFieldMillSm3,prfNpdidInformationCarrier) = verify_and_assign(firstline, data)
  data = data[1:]
  seen_fields = []
  result = {}
  for line in data:
    line = line.split(',')
    fieldName = line[prfInformationCarrier]
    if fieldName not in seen_fields:
      seen_fields.append(fieldName)
      datestr = "%s-%02d" % (line[prfYear], int(line[prfMonth]))
      if datestr not in date_to_ministers:
        print "bad data..."
        sys.exit(-1)
      else:
        if len(date_to_ministers[datestr]) > 1:
          print "WARN :: Skipping field %s which was split by ministers '%s'" % (fieldName, str(date_to_ministers[datestr]))
        else:
          result[line[prfNpdidInformationCarrier]] = datestr
      #print "%s => %s %02d" % (fieldName, line[prfYear], int(line[prfMonth]))
      pass
  return result

to_date = npdid_to_start_production_date()
to_reserve = npdid_to_reserves()

for npdid in to_date.keys():
  if npdid not in to_reserve:
    print "WARN skipping npdid " + npdid
    continue # skip 33/9-6 DELTA because it's STILL not in NPD reserves...
  dato = to_date[npdid]
  minister = date_to_ministers[dato][0]
  reserve = to_reserve[npdid]
  minister_to_reserve[minister]['oil'] += reserve[0]
  minister_to_reserve[minister]['gas'] += reserve[1]
  minister_to_reserve[minister]['oe'] += reserve[2]

for minister in minister_to_reserve.keys():
  res =  minister_to_reserve[minister]
  def f(x):
    return x * Decimal("6.29") / Decimal(1000.0)

  print "During %s reign (%d days) %.2f Gb of oil, %.2f Gboe of gas and %.2f Gboe of All Petroleum started producing." % ((minister+"'s").ljust(30), res['days_ruling'], f(res['oil']), f(res['gas']), f(res['oe']))

for k in date_to_ministers.keys():
  if len(date_to_ministers[k]) > 1:
    #print "%s => %s" % (k, str(date_to_ministers[k]))
    pass
  
