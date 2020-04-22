import csv

def Add_workbook_template(SiteID,ID,ReportDeveloper,FileName,DataFormatLink, DescriptionText, DataSourceLink, ThumbprintFilePath, Email,PII1):
   with open('templates.csv', 'a', newline='') as csvfile:
     fieldnames = ['SiteID','ID','ReportDeveloper','FileName','DataFormatLink', 'DescriptionText', 'DataSourceLink', 'ThumbprintFilePath', 'Email','PII1']
     writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)

     #writer.writeheader()
     writer.writerow({'SiteID':SiteID,'ID':ID,'ReportDeveloper':ReportDeveloper,'FileName':FileName,'DataFormatLink':DataFormatLink, 'DescriptionText':DescriptionText, 'DataSourceLink':DataSourceLink, 'ThumbprintFilePath':ThumbprintFilePath, 'Email':Email, 'PII1':PII1})

def Get_workbook_template(file='All'):   # as a dictionary
   wt={}  #contents of workbook template
   with open('templates.csv', mode='r') as csv_file:
       csv_reader = csv.DictReader(csv_file, quoting=csv.QUOTE_MINIMAL)
       line_count = 0
       for row in csv_reader:
            wt[row["FileName"]]=row
   #print(f'Processed {configd["communitytechnologyalliance"]["parent-project"]} lines.')
   if file=='All':
      return wt
   else:
      return wt[file]  

def Form_PII_string(PIINo,TableName,c1,c2,c3,c4,c5):
  # Constructs the PIIX string that is stored in the templates.csv file under PIIX fields
  # Validates Input (e.g. field names should not contain commas) such that 
  # it is safe to store it in a format like PII1=Client.csv('FirstName','LastName','SSN','DOB')
  # Returns Error string if input is invalid
  d1=TableName+c1+c2+c3+c4+c5
  if d1.find(',')>=0:
     return 'Error:Input text contains commas(,)'
  if d1.find('\'')>=0 or d1.find('"')>=0 :
     return 'Error:Input text contains quotes'  
  if TableName:
     if c1:
        columns="'" + c1 + "'"
        if c2:
           columns=columns + ',' + "'" + c2 + "'"
        if c3:
           columns=columns + ',' + "'" + c3 + "'"
        if c4:
           columns=columns + ',' + "'" + c4 + "'"
        if c5:
           columns=columns + ',' + "'" + c5 + "'"
        return 'PII'+ str(PIINo) + '=' + TableName + '(' + columns + ')' 
     else:
        return 'Error: Column 1 is blank'
  else:
     return 'Error: File Name is blank'  
 