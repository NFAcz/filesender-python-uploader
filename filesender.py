#!/usr/bin/env python3
#
# FileSender www.filesender.org
#
# Copyright (c) 2009-2019, AARNet, Belnet, HEAnet, SURFnet, UNINETT
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# *   Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
# *   Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
# *   Neither the name of AARNet, Belnet, HEAnet, SURFnet and UNINETT nor the
#     names of its contributors may be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import requests
import time
from collections.abc import Iterable
from collections.abc import MutableMapping
import hmac
import hashlib
import urllib3
import os
import json
import configparser
from os.path import expanduser
import queue
import threading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

parser = argparse.ArgumentParser()
parser.add_argument('files', help='path to file(s) to send', nargs='+')
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-p', '--progress', action='store_true')
parser.add_argument('-u', '--username', default=os.getenv('FILESENDER_USER_NAME', 'user'))
parser.add_argument('-e', '--email', default=os.getenv('FILESENDER_USER_EMAIL', 'user@example.org'))
parser.add_argument('-r', '--recipients', default=os.getenv('FILESENDER_RECIPIENTS', 'user@example.org'))
parser.add_argument('-a', '--apikey', default=os.getenv('FILESENDER_USER_APIKEY', 'TESTAPIKEY'))
parser.add_argument('-b', '--baseurl', default=os.getenv('FILESENDER_BASEURL', 'localhost'))
parser.add_argument('-d', '--days', type=int, default=os.getenv('FILESENDER_EXPIRE_DAYS', 10))
parser.add_argument('-s', '--subject')
parser.add_argument('-m', '--message')
args = parser.parse_args()

  
#configs
response = requests.get(args.baseurl+'/info', verify=False)
upload_chunk_size = response.json()['upload_chunk_size']

if args.verbose:
  print('baseurl          : '+args.baseurl)
  print('username          : '+args.username)
  print('email             : '+args.email)
  print('apikey            : '+args.apikey)
  print('upload_chunk_size : '+str(upload_chunk_size)+' bytes')
  print('recipients        : '+args.recipients)
  print('files             : '+','.join(args.files))

##########################################################################

def flatten(d, parent_key=''):
  items = []
  for k, v in d.items():
    new_key = parent_key + '[' + k + ']' if parent_key else k
    if isinstance(v, MutableMapping):
      items.extend(flatten(v, new_key).items())
    else:
      items.append(new_key+'='+v)
  items.sort()
  return items

def call(method, path, data, content=None, rawContent=None, options={}):
  data['remote_user'] = args.username
  data['timestamp'] = str(round(time.time()))
  flatdata=flatten(data)
  signed = bytes(method+'&'+args.baseurl.replace('https://','',1).replace('http://','',1)+path+'?'+('&'.join(flatten(data))), 'ascii')

  content_type = options['Content-Type'] if 'Content-Type' in options else 'application/json'

  inputcontent = None
  if content is not None and content_type == 'application/json':
    inputcontent = json.dumps(content,separators=(',', ':'))
    signed += bytes('&'+inputcontent, 'ascii')
  elif rawContent is not None:
    inputcontent = rawContent
    signed += bytes('&', 'ascii')
    signed += inputcontent

  bkey = bytearray()
  bkey.extend(map(ord, args.apikey))
  data['signature'] = hmac.new(bkey, signed, hashlib.sha1).hexdigest()

  url = args.baseurl+path+'?'+('&'.join(flatten(data)))
  headers = {
    'Accept': 'application/json',
    'Content-Type': content_type
  }
  response = None
  if method == 'get':
    response = requests.get(url, verify=False, headers=headers)
  elif method == 'post':
    response = requests.post(url, data=inputcontent, verify=False, headers=headers)
  elif method == 'put':
    response = requests.put(url, data=inputcontent, verify=False, headers=headers)
  elif method == 'delete':
    response = requests.delete(url, verify=False, headers=headers)

  if response is None:
    raise Exception('Client error')

  code = response.status_code

  if code!=200:
    if method!='post' or code!=201:
      raise Exception('Http error '+str(code)+' '+response.text)

  if response.text=='':
    raise Exception('Http error '+str(code)+' Empty response')

  if method!='post':
    return response.json()

  r = {}
  r['location']=response.headers['Location']
  r['created']=response.json()
  return r

def postTransfer(user_id, files, recipients, subject=None, message=None, expires=None, options=[]):

  if expires is None:
    expires = round(time.time()) + (args.days*24*3600)

  to = [x.strip() for x in recipients.split(',')]
  
  return call(
    'post',
    '/transfer',
    {},
    {
      'from': user_id,
      'files': files,
      'recipients': to,
      'subject': subject,
      'message': message,
      'expires': expires,
      'aup_checked':1,
      'options': options
    },
    None,
    {}
  )

def putChunk(f, chunk, offset):
  return call(
    'put',
    '/file/'+str(f['id'])+'/chunk/'+str(offset),
    { 'key': f['uid'] },
    None,
    chunk,
    { 'Content-Type': 'application/octet-stream' }
  )

def fileComplete(f):
  return call(
    'put',
    '/file/'+str(f['id']),
    { 'key': f['uid'] },
    { 'complete': True },
    None,
    {}
  )

def transferComplete(transfer):
  return call(
    'put',
    '/transfer/'+str(transfer['id']),
    { 'key': transfer['files'][0]['uid'] },
    { 'complete': True },
    None,
    {}
  )

def deleteTransfer(transfer):
  return call(
    'delete',
    '/transfer/'+str(transfer['id']),
    { 'key': transfer['files'][0]['uid'] },
    None,
    None,
    {}
  )

##########################################################################

#postTransfer
if args.verbose:
  print('postTransfer')

files = {}
filesTransfer = []
for f in args.files:
  fn_abs = os.path.abspath(f)
  fn = os.path.basename(fn_abs)
  size = os.path.getsize(fn_abs)

  files[fn+':'+str(size)] = {
    'name':fn,
    'size':size,
    'path':fn_abs
  }
  filesTransfer.append({'name':fn,'size':size})

troptions = {'get_a_link':0}


transfer = postTransfer( args.email,
                         filesTransfer,
                         args.recipients,
                         subject=args.subject,
                         message=args.message,
                         expires=None,
                         options=troptions)['created']

def worker():
  while True:
    item = q.get()
    if not item:
      break
    f = item[0]
    offset = item[1]
    with open(path, mode='rb', buffering=0) as fin:
      fin.seek(offset)
      data = fin.read(upload_chunk_size)
      putChunk(f, data, offset)
    global percent_done
    if args.progress:
      num_parts = size / upload_chunk_size
      cur_part = offset / upload_chunk_size
      cur_percent_done = round(cur_part / num_parts * 100)
      if cur_percent_done > percent_done:
        print('{0}, {1}%'.format(path, percent))
    percent_done = cur_percent
    q.task_done()

try:
  for f in transfer['files']:
    path = files[f['name']+':'+str(f['size'])]['path']
    size = files[f['name']+':'+str(f['size'])]['size']
    #putChunks
    q = queue.Queue()
    threads = []
    num_worker_threads = 30
    global percent_done
    percent_done = 0
    for i in range(num_worker_threads):
      t = threading.Thread(target=worker)
      t.start()
      threads.append(t)

    if args.verbose:
      print('putChunks: '+path)

    for offset in range(0,size,upload_chunk_size):
      q.put((f, offset))

    # block until all tasks are done
    q.join()

    # stop workers
    for i in range(num_worker_threads):
      q.put(None)
    for t in threads:
      t.join()

    #fileComplete
    if args.verbose:
      print('fileComplete: '+path)
    fileComplete(f)


  #transferComplete
  if args.verbose:
    print('transferComplete')
  transferComplete(transfer)
  if args.progress:
    print('Upload Complete')

except Exception as inst:
  print(type(inst))
  print(inst.args)
  print(inst)

  #deleteTransfer
  if args.verbose:
    print('deleteTransfer')
  deleteTransfer(transfer)

