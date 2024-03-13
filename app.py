import requests
import pydicom
import os
import shutil
import tempfile
import requests_toolbelt as tb

from io import BytesIO
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

@app.route('/hello', methods=['GET'])
def dicom():
    study_id = request.args.get('study_id')
    token = request.args.get('token')

    url = 'https://scaida-dicom-app-e6f6engddhfqa5g6.z01.azurefd.net/v1/studies/' + study_id

    headers = {'Accept': 'multipart/related; type="application/dicom"; transfer-syntax=*',
               "Authorization": "Bearer {}".format(token)}

    try:
        response = requests.get(url, headers=headers)

        mpd = tb.MultipartDecoder.from_response(response)

        slices = [pydicom.dcmread(BytesIO(part.content)) for part in mpd.parts]

        slices.sort(key=lambda x: float(x.InstanceNumber))
        
        # Create a temporary directory to store the DICOM files
        temp_dir = tempfile.mkdtemp()

        for ds in slices:
            # Get the StudyInstanceUID and SOPInstanceUID from the dataset
            study_uid = ds.StudyInstanceUID
            sop_uid = ds.SOPInstanceUID
            # Create the study folder if it doesn't exist
            study_folder = os.path.join(temp_dir, study_uid)
            os.makedirs(study_folder, exist_ok=True)
            # Set the file name as the SOPInstanceUID with .dcm extension
            file_name = sop_uid + ".dcm"
            # Set the full path to the file
            file_path = os.path.join(study_folder, file_name)
            # Save the dataset to the file
            ds.save_as(file_path)

        # Create a zip file in the temporary directory
        zip_filename = os.path.join(temp_dir, f"{study_id}.zip")
        shutil.make_archive(zip_filename[:-4], 'zip', temp_dir)

        # Return the zip file as a response
        return send_file(zip_filename, as_attachment=True, download_name=f"{study_id}.zip")
    
    except Exception as e:
        # Log the exception and return an error response
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    finally:
        # Cleanup: Remove the temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(debug=True)
