import sys
from flask import escape
import json
import urllib.request
from datetime import datetime
import ssl
import numpy as np
from google.cloud import storage
import requests

def extract_source(request):

  today = str(datetime.today().strftime('%Y-%m-%d-%H:%M:%S'))
  print(today)

  mailgun_key = "key-*"

  ssl._create_default_https_context = ssl._create_unverified_context

  headers = {}
  headers['User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0"

  source_url = "https://radarcovid19.jatimprov.go.id/"
  req = urllib.request.Request(source_url, headers = headers)
  with urllib.request.urlopen( req ) as url:
    source_string = url.read().decode('utf-8')
  
  if(source_string == ""):
    print("no content fetched from website.")
    exit
  
  string_marker = "var datapositiflatlon="
  lines = source_string.split("\n")
  line_cnt = 0
  rawJSON = ""
  for line in lines:
    line_cnt+=1
    if(line.startswith(string_marker)):
      print(line_cnt)
      rawJSON = line.replace(string_marker, "")
      rawJSON = rawJSON[:-1]
      break

  cases = json.loads( rawJSON )

  for count, case in enumerate(cases):
    if(case['lat'] == '' or case['lon'] == ''):
      continue
    
    case['lat'] = case['lat'].strip().replace(",", ".")
    case['lon'] = case['lon'].strip().replace(",", ".")

    cases[count] = case

  # source_file_name = "/tmp/" + today + ".json"
  # source_file_name = "" + today + ".json"
  # file = open( source_file_name, "w+" )
  # file.write( json.dumps(cases) )
  # file.close()

  # storage_client = storage.Client()
  # bucket_name = "cctv-malangkota-logger"

  # destination_blob_name =  today + ".json"
  # bucket = storage_client.bucket(bucket_name)
  # blob = bucket.blob(destination_blob_name)
  # blob.upload_from_filename(source_file_name)

  total_cases = len(cases)

  locations = {"Home": [-7.987851, 112.617932], "Park": [-7.982769, 112.630797]}

  emailText = "COVID19 Radar sources has been checked with {} total cases.\n".format(total_cases)

  for key in locations:
    # current_location = [-7.371910, 112.78816]
    current_location = locations[key]
    current_case = 0

    print("Checking {}\n".format(key))

    cases_within_range = get_cases_with_ranges(current_location, cases, 5)

    case_types = {}
    for case in cases_within_range:
      if case['status_pasien'] not in case_types:
        case_types.update( { case['status_pasien']: 0 } )
      
      case_types.update( { case['status_pasien']: case_types[case['status_pasien']]+1 } )
      current_case += 1

    emailText += "There are {} total cases near {}:\n".format(current_case, key)
    emailText += "".join([" -%s: %s\n" % (key, value) for (key, value) in case_types.items()])



  requests.post(
  "https://api.mailgun.net/v3/send.freelancer.web.id/messages",
  auth=("api", mailgun_key),
  data={"from": "COVID19 Mailer <noreply@send.freelancer.web.id>",
    "to": ["ariefbayu@gmail.com"],
    "subject": "Daily COVID19 Log [{}]".format(total_cases),
    "text": emailText})

  #send something to browser
  #so that it know the page is working fine
  return "ok"

def get_cases_with_ranges(target, list_of_cases, range):
  result = []
  for case in list_of_cases:
    case_lat = 0.0
    try:
      case_lat = float(case['lat'])
    except ValueError:
      case_lat = 0.0
    case_lon = 0.0
    try:
      case_lon = float(case['lon'])
    except ValueError:
      case_lon = 0.0
    
    if(get_distance(target[0], target[1], case_lat, case_lon) < range):
      result.append(case)
  
  return result

def get_distance(lat1, lon1, lat2, lon2):
  earth_radius = 6371 #value in KM, change to 3959 for mile calculation
  
  dLat = np.radians(lat2 - lat1)
  dLon = np.radians(lon2 - lon1)

  a = np.sin(dLat/2) \
      * np.sin(dLat/2) \
      + np.cos(np.radians(lat1)) \
      * np.cos(np.radians(lat2)) \
      * np.sin(dLon/2) \
      * np.sin(dLon/2)
  c = 2 * np.arcsin(np.sqrt(a))
  d = earth_radius * c

  return d