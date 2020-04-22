import csv  

def wlog(filepath,function,version,timest,requester,req_id,*rest): 
  fields=[function,version,timest,requester,req_id]
  for r in rest: fields.append(r)
  with open(filepath, 'a') as f:
      writer = csv.writer(f)
      writer.writerow(fields)
	  
def wlogresult(filepath, *rest): 
  with open(filepath, 'a') as f:
      writer = csv.writer(f)
      writer.writerow(rest)