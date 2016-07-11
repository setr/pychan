# pychan
simple static-chan using python3 and sqlite

virtualenv -p python3 testchan 
source testchan/bin/activate.sh 
pip3 install -r requirements.txt 
export FLASK_APP=testchan.py
export FLASK_DEBUG=1
flask run

then go to localhost:5000
