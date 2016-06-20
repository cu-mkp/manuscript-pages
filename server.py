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

"""If modifying these scopes, delete your previously saved credentials
    at ~/.credentials/drive-python-quickstart.json
"""
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
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)   # This is where the magic happens
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
    """Given url and path, download the file located at url to location path
    """
    try:
        testfile = urllib.URLopener()   
        testfile.retrieve(url, path)
    except:
        return


def get_new_file_title(old_title):
    """Given a file title, return the file's new title, according to the naming convention:
        tc_p057r ==> 057_tc_preTEI.xml
    """
    m = re.search('\d+[rv]', old_title)
    page_number = m.group(0)
    m = re.search('[tcnl]+', old_title)
    file_type = m.group(0)  # File_type refers to whether the file is tc, tcn, or tl
    new_file_title = page_number + "_" + file_type + "_preTEI.xml"
    return new_file_title

def add_root_tags(path):
    """Given a file's location path, add root tags to the beginning and end of the file
    """
    with open(path, "a") as f:    # Append "</root>" to end of file
        f.write("</root>")
    
    with open(path, "r+") as f:   # Add "<root>" to beginning of file
        old = f.read()
        f.seek(0)
        f.write("<root>" + old)
    return

def clear_directory(path):
    """Clears the directory at location path of all files and subdirectories
    """
    for the_file in os.listdir(path):
        file_path = os.path.join(path, the_file)
        try:
           if os.path.isfile(file_path):
               os.unlink(file_path)
           elif os.path.isdir(file_path):
               shutil.rmtree(file_path)
        except Exception as e:
           print(e)
    return

def upload_csv_as_spreadsheet(service, path, file_title, file_parents=""):
    """Uploads a csv file to user's Google Drive as a Google spreadsheet

    Args:
        service: the service object with which you are accessing the Drive API
        path: the path to the file to be uploaded
        file_title: the title to be given to the uploaded file
        file_parents: the IDs of the folders that this file should be uploaded to
            e.g. if you with the uploaded file to be placed within a directory with ID 0BwJi-u8sfkVDZ05XNy1tMUdQM1E,
                then pass [{'id' : '0BwJi-u8sfkVDZ05XNy1tMUdQM1E'}] as the file_parents argument
            If no value is passed for file_parents, then it is placed in the root folder of the user's Drive
    """
    if file_parents=="":
        file_metadata = {    
            'title' : file_title,
        'mimeType' : "application/vnd.google-apps.spreadsheet"
        }
    else:
        file_metadata = {    
            'title' : file_title,
        'mimeType' : "application/vnd.google-apps.spreadsheet",
        'parents' : file_parents
    }
    
    media = MediaFileUpload(path, mimetype='text/csv', resumable=True)
    create_file = service.files().insert(body=file_metadata, media_body=media,fields='id').execute()
    return

def main():
    """Downloads every file in __Manuscript Pages and saves them to the correct subdirectory of manuscript_downloads.
        Adds root tags to each file, checks if the files are well-formed XML.
        Writes the results of this check to well_formedness_errors.csv
        Uploads the csv as a spreadsheet to 2016 Files for Paleographers.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v2', http=http)
    
    clear_directory("./manuscript_downloads/")  # Clear manuscript_downloads directory

    for x in range(1,171):  # Repopulate manuscript_downloads with appropriate subdirectories
        os.makedirs("./manuscript_downloads/" + str(x).zfill(3) + "r")
        os.makedirs("./manuscript_downloads/" + str(x).zfill(3) + "v")

    csv = open("well_formedness_errors.csv", "wb")  # Create csv file

    """Get each folder in manuscript pages.
        maxResults is set to 400 so that every folder in __Manuscript Pages can be processed.
        If you would like to test the code for some functionality, set maxResults to a smaller number.
    """
    folders = service.files().list(q="'0B42QaQPHLJloNnZhakpiVk9GRmM' in parents", maxResults="400").execute()

    folders_hash = folders["items"]

    for folder in folders_hash:
        try:    # Get the folder's id
            folder_id = folder["id"]
            print(folder_id)
            print(folder["title"])
        except:
            print("no title")

        files_within_folder = service.files().list(q="'" + folder_id + "' in parents").execute()    # Use the folder's id to get all files within the folder
        files = files_within_folder.get('items', [])
        if not files:
            print('No files found.')
        else:
            print('Files:')
            
            for f in files: # Process every file with an exportLink
                try:
                    ftitle = f["title"] # Get the file's title
                    m = re.search('\d+[rv]', ftitle)
                    page_number = m.group(0)    # Get the page number of the file to put it in the correct folder
                    new_file_title = "manuscript_downloads/" + page_number + "/" + get_new_file_title(ftitle)   # Generate the file's new name
                    print(new_file_title)
                    
                    flink = f["exportLinks"]["text/plain"]
                    download_file_by_url(flink, new_file_title) # Using the exportLink, download and save the file with its new title
                    add_root_tags(new_file_title)   # Modify the file to add root tags at the beginning and end

                    m = re.search('[tcnl]+', ftitle)
                    file_type = m.group(0)
                    with open("well_formedness_errors.csv", "a") as myfile: # Write the page number, file type (tc, tcn, or tl), and link to the csv file
                        myfile.write(page_number + "," + file_type + "," + flink)

                    try:    # Check if the file is well-formed XML, write results to the csv
                        with open(new_file_title, "r") as myfile:
                            xml = myfile.read()
                            doc = etree.fromstring(xml)
                        with open("well_formedness_errors.csv", "a") as myfile:
                            myfile.write(", well-formed, , , ")

                        download_file_by_url("http://52.87.169.35:8080/exist/rest/db/ms-bn-fr-640/lib/preTEI.rng", "preTEI.rng")    # Download the schema
                        relaxng_doc = etree.parse("preTEI.rng")
                        relaxng = etree.RelaxNG(relaxng_doc)
                        doc = etree.parse(new_file_title)

                        try:    # Validate the file against the schema, write results to the csv
                            relaxng.assertValid(doc)
                            with open("well_formedness_errors.csv", "a") as myfile:
                                myfile.write(", schema-valid\n")
                        except Exception as e:
                            with open("well_formedness_errors.csv", "a") as myfile:
                                myfile.write(", not schema-valid, " + str(e) + "\n")

                    except Exception as e:
                        with open("well_formedness_errors.csv", "a") as myfile:
                            myfile.write(", not well-formed, " + str(e) + "\n")

                except:
                    print("No exportLink for this file")

    print(len(folders_hash) + " folders processed.")

    upload_csv_as_spreadsheet(service,  # Upload the csv file as a spreadsheet
        "well_formedness_errors.csv", 
    "XML_well-formedness_errors_list", 
    [{'id' : '0BwJi-u8sfkVDZ05XNy1tMUdQM1E'}])

if __name__ == '__main__':
    main()