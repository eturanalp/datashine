## Publishes the packaged workbook to Tableau Online
import requests
import json
from read_config_into_dict import read_config_file
import read_config_into_dict          # read configuration file
from subprocess import check_output   # call curl
import os     # file operations
import subprocess
import uuid   # to generate random string
import zipfile
from shutil import copyfile
import shutil   # to make zip file from folder and to remove directory
from datetime import datetime  # to calculate if user login is within last 2 weeks
from workbook_template_CRUD import Get_workbook_template
from mask import maskPII
import smtplib

def CreateDashboardInstance(req_id,site_id, report_developer, dashboard_template, user_email, data_zip_file, remove_pii_flag=False, only_dashboard_flag=False, options='forFutureUse'):
   #dashboard_template is the path to the Tableau file(typically twbx) that contains the dashboard that uses standard csv files as data source 
   #data_zip_file is the path to the input customer data file containing csv files.
   site_config=read_config_file(site=site_id)
   stoken=Get_TO_Access_Token(site_id,site_config['user'],site_config['password'],site_config['host-api-url'])
   print(stoken)
   user_id=CreateTableauUser(user_email,stoken,site_config['site_guid'],site_config['host-api-url'],site_config['user_group'])
   project_id=CreateProject(site_config['site_guid'],site_config['host-api-url'],site_config['parent-project-name'],stoken,report_developer,user_email)
   print(project_id)
   if project_id:
      print(SetProjectPermissions(site_config['site_guid'],site_config['host-api-url'],stoken,project_id,user_id))
   else:
      return ('Could not create Project Folder on Tableu Online','')
   [workbook_instance,XF]=InsertDataIntoTemplate(req_id,site_id, report_developer, dashboard_template, data_zip_file, user_email, remove_pii_flag)     
   if not workbook_instance:
      return ('Could not create workbook instance','')      
   (link,wid)=PublishWorkbookInstance(req_id,workbook_instance,site_config['site_guid'],site_config['host-api-url'],project_id,stoken,report_developer,user_email,dashboard_template, data_zip_file)   
   DeleteWorkFiles(req_id,workbook_instance,XF,project_id)
   if link:
      gmail("xxxxxxx@ctagroup.org",user_email,link)
      return (link,wid)
   else:
      return ('Could not create dashboard instance','')

def Get_TO_Access_Token(site,user,password,site_url):
   signin_payload= '''{ \"credentials\": { \"name\": \"%s\", \"password\": \"%s\", \"site\": {\"contentUrl\": \"%s\" }}}''' % (user,password,site)
   aheader = {'Content-type':'application/json',
             'Accept':'application/json'}
   curlGetTokenResult = requests.post('%sauth/signin' % site_url,data=signin_payload, headers=aheader)           
   y=json.loads(curlGetTokenResult.text)
   token=y['credentials']['token'] 
   return token
 
def CreateTableauUser(user_email,stoken,site_guid,site_url,designated_user_group):
   # Adds user to Tableau Online site, returns the user_id
   # Also add the user to a designated user group e.g. "DS_data_uploaders" 
   payload='''{ \"user\": { \"name\": \"%s\", \"siteRole\": \"Viewer\"}}''' % user_email
   aheader = {'Content-type':'application/json',
             'Accept':'application/json'}
   aheader['X-Tableau-Auth']=stoken          
   postresult = requests.post('%ssites/%s/users/' % (site_url,site_guid),data=payload, headers=aheader) 
   if (postresult.status_code==409):   # User exists
      #return the user_id of this existing user         
      getresult = requests.get('%ssites/%s/users?filter=name:eq:%s' % (site_url,site_guid,user_email), headers=aheader) 
      if (getresult.status_code==200):
          y=json.loads(getresult.text)
          user_id=y["users"]["user"][0]["id"]
          #print(f'Found this user:{y["users"]["user"][0]["name"]}')
          return user_id 
      else:
          return 0 
   elif (postresult.status_code==201):     # User is created. Also add it to the designated group i.e. DS_data_uploaders
      y=json.loads(postresult.text)
      user_id=y["user"]["id"]
      print('user-id=%s' % user_id)
      get_group_id_payload='''{ \"user\": \"%s\"}''' % user_id
      get_group_id_getresult = requests.get('%ssites/%s/groups?filter=name:eq:%s' % (site_url,site_guid,designated_user_group),data=get_group_id_payload, headers=aheader)   
      if (get_group_id_getresult.status_code==200):
         yy=json.loads(get_group_id_getresult.text)
         try:
            group_id=yy["groups"]["group"][0]["id"]
         except:
            print('Could not obtain id for user group. Check that the designated group exists.')
            return 0
         aytg_payload='''{\"user": { \"id\":\"%s\"}}''' % user_id
         aytg_postresult = requests.post('%ssites/%s/groups/%s/users' % (site_url,site_guid,group_id),data=aytg_payload, headers=aheader)
         if (aytg_postresult.status_code==200):   
            return user_id 
         elif (aytg_postresult.status_code==409):   
            print('User already in Group')    
            return 0
         else:
            return 0
      else:
          print('Could not obtain id for user group') 
          return 0        
   else:
      return 0

def CreateProject(site_guid,site_url,parent,stoken,rdeveloper,user_email):
      # A project is created for the workbook instance, let's call it the-project. It is named as "DS_{user_email}".
      # It is created as \parent-project\Report-developer's project\the-project
      # First, get the guid of the parent project=the root folder under which all workbook instances are stored.
      parent_project_id=''
      aheader = {'Content-type':'application/json','Accept':'application/json'}
      aheader['X-Tableau-Auth']=stoken           
      getresult = requests.get('%ssites/%s/projects?filter=name:eq:%s' % (site_url,site_guid,parent), headers=aheader) 
      #print(f'Get Response for {parent}:{getresult.text}')
      if (getresult.status_code==200):
          if "\"project\"" in getresult.text:
             y=json.loads(getresult.text)
             parent_project_id=y["projects"]["project"][0]["id"]
          else:
             print('Creating the Parent Project')         
             payload='''{ \"project\": {\"name\": \"%s\",\"description\": \"Auto-created project by DataShine as the root-parent project\",\"contentPermissions\": \"LockedToProject\"}}''' % (parent)        
             postresult = requests.post('%ssites/%s/projects' % (site_url,site_guid),data=payload, headers=aheader) 
             print(postresult.text)			 
             print(payload)
             if (postresult.status_code==201):      
                y=json.loads(postresult.text)
                parent_project_id=y['project']['id']    
             else:
                return 0                         
      else:
          return 0 
      	  
      # Get rdeveloper_project_id. Create The Developer's project if necessary
      aheader = {'Content-type':'application/json','Accept':'application/json'}
      aheader['X-Tableau-Auth']=stoken           
      getresult = requests.get('%ssites/%s/projects?filter=parentProjectId:eq:%s,name:eq:%s' % (site_url,site_guid,parent_project_id,rdeveloper), headers=aheader) 
      if (getresult.status_code==200):
          if "\"project\"" in getresult.text:
             y=json.loads(getresult.text)
             rdeveloper_project_id=y["projects"]["project"][0]["id"]
          else:
             #  Create the Report Developer's Project
             print('Creating the Report Developer\'s Project')         
             payload='''{ \"project\": {\"parentProjectId\":\"%s\",\"name\": \"%s\",\"description\": \"Auto-created project by DataShine for developer %s for user %s\",\"contentPermissions\": \"LockedToProject\"}}''' % (parent_project_id,rdeveloper,rdeveloper,user_email)        
             postresult = requests.post('%ssites/%s/projects' % (site_url,site_guid),data=payload, headers=aheader)         
             if (postresult.status_code==201):      
                y=json.loads(postresult.text)
                rdeveloper_project_id=y['project']['id'] 
                print('rdeveloper project created:%s' % y['project']["name"])				
             else:
                return 0             
      else:
          return 0  
  
      # Create The-Project for this workbook instance
      payload='''{ \"project\": {\"parentProjectId\":\"%s\",\"name\": \"DS_%s\",\"description\": \"Auto-created project by DataShine for user %s\",\"contentPermissions\": \"LockedToProject\"}}''' % (rdeveloper_project_id,user_email,user_email)        
      postresult = requests.post('%ssites/%s/projects' % (site_url,site_guid),data=payload, headers=aheader) 
      if (postresult.status_code==409):
         #return the project_id of the existing project for the user         
         getresult = requests.get('%ssites/%s/projects?filter=name:eq:DS_%s' % (site_url,site_guid,user_email), headers=aheader) 
         if (getresult.status_code==200):
            if "\"project\"" in getresult.text:
               y=json.loads(getresult.text)
               project_id=y["projects"]["project"][0]["id"]
               return project_id
            else:
               return 0 
         else:
            return 0 
      elif (postresult.status_code==201):      
         y=json.loads(postresult.text)
         project_id=y['project']['id']
         return project_id 
      else:
         return 0
         
def SetProjectPermissions(site_guid,site_url,stoken,project_id,user_id,capability='Read'):
   # Set project permissions and the default workbook permissions in the project to the capability
   payload='''<tsRequest><permissions><granteeCapabilities><user id=\"%s\" /> <capabilities><capability name=\"%s\" mode=\"Allow\" /></capabilities></granteeCapabilities></permissions></tsRequest>''' % (user_id,capability)
   aheader = {'Content-type':'application/xml','Accept':'application/json'}
   aheader['X-Tableau-Auth']=stoken          
   putresult = requests.put('%ssites/%s/projects/%s/permissions' % (site_url,site_guid,project_id),data=payload, headers=aheader) 
   if (putresult.status_code==200): 
      payload='''<tsRequest><permissions><granteeCapabilities><user id=\"%s\" /> <capabilities><capability name=\"%s\" mode=\"Allow\" /><capability name=\"Filter\" mode=\"Allow\" /></capabilities></granteeCapabilities></permissions></tsRequest>''' % (user_id,capability)     
      putresult = requests.put('%ssites/%s/projects/%s/default-permissions/workbooks' % (site_url,site_guid,project_id),data=payload, headers=aheader) 
      if (putresult.status_code==200):
         return 1
      else: 
         return 0     
   else:
      return 0   
 
def InsertDataIntoTemplate(req_id,site_id, rdev, dashboard_template, data_zip_file,user,remove_pii_flag):
    # dashboard_template and data_zip_file are file paths (e.g. ".\twbx_templates\Demographics_Report2019_12.twbx")
    # Ideally dashboard_template is under .\twbx_templates folder and the data_zip_file is under .\data_files folder
    # data_zip_file contains csv files under the root folder
	
    #1. Create a temp folder X under \zip_work
    #2. unzip dashboard_template to \zip_work\X
    #3. data_source_folder=the first (ideally only) folder under \zip_work\X\data
    #4. copy contents of data_zip_file to zip_work\X\data\data_source_folder
	#5. Remove PII from the file whose name is specified in templates.csv(e.g. Clients) from zip_work\X\data\data_source_folder
    #6. zip  zip_work\X\* into instance_path
    #7. rename instance_path to instance_path.twbx
    #8. return instance_path
    
    XF='.\\zip_work\\'+'TD_' + req_id
    try:
       os.mkdir(XF)
    except OSError:
        print ("Creation of directory %s failed" % XF)
        return ''
    try:
       zipfile.ZipFile(dashboard_template).extractall(XF)
    except:
        print ("Zip extract of Template failed %s" % XF)
        return ''
    data_source_folder=next(os.walk(XF + '\\data'))[1][0]  # first folder under data will be populated
    print(data_source_folder)
    try: 
       zipfile.ZipFile(data_zip_file).extractall(XF + '\\data\\' + data_source_folder )
    except BadZipfile:
        print ("Bad zip file %s" % data_zip_file)
        return ''       
    except:
        print ("Zip extract of input data file failed %s" % data_zip_file)
        return ''
    #Get PII1_filename and PII1_fieldnames from templates.csv
    if remove_pii_flag:
       #print("Inside remove_pii_flag.....")
       template_data=Get_workbook_template(file=os.path.basename(dashboard_template))
       PII1_fname=template_data['PII1'].split('=')[1].split('(')[0]
       f1=template_data['PII1'].split('=')[1].split('(')[1].strip('()').split(',')
       for i,f1i  in enumerate(f1):
         f1[i]=f1i.strip('\'') 
       PII1_fieldnames=f1
    #Produce the PII removed file and replace it with the original
       PII1_fpath=XF + '\\data\\' + data_source_folder + '\\' + PII1_fname	
       maskPII( PII1_fpath, PII1_fpath + '.masked', columns=PII1_fieldnames, operation='mask')
       try:
          shutil.move(PII1_fpath + '.masked', PII1_fpath)
       except:
           print ("Replacing PII masked file with %s failed" % PII1_fpath)
           return ''	
    instance_path='.\\workbook_instances\\%s_' % os.path.basename(dashboard_template).replace(" ", "")
    instance_path=instance_path + os.path.basename(data_zip_file).replace(" ", "")
    instance_path=instance_path + '_' + rdev.replace(" ", "") + '_' + user.replace(" ", "") + '_' + req_id
    print(instance_path)
    shutil.make_archive(instance_path, 'zip', XF)
    try:
       shutil.move(instance_path + '.zip', instance_path + '.twbx')
    except:
        print ("Renaming of instance %s failed" % instance_path)
        return ''
    return [instance_path + '.twbx', XF]

def PublishWorkbookInstance(req_id,workbook_instance,site_guid,site_url,project,stoken,rdeveloper,user_email,dashboard_template, data_zip_file):
    ##Finally, publish the workbook in the created project folder

    request_payloadfilename='RP_' + req_id + '.xml'
    request_payload='<tsRequest><workbook name=\"WI_%s_%s\" showTabs=\"false\" ><project id=\"%s\"/></workbook></tsRequest>' % (os.path.basename(dashboard_template).replace(" ", ""),os.path.basename(data_zip_file).replace(" ", ""),project)
    with open(request_payloadfilename, 'w') as fi:
        fi.write(request_payload)
        fi.close()
    print(f'request_payload: {request_payload}')
 
    token_header='''X-Tableau-Auth:%s''' % stoken
    token_header=token_header.replace('|','^|')
    # copied curl.exe to the current path
    publish_workbook=subprocess.check_output(['curl', '-H', '''Accept: application/json''', '-H', '''Content-Type: multipart/mixed;''', '-H', token_header, '-F', '''request_payload=@%s''' % request_payloadfilename, '-F', '''tableau_workbook=@%s''' % workbook_instance, '-X', 'POST', '%ssites/%s/workbooks?workbookType=twbx^&overwrite=true' %(site_url,site_guid)],shell=True)
    os.remove(request_payloadfilename)
    #print(f'CURL result: {publish_workbook}')
    y=json.loads(publish_workbook)
    if 'createdAt' in publish_workbook.decode("utf-8") :
       print('Publish Successfull!!')
    print(y["workbook"]["webpageUrl"])   
    if 'http' in y["workbook"]["webpageUrl"]: 
        print('workbook-id=%s' % y["workbook"]["id"])
        return (y["workbook"]["webpageUrl"],y["workbook"]["id"])
    else: 
        print('Could not create dashboard instance')
        return ''    
    
    # Below code returns error "uncerognized content" from Tableau Online Publish Workbook API    
    #files = [('request_payload',('request_payload',open(request_payloadfilename, 'rb'), 'text/xml', {'Expires': '0'})),('tableau_workbook', ('tableau_workbook', open(workbook_instance, 'rb'), 'application/octet-stream', {'Expires': '0'}))]
    #files = {'request_payload':('somefile.txt',request_payload)}
    #aheader = {'Content-Type': 'multipart/mixed;','Accept':'application/json'}
    #aheader['X-Tableau-Auth']=stoken 
    
    #prep=requests.Request('POST', '%ssites/%s/workbooks?workbookType=twbx&overwrite=true' % (site_url,site_guid), headers=aheader, files=files).prepare()
    #print(prep.body)
    # publish_workbook=requests.post('%ssites/%s/workbooks?workbookType=twbx&overwrite=true' % (site_url,site_guid), headers=aheader, files=files)
    # print(publish_workbook.text)
    # y=publish_workbook.json
    # if 'createdAt' in publish_workbook:
       # print('Publish Successfull!!')
    # print(y["workbook"]["webpageUrl"])   
    # if 'http' in y["workbook"]["webpageUrl"]: 
        # return y["workbook"]["webpageUrl"]
    # else: 
        # return 'Could not create dashboard instance'

def DeleteWorkFiles(req_id,workbook_instance,XF,project_id):
    print(workbook_instance)
    print(XF)
    try:
       f = open(workbook_instance, 'w')
       f.write('req_id=%s , instance_name=%s , project-id=%s' %(req_id,workbook_instance,project_id))
       f.close()
    except:
       print('Error deleting contents of workbook instance %s' % workbook_instance) 
       return 0
    try:
       shutil.rmtree(XF)
    except OSError as e:
       print ("Error deleting work folder %s . Error: %s - %s." % (XF,e.filename, e.strerror))  
       return 0
    os.mkdir(XF)
    return 1

def DeleteWorkbookInstanceFromTableauOnline(wid,site_id):
   # No payload
   # site_id is the TO site name that is part of the API access URL
   # First query the workbook's project and then delete the project
   #site-id/workbooks/workbook-id
   
   site_config=read_config_file(site=site_id)
   stoken=Get_TO_Access_Token(site_id,site_config['user'],site_config['password'],site_config['host-api-url'])
   aheader = {'Content-type':'application/xml','Accept':'application/json'}
   aheader['X-Tableau-Auth']=stoken          
   
   getresult= requests.get('%ssites/%s/workbooks/%s' % (site_config['host-api-url'],site_config['site_guid'],wid) , headers=aheader)
   if (getresult.status_code==200):
       try:
          y=json.loads(getresult.text)
          project_id=y["workbook"]["project"]["id"]
       except:
          print('Could not locate project for workbook')
          return 0
       deleteresult = requests.delete('%ssites/%s/projects/%s' % (site_config['host-api-url'],site_config['site_guid'],project_id), headers=aheader) 
       if (deleteresult.status_code==204): 
          return 1   
       else:
          return 0              

def DeleteInactiveUsers(site_id,timediff_inseconds):
   # 1. Get users in group site_config['user_group']
   # 2. For each of them, remove the user if it did not login in the past 2 weeks.
   # Does not delete the project which was created for this user at the time of workbook instance upload
   # Therefore it must be deleted manually. 
   # It is under the designated project of the site under report developer's folder (e.g. HUDCSV_Projects\RD2)
   site_config=read_config_file(site=site_id)
   stoken=Get_TO_Access_Token(site_id,site_config['user'],site_config['password'],site_config['host-api-url'])
   designated_user_group=site_config['user_group']
   site_guid=site_config['site_guid']
   site_url=site_config['host-api-url']
   aheader = {'Content-type':'application/xml','Accept':'application/json'}
   aheader['X-Tableau-Auth']=stoken 
    
   #get_group_id_payload='''{ \"user\": \"%s\"}''' % user_id
   get_group_id_getresult = requests.get('%ssites/%s/groups?filter=name:eq:%s' % (site_url,site_guid,designated_user_group), headers=aheader)   
   if (get_group_id_getresult.status_code==200):
       yy=json.loads(get_group_id_getresult.text)
       try:
          group_id=yy["groups"]["group"][0]["id"]
       except:
          print('Could not obtain id for user group. Check that the designated group exists.')
          return 0
       get_users_result= requests.get('%ssites/%s/groups/%s/users' % (site_url,site_guid,group_id) , headers=aheader)
       if (get_users_result.status_code==200):
          yyy=json.loads(get_users_result.text)
          print(get_users_result.text)
          if len(yyy["users"])<1:
             print('No Users in group %s' % designated_user_group)
             return 1
          for u in yyy["users"]["user"]:    # for each user
             get_user= requests.get('%ssites/%s/users/%s' % (site_url,site_guid,u["id"]) , headers=aheader)
             print(u["name"] + ',' + u["id"])
             lastLoginTime=datetime.now()
             if "lastLogin" in json.loads(get_user.text)["user"]:
                lastLogin=json.loads(get_user.text)["user"]["lastLogin"]
                lastLoginTime = datetime.strptime(lastLogin, '%Y-%m-%dT%H:%M:%SZ')
                diff=lastLoginTime - datetime.now()
                if diff.seconds>timediff_inseconds:
                   # delete user
                   if not ("ctagroup.org" in u["name"]):
                      del_user= requests.delete('%ssites/%s/users/%s' % (site_url,site_guid,u["id"]) , headers=aheader)
                      if del_user.status_code==204:
                         #TODO: Also delete user's project under rdeveloper folder
                         print('Deleted User %s. Delete its projects manually.' % u["name"])
                      else:
                         print('Could not delete User %s' % u["name"])
                   else:
                      print("Alert : Can not delete user %s because User has ctagroup.org email" % u["name"])
                else:
                   print('User %s logged in %s days ago' % (u["name"],diff.days))
             else:
                print('User %s has never logged in' % u["name"])
                # TODO: Handle this situation later
                # Delete users workbooks, not implemented
                get_workbooks= requests.get('%ssites/%s/users/%s/workbooks' % (site_url,site_guid,u["id"]) , headers=aheader)
                print("Users workbooks:" + get_workbooks.text)
                yyw=json.loads(get_workbooks.text)
                for w in yyw["workbooks"]["workbook"]:
                   print(w["name"])
             print(lastLoginTime)
             print(get_user.text)
          return get_users_result.text  
       else:
          return 'Could not obtain users for group %s' % designated_user_group
   else:
       return 0
       
  
def gmail(semail,email,messagelink):
  ## Send email via gmail smtp 587
  ## semail=source, email=destination
  s = smtplib.SMTP('smtp.gmail.com', 587) 
  s.starttls() 
  s.login("xxxxxxx@ctagroup.org", "yyyyyyyyyy")  
  message1="Your Tableau Online workbook was successfully created at " + messagelink + " ."
  message = 'Subject: {}\n\n{}'.format("Your Tableau Online workbook", message1)
  try:
    r=s.sendmail(semail, email, message)
  except:
    print("Error sending email to " + email)  
  print("message sent to " + email)
  s.quit()
  return r
  
def testcurl():
    # env = os.environ
    # publish_workbook=subprocess.run('curl -H',shell=True,env=env) 
    publish_workbook=subprocess.check_output(['curl', '-H'])
    print(publish_workbook) 

# DONE TODO: Enforce max-data-size
# TODO: There are TODO's inside the code
# FUTURE FEATURE: If dashboard_template is blank then upload data for all of the report_developer's dashboards.
# FUTURE FEATURE: Let users replace connection information instead of data itself
# FUTURE FEATURE: Implemented for PII1. 
#                 Let developers specify the PII in a format like Client.csv(Name, Tel, email) so that remove_pii_flag=True can be implemented by masking those columns in csv during upload . Developers may be asked to upload a sample data file and asked to identify PII columns for upto 3 tables in the mean time.
# TODO: Use a different email account to send email