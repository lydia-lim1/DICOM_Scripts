# DICOM_Scripts

This repo contains DICOM-networking (pynetdicom) and DICOM handling (pydicom) based scripts. More explanation/ details for each script in this repo can be found below:

**1) Mass_PACS_Download_Tool.py**

___________OVERVIEW:____________
    
>> Script that downloads scan data in .dcm format from an imaging archive (e.g. PACS) to folder on your computer (path: 'BASE_SAVE_DIR') based on a
list (.csv) of accession numbers. End up with folder per accession number, containing series level sub folders containing the .dcm files.

>> This script is for MRI images, if want other types of images e.g. CT will need to replace 'MRImageStorage' SOP class with an appropriate alterative
e.g. 'CTImageStorage'


_______TIPS:_______________________

You will need to know AE Title ('REMOTE_AE'), IP address ('REMOTE_IP') and port number ('REMOTE_PORT') of the service class provider (e.g PACs)
The local AE Title ('LOCAL_AE') will likely need to be recognised by the SCP, meaning you will likely need to ask your PACs manager to add 
your calling AE Title and workstation for this script to function.

If you use Fuji Synapse PACs and have the QueryRetrieveSCU tool downloaded and configured to PACs already,
you can define 'LOCAL_AE' below as one listed on tool (e.g. 'CIMQRTOOL') 
___________________________________


