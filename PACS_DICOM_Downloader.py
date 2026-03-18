
"""
Created on Wed Mar 18 10:10:07 2026, @author: lydia.lim

___________OVERVIEW:____________
    
Download MRI DICOM studies from PACS using a CSV list of accession numbers.

Inputs:
- CSV file containing accession numbers
- PACS AE title, IP and port
- Local AE title recognised by PACS

Outputs:
- One folder per accession number under BASE_SAVE_DIR
- Series-level subfolders containing .dcm files
- Log file of retrieval progress and errors


_______NOTES:_______________________

- Uses C-FIND to get StudyInstanceUID from accession number
- Uses C-GET to retrieve DICOM files
- Currently configured for MR Image Storage
___________________________________
"""

import time
import os
import pandas as pd 
from datetime import datetime
from pynetdicom import AE, evt, build_role
from pynetdicom.sop_class import (
    StudyRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelGet,
    MRImageStorage
)
from pydicom.dataset import Dataset

#Imaging archive's networking info (ask your PACs manager)
REMOTE_AE = "EXAMPLESCP"
REMOTE_IP = "00.000.00.00"
REMOTE_PORT = 104

#Your local machine's networking info (ask your PACs manager to allow this AE Title for calling)
LOCAL_AE = "CIMQRTOOL"


#File path where want images saved:
BASE_SAVE_DIR = "H:/NM/Research/Vestibular Schwannoma Research Project (Lydia Lim)/Positive"
CURRENT_ACCESSION_DIR = None

#.csv file and path for patient accession numbers (ensure csv contains no headers)
Accession_list_path= "C:/Users/lydia.davidson/.spyder-py3/Excels/acc_numb.csv"

SLEEP_BETWEEN_STUDIES_S = 0.2
RETRY_ON_FAIL = 1
LOGFILE = "batch_retrieve_log.txt"
role = build_role(MRImageStorage, scp_role=True) #Allows us to switch from SCU to SCP for the c-get (SCU for query and SCP for C-store)

#Log fn for date/time and record of success/failiure of 
def log(msg: str):
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

#fn to avoid crashes due to folder name being named after series description tag, where invalid windows folder naming conventions may be otherwise triggered
def safe_folder_name(name: str) -> str:
    bad_chars = '<>:"/\\|?*'
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name.strip()

# Handler function to allow SCU (us) to handle the saving of the .dcms when we receive them. Section also managed sub-folder structure
def handle_store(event):
    """Handle a C-STORE request event."""
    global CURRENT_ACCESSION_DIR
    
    ds = event.dataset
    ds.file_meta = event.file_meta
    
    if CURRENT_ACCESSION_DIR is None:
        raise RuntimeError("CURRENT_ACCESSION_DIR is not set before C-STORE")
    
    os.makedirs(CURRENT_ACCESSION_DIR, exist_ok=True)
    
  
    series_desc = safe_folder_name(getattr(ds, "SeriesDescription", "unknown_series"))
    series_dir = os.path.join(CURRENT_ACCESSION_DIR, f"{series_desc}")
    os.makedirs(series_dir, exist_ok=True)
    
    sop_uid = ds.SOPInstanceUID
    filename = os.path.join(series_dir, f"{sop_uid}.dcm")
    ds.save_as(filename, enforce_file_format=True)
    

    # Return a 'Success' status
    return 0x0000

handlers = [(evt.EVT_C_STORE, handle_store)]

#CFIND to get back certain dcm tag (Study UID) given a certain accession number as input. 
#This step is because cget fn below needs Study UID as input and not accession numbers 
def cfind_study_uids(ae: AE, accession: str) -> list[str]:
    ds = Dataset()                                #Makes an empty DICOM dataset to store tags 
    ds.QueryRetrieveLevel = "STUDY"
    ds.AccessionNumber = accession                #match on accession number
    ds.StudyInstanceUID = ""                      #request StudyInstanceUID back (blank value= return this tag)

    assoc = ae.associate(REMOTE_IP, REMOTE_PORT, ae_title=REMOTE_AE)
    if not assoc.is_established:
        raise RuntimeError("Association failed (C-FIND)")

    uids = []
    for status, identifier in assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind):
        if status and status.Status in (0xFF00, 0xFF01) and identifier:
            uid = getattr(identifier, "StudyInstanceUID", None)
            if uid:
                uids.append(str(uid))

    assoc.release()

    # remove any duplicates
    seen = set()
    out = []
    for u in uids:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


#C-GET function to retrieve .dcm file from remote AE back to us via this connection we established
def cget(ae: AE, study_uid: str, accession: str) -> int:
    global CURRENT_ACCESSION_DIR

    CURRENT_ACCESSION_DIR = os.path.join(BASE_SAVE_DIR, accession)
    ds = Dataset()
    ds.QueryRetrieveLevel = "STUDY"
    ds.StudyInstanceUID = study_uid
    
    assoc = ae.associate(REMOTE_IP, REMOTE_PORT, ae_title=REMOTE_AE, ext_neg=[role], evt_handlers=handlers)
    if not assoc.is_established:
        raise RuntimeError("Association failed (C-GET)")
        
    final_status = None
    for status, _ in assoc.send_c_get(ds, query_model=StudyRootQueryRetrieveInformationModelGet):
        if status:
            final_status = status.Status

    assoc.release()
    return final_status if final_status is not None else -1

def main():
    
    ae = AE(ae_title=LOCAL_AE)
    #presentation contexts (DICOM handshake)
    ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)     
    ae.add_requested_context(StudyRootQueryRetrieveInformationModelGet)
    ae.add_requested_context(MRImageStorage)
    
    df = pd.read_csv(Accession_list_path, header=None)
    accessions = (
        df[0]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .tolist()
    )
    log(f"Starting batch for {len(accessions)} accessions")

    for i, acc in enumerate(accessions, start=1):
        log(f"[{i}/{len(accessions)}] Accession {acc}")
        

        # C-FIND with a second retry if there was an error first time around
        for attempt in range(RETRY_ON_FAIL + 1):
            try:
                uids = cfind_study_uids(ae, acc)
                break
            except Exception as e:
                log(f"  C-FIND error (attempt {attempt+1}): {e}")
                if attempt == RETRY_ON_FAIL:
                    uids = []
                else:
                    time.sleep(1)

        if not uids:
            log("  No study found (or C-FIND failed).")
            continue
        # C-Get with a second retry if there was an error first time around
        for uid in uids:
            log(f"  C-GET StudyInstanceUID {uid}")
            for attempt in range(RETRY_ON_FAIL + 1):
                try:
                    status = cget(ae, uid, acc)
                    log(f"    Final C-GET status: 0x{status:04X}" if status >= 0 else "    No status returned")
                    break
                except Exception as e:
                    log(f"    C-Get error (attempt {attempt+1}): {e}")
                    if attempt == RETRY_ON_FAIL:
                        log("    Giving up on this UID.")
                    else:
                        time.sleep(1)

        time.sleep(SLEEP_BETWEEN_STUDIES_S)

    log("Batch complete.")

if __name__ == "__main__":
    main()
