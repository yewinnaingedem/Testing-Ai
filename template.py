import os 
from pathlib import Path 
import logging 

logging.basicConfig(level=logging.INFO , format='[%(asctime)s]: %(messsage)s:')

list_of_files = [
    'src/__init__.py',
    'src/helper.py' ,
    'src/prompt.py',
    '.env' ,
    'setup.py',
    'app.py' ,
    'research/trials.ipynb',
    'test.py'
]

for filePath in list_of_files : 
    filePath = Path(filePath) 
    fileDir , fileName = os.path.split(filePath)
    
    if fileDir != "" : 
        os.makedirs(fileDir , exist_ok=True )
        logging.info(f"Creating directory ; {fileDir} for the file : {fileName}")
    if(not os.path.exists(filePath)) or (os.path.getsize(filePath) == 0) : 
        with open (filePath , 'w') as f : 
            pass 
            logging.info(f"Creating the file: {filePath}")
    
    else: 
        logging.info(f"{filePath} already exists")
        