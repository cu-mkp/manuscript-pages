from __future__ import print_function
import httplib2
import os
import shutil
import io
import json
import urllib

from lxml import etree

from apiclient import discovery
from apiclient import http
from apiclient.http import MediaFileUpload
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
SCOPES = 'https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/drive.file'
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
    page_number = m.group(0)
    m = re.search('[tcnl]+', old_title)
    #file_type refers to whether it is tc, tcn, or tl
    file_type = m.group(0)
    new_file_title = page_number + "_" + file_type + "_preTEI.xml"
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
    
    #clear manuscript_downloads, then create relevant subdirectories
    for the_file in os.listdir("./manuscript_downloads/"):
        file_path = os.path.join("./manuscript_downloads/", the_file)
        try:
           if os.path.isfile(file_path):
               os.unlink(file_path)
           elif os.path.isdir(file_path):
               shutil.rmtree(file_path)
        except Exception as e:
           print(e)

    for x in range(1,171):
        os.makedirs("./manuscript_downloads/" + str(x).zfill(3) + "r")
        os.makedirs("./manuscript_downloads/" + str(x).zfill(3) + "v")

    #Create csv file
    csv = open("well_formedness_errors.csv", "wb")

    #Get each folder in manuscript pages.
    #maxResults is set to 400 so that every folder in __Manuscript Pages can be processed.
    #If you would like to test the code for some functionality, set maxResults to a smaller number.
    folders = service.files().list(q="'0B42QaQPHLJloNnZhakpiVk9GRmM' in parents", maxResults="400").execute()

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
                    print(new_file_title)

                    #grab the file's exportLink to download it
                    flink = f["exportLinks"]["text/plain"]
                    
                    #using exportLink, download and save the file with its new title
                    download_file_by_url(flink, new_file_title)
                    #modify the file to add root tags at the beginning and end
                    add_root_tags(new_file_title)

                    #write the page number, file type (tc, tcn, or tl), and link to the csv file
                    m = re.search('[tcnl]+', ftitle)
                    file_type = m.group(0)
                    with open("well_formedness_errors.csv", "a") as myfile:    
                        myfile.write(page_number + "," + file_type + "," + flink)

                    #check if the file is well-formed XML; 
                    #if it is, write "well-formed" to the csv file; if it's not, write the error message
                    try:
                        with open(new_file_title, "r") as myfile:
                            xml = myfile.read()
                            doc = etree.fromstring(xml)
                        with open("well_formedness_errors.csv", "a") as myfile:
                            myfile.write(", well-formed\n")
                    except Exception as e:
                        print(e)
                        with open("well_formedness_errors.csv", "a") as myfile:
                            myfile.write(", error, " + str(e) + "\n")
                except:
                    print("No exportLink for this file")
    print(len(folders_hash))

    #upload the csv file as a spreadsheet
    file_metadata = {
        'name' : 'wf_errors',
        'title' : 'XML_well-formedness_errors_list',
    'mimeType' : 'application/vnd.google-apps.spreadsheet',
    'parents' : [{'id' : '0BwJi-u8sfkVDZ05XNy1tMUdQM1E'}]
    }
    media = MediaFileUpload('well_formedness_errors.csv', mimetype='text/csv', resumable=True)
    create_file = service.files().insert(body=file_metadata, media_body=media,fields='id').execute()

if __name__ == '__main__':
    main()