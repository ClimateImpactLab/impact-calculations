import urllib.request, urllib.error, urllib.parse, json, os
try:
    import gspread
    from oauth2client.client import SignedJwtAssertionCredentials
except:
    print("Failed to load gspread and oauth2client; Google functions will not work.")

def open_url(path):
    req = urllib.request.Request(full_url(path))
    return urllib.request.urlopen(req)

def full_url(path):
    return "http://dmas.berkeley.edu" + path
    #return "http://127.0.0.1:8080" + path

def get_dmas_spreadsheet():
    json_key = json.load(open(os.path.dirname(os.path.realpath(__file__)) + "/DMAS-45b7d1cccd53.json"))
    scope = ['https://spreadsheets.google.com/feeds']

    credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
    gc = gspread.authorize(credentials)

    # Open a worksheet from spreadsheet with one shot
    return gc.open("Master DMAS Information")

def get_model_info():
    wks = get_dmas_spreadsheet().get_worksheet(1)
    header = wks.row_values(1)
    ids = wks.col_values(header.index('Unique ID') + 1)

    return wks, header, ids
