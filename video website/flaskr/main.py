import os
from app import app
import urllib.request
from flask import Flask, flash, request, redirect, url_for, send_from_directory, render_template
from werkzeug.utils import secure_filename
import bckend, sys

@app.route('/boo')
def download_file():
    print("in here", file = sys.stderr, flush = True)
    return send_from_directory('static/outputfile/',
                               "out.musicxml", as_attachment=True)
   



@app.route('/')
def upload_form():
	return render_template('upload.html')

@app.route('/', methods=['POST']) #dictates what loads with the url is just "/"
def upload_video():
	if 'file' not in request.files: 
		flash('No file part')
		return redirect(request.url)
	file = request.files['file']
	if file.filename == '':
		flash('No image selected for uploading')
		return redirect(request.url)
	if file.filename[-4:] != ".mp4": 
		flash('Not the correct filetype')
		return redirect(request.url)
	else:
		filename = secure_filename(file.filename)
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		
		keyFrame = request.form.get("keyFrame")
		noteFrame = request.form.get("noteFrame")
		lastNote = request.form.get("lastNote")
		tempo = request.form.get("tempo")
		key = request.form.get("key")
		title = request.form.get("title")
		composer = request.form.get("composer") 
		noteThreshold = request.form.get("noteThreshold")
		
		print("inputs", filename, keyFrame, noteFrame, lastNote, tempo, key, 
            title, composer, noteThreshold)

		if (keyFrame == ""): keyFrame = "0:00"
		if (noteFrame == ""): noteFrame = "0:00"
		if (lastNote == ""): lastNote = "0:00"
		if (tempo == ""): tempo = -1
		if (key == ""): key = 0
		if (title == ""): title = "il Vento D'oro" 
		if (composer == ""): composer = "Yugo Kanno"  
		if (noteThreshold == ""): noteThreshold = 60

		# backend.hi(filename, keyFrame, noteFrame, lastNote, tempo, key, 
        #     title, composer, keyThreshold, keyLen, noteBuf,
        #     noteYRange, noteThreshold)
		
		bckend.main(filename, 0, 4500, 34000, -1, 0, 
            title, composer, noteThreshold)

  
		print("10 almost done")
		return render_template('/boo.html', filename="out.musicxml" )
 
 

if __name__ == "__main__":
    print("run 2")
    app.run(debug = True)

 