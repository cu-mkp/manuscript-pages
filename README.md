You may want to begin by setting up a virtual environment (that way, dependencies are less of a headache). 

Activate the virtual environment: source venv/bin/activate

AUTHENTICATION:
Create a project via the Google Developers Console. Then enable Google Drive API. Then create OAuth2.0 Credentials. Check the Web Server App and User Data options and make "http://localhost:8080/" the redirect URI. Put your gmail address and type in a product name, and then download your credentials as a json file. Rename the file "client_secret.json" and place it in the directory from which you will run the program.

In the directory from which you run the program, create a folder titled "manuscript_downloads". This is where all the manuscript pages will be saved. In the same directory, make a folder titled ".credentials" (not sure if this one is actually necessary, but it doesn't hurt).

To run: python server.py