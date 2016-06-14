from __future__ import print_function
import httplib2

import os
import io
import json
import urllib

from lxml import etree

from apiclient import discovery
from apiclient import http
from apiclient import errors

import oauth2client
from oauth2client import client
from oauth2client import tools

import re

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'
REDIRECT_URI = "http://localhost:8080/"


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('./')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-quickstart.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        #this is where the magic happens
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            print(flow)
            print(store)
            print(flags)
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def download_file_by_url(url, path):
    try:
        testfile = urllib.URLopener()   
        testfile.retrieve(url, path)
    except:
        return

#given a file title, return the file's new title, according to the naming convention:
# tc_p057r ==> 057_tc_preTEI.xml
def get_new_file_title(old_title):
    m = re.search('\d+[rv]', old_title)
    folio_number = m.group(0)
    m = re.search('[tcnl]+', old_title)
    #file_type refers to whether it is tc, tcn, or tl
    file_type = m.group(0)
    new_file_title = folio_number + "_" + file_type + "_preTEI.xml"
    return new_file_title

def add_root_tags(file_title):
    #append "</root>" to end of file
    with open(file_title, "a") as f:
        f.write("</root>")
    #add "<root>" to beginning of file
    with open(file_title, "r+") as f:
        old = f.read()
        f.seek(0)
        f.write("<root>" + old)
    return

def main():
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v2', http=http)

    #Get each folder in manuscript pages
    folders = service.files().list(q="'0B42QaQPHLJloNnZhakpiVk9GRmM' in parents", maxResults="5").execute()
    folders_hash = folders["items"]

    for folder in folders_hash:
        #get the folder's id
        try:
            folder_id = folder["id"]
            print(folder_id)
            print(folder["title"])
        except:
            print("no title")

        #using the folder's id, grab all files within the folder
        files_within_folder = service.files().list(q="'" + folder_id + "' in parents").execute()
        files = files_within_folder.get('items', [])
        if not files:
            print('No files found.')
        else:
            print('Files:')
            #grab the export link (if it exists) of each file within the folder
            for f in files: 
                try:
                    #grab the file's title and generate the new title
                    ftitle = f["title"]
                    #grab the page number of the file to put it in the correct folder
                    m = re.search('\d+[rv]', ftitle)
                    page_number = m.group(0)
                    new_file_title = "manuscript_downloads/" + page_number + "/" + get_new_file_title(ftitle)
                    print(ftitle)
                    print(new_file_title)
                    #grab the file's exportLink to download it
                    flink = f["exportLinks"]["text/plain"]
                    print(flink)
                    #using exportLink, download and save the file with its new title
                    download_file_by_url(flink, new_file_title)
                    #modify the file to add root tags at the beginning and end
                    add_root_tags(new_file_title)

                    #check if the file is well-formed XML
                    try:
                        xml = str(f.open(new_file_title))
                        doc = etree.fromstring(xml)
                    except XMLSyntaxError as e:
                        print(e)
                except:
                    print("No exportLink for this file")
    print(len(folders_hash))

if __name__ == '__main__':
    main()