#!/usr/bin/env bash
cd /var/www/
rm -r pychan
git clone https://github.com/setr/pychan.git

chown -R webdev pychan
chgrp -R www-data pychan
#cp ~/pychan.ini pychan/pychan.ini
cp ~/pychan.service /etc/systemd/system/pychan.service
mkdir -p src/imgs src/thumb

cd pychan
virtualenv -p python3 pychanenv
source pychanenv/bin/activate
pip install -r requirements.txt
python3 db_meta.py
python3 db_main.py

# have to do it again for the files we just created
chown -R webdev pychan
chgrp -R www-data pychan

sudo systemctl restart nginx
sudo systemctl restart pychan
sudo systemctl enable pychan
sudo systemctl daemon-reload
