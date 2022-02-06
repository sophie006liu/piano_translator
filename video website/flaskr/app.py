from flask import Flask

UPLOAD_FOLDER = 'static/uploads/' #the alias for where uploads go
DLOAD_FOLDER = 'static/outputfile/' #the alias for where uploads go

app = Flask(__name__)
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 