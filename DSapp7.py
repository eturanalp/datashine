#!flask/bin/python 
from flask import Flask, jsonify, render_template, redirect, url_for, request
import os  #path, remove, stat
from os import listdir  # to read list of dashboards from .\twbx_templates
from os.path import isfile, join
from create_dashboard_instance10 import CreateDashboardInstance
from create_dashboard_instance10 import DeleteWorkbookInstanceFromTableauOnline
from Alogging import wlog
from Alogging import wlogresult
import uuid   # to generate random string
import datetime
from read_config_into_dict import validate_app_token
from workbook_template_CRUD import Add_workbook_template
from workbook_template_CRUD import Get_workbook_template
from workbook_template_CRUD import Form_PII_string


# Authenticate the Application with "AppSecret" token either in the header or in the form. It is compared to the value in config_file.

app = Flask(__name__, static_url_path='/static')
  
@app.route('/CreateDashboard2', methods=['POST','GET'])
# This web page is for uploading only HUD CSV Data against our own Dashboards (e.g. Client Demographics)
def CreateDashBoard2():
    twbxfiles = [f for f in listdir('.\\twbx_templates\\') if isfile(join('.\\twbx_templates\\', f))]
    instancelink = 'None'
    wid='None'
    #return 'WTH'
    if request.method == 'GET':
        if request.args and request.args['dt'] and not request.args['dt'].isspace():
           print(request.args)
           return render_template('CreateDashboard2.html', link=instancelink, widd=wid, colours=twbxfiles,template=Get_workbook_template(file=request.args['dt'])),200  
        else:
           return render_template('CreateDashboard2.html', link=instancelink, widd=wid, colours=twbxfiles,template=Get_workbook_template(file='Demographics_Report2019_12.twbx')),200  
    if request.method == 'POST':
        # TODO: security scan form fields
        headers = request.headers
        auth_get = headers.get("AppSecret")
        if "AppSecret" in headers:
            if not validate_app_token(request.form['siteid'],auth_get):
                return render_template('CreateDashboard2.html', result='Authentication Failed', link=instancelink, widd=wid, colours=twbxfiles,template=Get_workbook_template(file=request.form['Dashboard'])),401
        elif "AppSecret" in request.form:       
            if not validate_app_token(request.form['siteid'],request.form['AppSecret']):
                return render_template('CreateDashboard2.html', result='Authentication Failed', link=instancelink, widd=wid, colours=twbxfiles,template=Get_workbook_template(file=request.form['Dashboard'])),401     
        else:
            return render_template('CreateDashboard2.html', result='Authentication Failed', link=instancelink, widd=wid, colours=twbxfiles,template=Get_workbook_template(file=request.form['Dashboard'])),401     
        site_id=request.form['siteid']
        report_developer=request.form['report_developer']
        dashboard_template='.\\twbx_templates\\' + request.form['Dashboard']
        user_email=request.form['submitter']
        datafile=request.files['datafile']
        data_zip_file=os.path.join('.\\data_files', datafile.filename)
        datafile.save(data_zip_file)
        if os.stat(data_zip_file).st_size > 64000000 :
          os.remove(data_zip_file)
          return render_template('CreateDashboard2.html', result='File Size exceeds 64MB', link=instancelink, widd=wid, colours=twbxfiles, template=Get_workbook_template(file=request.form['Dashboard'])),500
        remove_pii_flag=request.form.get('remove_pii')  ## TODO: Needs to work when checkbox unselected
        print("request.form.get remove pii flag:") 
        print(remove_pii_flag)
        only_dashboard_flag=request.form['only_dashboard']
        options=request.form['options']
        req_id=uuid.uuid4().hex[0:8]  #request id
        print('req-id=%s' % req_id)
        wlog('log.txt','CreateDashboard2','1.0',datetime.datetime.now(),'App1',req_id,site_id,report_developer,dashboard_template,user_email,data_zip_file,remove_pii_flag,only_dashboard_flag,options)
        (instancelink,wid)=CreateDashboardInstance(req_id,site_id,report_developer,dashboard_template,user_email,data_zip_file,remove_pii_flag,True,options)
        wlogresult('log.txt','Result:',instancelink,wid)
        if wid:
          return render_template('CreateDashboard2.html', link=instancelink, widd=wid, colours=twbxfiles,result='Upload was successfull. Workbook was successfully created.',template=Get_workbook_template(file=request.form['Dashboard'])),200
        else:
          return render_template('CreateDashboard2.html', link=instancelink, widd=wid, colours=twbxfiles, template=Get_workbook_template(file=request.form['Dashboard'])),500        
    if (instancelink=='None'):
       return render_template('CreateDashboard2.html', link=instancelink, widd=wid, colours=twbxfiles, template=Get_workbook_template(file=request.form['Dashboard'])),500
    else:
       return render_template('CreateDashboard2.html', link=instancelink, widd=wid, colours=twbxfiles, template=Get_workbook_template(file=request.form['Dashboard'])),200 
 
	   
@app.route('/DeleteWorkbookInstance', methods=['POST','GET'])
def DeleteWorkbookInstance():
    if request.method == 'POST':
        # TODO: security scan form fields
        headers = request.headers
        auth_get = headers.get("AppSecret")
        if "AppSecret" in headers:
            if not validate_app_token(request.form['siteid'],auth_get):
                return render_template('DeleteWorkbookInstance.html', result='No Authorization!'),401
        elif "AppSecret" in request.form:       
            if not validate_app_token(request.form['siteid'],request.form['AppSecret']):
                return render_template('DeleteWorkbookInstance.html', result='No Authorization!'),401
        wid=request.form['wid']
        site_id=request.form['siteid']
        req_id=uuid.uuid4().hex[0:8]  #request id
        print('req-id=%s' % req_id)
        wlog('log.txt','DeleteWorkbookInstance','1.0',datetime.datetime.now(),'App1',req_id,site_id,wid)
        result=DeleteWorkbookInstanceFromTableauOnline(wid,site_id)
        if result:
                wlogresult('log.txt','Result:','Success!')
                return render_template('DeleteWorkbookInstance.html', result='Success!'),200
        else:
                wlogresult('log.txt','Result:','Fail!')
                return render_template('DeleteWorkbookInstance.html', result='Fail!'),404
    else:
        return render_template('DeleteWorkbookInstance.html', result='Fill in the form!'),200

@app.route('/UploadWorkbookTemplate', methods=['POST','GET'])
def UploadWorkbookTemplate():
        # Saves the Tableau Packeged Workbook (twbx) which is essentially a zip file
        # inserts req_id_RD_filename.twbx into .\twbx_templates
		# Inserts a record into templates.csv
        # TODO: security scan form fields
    if request.method == 'GET':   
       return render_template('UploadWorkbookTemplate.html', result='Fill in the form!'),200
    if request.method == 'POST':
        headers = request.headers
        auth_get = headers.get("AppSecret")
        if "AppSecret" in headers:
            if not validate_app_token(request.form['siteid'],auth_get):
                return render_template('UploadWorkbookTemplate.html', result='No Authorization!'),401
        elif "AppSecret" in request.form:       
            if not validate_app_token(request.form['siteid'],request.form['AppSecret']):
                return render_template('UploadWorkbookTemplate.html', result='No Authorization!'),401
        else:
            return render_template('UploadWorkbookTemplate.html', result='No Authorization!'),401		
        report_developer=request.form['report_developer']
        site_id=request.form['siteid']
        twbxfile=request.files['twbxfile']
        req_id=uuid.uuid4().hex[0:8]  #request id
        twbx_name=req_id+'_'+report_developer+'_'+twbxfile.filename.replace(" ", "").replace("_","")
        wlog('log.txt','UploadWorkbookTemplate','1.0',datetime.datetime.now(),'App1',req_id,site_id,twbx_name)
        try:
           twbxfile.save(os.path.join('./twbx_templates', twbx_name))
        except OSError as e:
           print ("Error: %s - %s." % (e.filename, e.strerror))  
           print ("Copying of %s failed" % twbx_name)
           wlogresult('log.txt','Result:','Fail!')
           return render_template('UploadWorkbookTemplate.html', result='Fail!'),500
        if os.stat(os.path.join('./twbx_templates', twbx_name)).st_size > 64000000 :
           os.remove(os.path.join('./twbx_templates', twbx_name))
           return render_template('UploadWorkbookTemplate.html', result='Fail! Too Big File!'),500
        thprfile=request.files['tpfile']
        if thprfile:
           thprfilename= twbx_name+thprfile.filename.replace(" ", "").replace("_","")
           try:
              thprfile.save(os.path.join('./static/images',thprfilename ))
           except OSError as e:
              print ("Error: %s - %s." % (e.filename, e.strerror))  
              thprfilename='ThumbprintFilePathNone'
           if os.stat(os.path.join('./static/images',thprfilename )).st_size > 64000000 :
              os.remove(os.path.join('./static/images',thprfilename ))
              thprfilename='ThumbprintFilePathNone'
        else:    
           thprfilename='ThumbprintFilePathNone'
        Email=request.form['Email']
        PII1=Form_PII_string(1,request.form['PII1_Table'],request.form['PII1_Column1'],request.form['PII1_Column2'],request.form['PII1_Column2'],request.form['PII1_Column4'],request.form['PII1_Column5'])
        if PII1.find('Error:')>=0:
           return render_template('UploadWorkbookTemplate.html', result='Fail!'+PII1),500
        else:   
           Add_workbook_template(site_id,req_id,report_developer,twbx_name,request.form['DataFormatLink'], request.form['DescriptionText'], request.form['DataSourceLink'], thprfilename, Email,PII1)
        wlogresult('log.txt','Result:','Success!')
        return render_template('UploadWorkbookTemplate.html', result=twbx_name),201       
    else:
        return render_template('UploadWorkbookTemplate.html', result='Fill in the form!'),200

@app.route('/DeleteWorkbookTemplate', methods=['POST','GET'])
def DeleteWorkbookTemplate():
        # deletes req_id_RD_filename.twbx from .\twbx_templates
        # TODO: security scan form fields
    if request.method == 'GET':   
       return render_template('DeleteWorkbookTemplate.html', result='Fill in the form!'),200
    if request.method == 'POST':
        headers = request.headers
        auth_get = headers.get("AppSecret")
        if "AppSecret" in headers:
            if not validate_app_token(request.form['siteid'],auth_get):
                return render_template('DeleteWorkbookTemplate.html', result='No Authorization!'),401
        elif "AppSecret" in request.form:       
            if not validate_app_token(request.form['siteid'],request.form['AppSecret']):
                return render_template('DeleteWorkbookTemplate.html', result='No Authorization!'),401
        else:
            return render_template('DeleteWorkbookTemplate.html', result='No Authorization!'),401		
        report_developer=request.form['report_developer']
        site_id=request.form['siteid']
        twbxfile=request.form['twbxfile']
        req_id=uuid.uuid4().hex[0:8]  #request id
        wlog('log.txt','DeleteWorkbookTemplate','1.0',datetime.datetime.now(),'App1',req_id,site_id,twbxfile)
        try:
           if os.path.exists(os.path.join('.\\twbx_templates', twbxfile)):
               os.remove(os.path.join('.\\twbx_templates', twbxfile))
           else:
               print("Could not locate Workbook file")
               wlogresult('log.txt','Result:','Could not locate Workbook file!')
               return render_template('DeleteWorkbookTemplate.html', result='Fail!'),404
        except OSError as e:
           print ("OS File Error: %s - %s." % (e.filename, e.strerror))  
           wlogresult('log.txt','Result:','Fail!')
           return render_template('DeleteWorkbookTemplate.html', result='Fail!'),500
        wlogresult('log.txt','Result:','Success!')
        return render_template('DeleteWorkbookTemplate.html', result='Success!'),200       
    else:
        return render_template('DeleteWorkbookTemplate.html', result='Fill in the form!'),200
 

  
## DONE: TODO: Improve UploadWorkbookTemplate and CreateDashboard such that CreateDashboard lists uploaded twbx_templates automatically 
## DONE TODO: Tailor for end user: Provide thumbprints and details for our dashboards
## DONE TODO: Add support for link to file data format documentation (UploadWprkbookTemplate) e.g. https://hudhdx.info/Resources/Vendors/HMIS%20CSV%20Specifications%20FY2020%20v1.6.pdf
## IDEA: Reporting for Good Repository : Accept all report definition file formats in addition to Twbx. Tableau workbook repository of analytic dashboards for public good.
## DONE TODO: Store WorkbookTemplate fields in a text file:ID,ReportDeveloper,FileName,DataFormatLink, DescriptionText, DataSourceLink, 
## TODO: ThumbprintFilePath(.\tpfiles)<---GET /api/api-version/sites/site-id/workbooks/workbook-id/previewImage)
## TODO: Web Page that lists Dashboard Templates (simply return templates.csv except the email maybe)
## DONE: TODO: Create a data PII remover module to automatically remove email,SSN, Name, Phone number from the CSV file using regex. Call it before data upload.
##    DONE. But not by regex but with csv module by simply quoting all fields. See mask.py
## DONE: TODO: For HUD CSV data, automatically remove PII columns (or mask data in PII columns). Tell users that "No PII Data will be stored after processing". 
## TODO: Implement only_dashboard flag by publishing only the dashboard (not views)

 
    