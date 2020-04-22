import os     # file operations
from shutil import copyfile
import csv
#import re
from workbook_template_CRUD import Get_workbook_template
from workbook_template_CRUD import Form_PII_string

def maskPII(csvfilepath, outputcsvfilepath, columns=['FirstName','LastName','SSN','DOB'], operation='mask'):
  # opens csvfile, mask\delete contents of the data in the specified columns and output the file with the masked data
  # Effectively adds double quotes to all fields.
  ci=[]  # column indexes of the fieldnames in columns
  with open(csvfilepath,"r") as source:
    rdr= csv.reader( source, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    fieldnames=next(rdr)
    for fi,f in enumerate(fieldnames):
      for c in columns:
          if f.upper()==c.upper():   # Case in-sensitive comparison of column names
            ci.append(fi)
    print(fieldnames)
    print(ci)
    
    with open(outputcsvfilepath,"w", newline='') as result:
        wtr= csv.writer( result , delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        wtr.writerow(fieldnames)
        for r in rdr:
            for i in ci:
              r[i]='3333'  # This is masking
            wtr.writerow(r)

def testre(x,mci):
  str = x
  x = re.split(",", str)
  print(x)
  for y in mci:
     print(x[y])
     if x[y][0]=='"':
       x[y]="\"***\""
     else:
       x[y]=0
  # print(x)	
  # for i in x:
    # print(type(i))
    # if type(i)=="<class 'str'>":
      # i=i[1:-1]
      # print(i)
  print(x)
  #csv.register_dialect('csv1', delimiter=',', quoting=csv.QUOTE_NONE, doublequote=False)
  # with open("testout1.txt","w") as result:
    # wtr= csv.writer(result , delimiter=',', quoting=csv.QUOTE_MINIMAL, doublequote=False) 
    # wtr.writerow(x)  
   
def testsplit():
   template_data=Get_workbook_template(file='Demographics_Report2019_12.twbx')
   print(template_data)
   PII1_fname=template_data['PII1'].split('=')[1].split('(')[0]
   print(PII1_fname)
   f1=template_data['PII1'].split('=')[1].split('(')[1].strip('()').split(',')
   for i,f1i  in enumerate(f1):
     f1[i]=f1i.strip('\'') 
   PII1_fieldnames=f1
   
   print(f1)
	
#testsplit()
#print(Form_PII_string(1,'Client.csv','FirstName','LastName','SSN','DOB',''))
#testre("The,\"rain\",5,in,\"Spa,in\",,,heavy",[1,3])