# filesender-python-uploader

This repo contains a python script to upload files via [Filesender](https://filesender.org/) API.

It is a fork of an example [script](https://github.com/filesender/filesender/blob/893286587656d4bb7c413cbd4c40fca59f710e09/scripts/client/filesender.py) from project's GIT repository, which contains following features compared to the original version:
- multi-threaded upload
- replaced file-based configuration with environment variables.
- username and sender e-mail as separate variables (needed for SAML environments)
- added ability to specify expiration
- progress option shows percentual representation
- prints download URL at the end of successful transfer

## Usage

```
$ python filesender.py
usage: filesender.py [-h] [-v] [-p] [-u USERNAME] [-e EMAIL] [-r RECIPIENTS]
                     [-a APIKEY] [-b BASEURL] [-d DAYS] [-s SUBJECT]
                     [-m MESSAGE]
                     files [files ...]

positional arguments:
  files                 path to file(s) to send

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose
  -p, --progress
  -u USERNAME, --username USERNAME
  -e EMAIL, --email EMAIL
  -r RECIPIENTS, --recipients RECIPIENTS
  -a APIKEY, --apikey APIKEY
  -b BASEURL, --baseurl BASEURL
  -d DAYS, --days DAYS
  -s SUBJECT, --subject SUBJECT
  -m MESSAGE, --message MESSAGE

```

## Examples
Parameters specified using runtime configuration:

```
$ ./filesender.py -p -v -u sender -e sender@example.com -a abcdef \
-r recipient@example.com -b https://filesender.example.com/rest.php \
-s "Example subject" -m "Example message" /home/sender/testfile.zip

baseurl          : https://filesender.example.com/rest.php
username          : sender
email             : sender@example.com
apikey            : abcdef
upload_chunk_size : 5242880 bytes
recipients        : recipient@example.com
subject           : Example subject
message           : Example message
files             : /home/sender/testfile.zip
postTransfer
putChunks: /home/sender/testfile.zip
Uploading /home/sender/testfile.zip part 3/3
/home/sender/testfile.zip, 99%
Uploading /home/sender/testfile.zip part 2/3
Uploading /home/sender/testfile.zip part 0/3
Uploading /home/sender/testfile.zip part 1/3
/home/sender/testfile.zip, 33%
fileComplete: /home/sender/testfile.zip
transferComplete: https://filesender.example.com/?s=download&token=e3a11b38-1a15-4215-a31b-f0b5f50859fc
Upload Complete: https://filesender.example.com/?s=download&token=e3a11b38-1a15-4215-a31b-f0b5f50859fc
```

Parameters specified using environment variables:
```
#!/bin/bash
export FILESENDER_BASEURL="https://filesender.example.com/rest.php"
export FILESENDER_USER_NAME="sender"
export FILESENDER_USER_EMAIL="sender@example.com"
export FILESENDER_USER_APIKEY="abcdef"
export FILESENDER_RECIPIENTS="recipient@example.com"
export FILESENDER_EXPIRE_DAYS="29"
export FILESENDER_SUBJECT="Example subject"
export FILESENDER_MESSAGE="Example message"

python filesender.py -p $1
````
