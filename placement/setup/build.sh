git clone git@github.com:tapansriv/s3-column-cache.git

sudo apt update
sudo apt install python3.12-venv

python3 -m venv venv
source venv/bin/activate

cd s3-column-cache
pip install -r requirements.txt
pip install -e .
