import csv

def read_config_file(site='All'):   # into dictionary
   configd={}  #contents of config file
   with open('config_file.txt', mode='r') as csv_file:
       csv_reader = csv.DictReader(csv_file)
       line_count = 0
       for row in csv_reader:
            configd[row["site-id"]]=row
   #print(f'Processed {configd["communitytechnologyalliance"]["parent-project"]} lines.')
   if site=='All':
      return configd
   else:
      return configd[site]    
   
def validate_app_token(site_id,app_token):
    cd=read_config_file()  
    if app_token==cd[site_id]["app-auth-token"]:
       return True
    else:
       return False
       