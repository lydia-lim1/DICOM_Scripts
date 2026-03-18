#A python code to extract a DICOM tag (Series Description) from all DICOM files within all subfolders of a defined directory. Saves output as a text file.

import os
import pydicom


my_dir = r"D:\Lydia\SCHXR_sample"   # Paste the folder path to root folder you want to interogate


f = open("SeriesDescriptors.txt", "w")    # Creates new text file where result will be saved

for path, sub_dirs, files in os.walk(my_dir):  #Traverses directory recursively through any/all sub folders
    for file in files:
        if file.endswith(".dcm"):
            file_path = os.path.join(path, file)  #Joins file to path statement
            fn = pydicom.dcmread(file_path)
            a = [file , fn.SeriesDescription]   #Output information want to display (file name and series descr tag)
            print(a)
            f.writelines("%s\n" % a)          #Saves results in text file

            
