#!/usr/bin/env bash
cd /var/www/
sudo rm -rf pychan
git clone https://github.com/setr/pychan.git
sudo chown -R webdev pychan
sudo chgrp -R www-data pychan
sudo cp ~/pychan.ini pychan/pychan.ini
sudo cp ~/pychan.service /etc/systemd/system/pychan.service
sudo cat pychan/system/ubuntu16/pychan_site.nginx > /etc/nginx/sites-available/pychan
sudo cat pychan/system/ubuntu16/nginx.conf > /etc/nginx/nginx.conf

# add AWS config settings
export AWS_DEFAULT_PROFILE=pychan
echo "aws = True" >> pychan/config.py
echo "S3_BUCKET = 'pychan'" >> pychan/config.py
echo "S3_BUCKET_DOMAIN = 's3-us-west-2.amazonaws.com'" >> pychan/config.py

echo "installing libraries"
cd pychan
mkdir -p static/src/imgs static/src/thumb
virtualenv -p python3 pychanenv
source pychanenv/bin/activate
pip -q install -r requirements.txt

echo "generating template posts/db"
python3 db_meta.py
python3 db_main.py

echo "uploading static files to aws"
aws s3 sync ../pychan/static s3://pychan/static --acl public-read# have to do it again for the files we just created
cd ..
sudo chown -R webdev pychan
sudo chgrp -R www-data pychan

echo "clearing log"
echo '' > /var/log/uwsgi/pychan.log
echo "restarting all daemons"
sudo systemctl restart nginx
sudo systemctl restart pychan
sudo systemctl enable pychan
sudo systemctl daemon-reload