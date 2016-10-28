#!/usr/bin/env bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev nginx ffmpeg \
                         ghostscript libgs-dev imagemagick   \
                         awscli
sudo pip3 install virtualenv
# nginx doesn't know about the gs path; so we need to force imagemagick to use the absolute path of gs
# in order to handle pdf thumbnailing.
sudo sed --in-place=.orig -e '/\(\&quot;\)gs\1/ s_gs_/usr/bin/gs_g' /etc/ImageMagick-6/delegates.xml

sudo chmod a+rwx /var/log/nginx
sudo mkdir /var/log/uwsgi
sudo touch /var/log/uwsgi/pychan.log
sudo chmod a+rwx /var/log/uwsgi/* /var/log/uwsgi

aws configure --profile pychan
aws s3 mb s3://pychan
aws s3api put-bucket-policy -bucket pychan -policy file://bucket-policy.json