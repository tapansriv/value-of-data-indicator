x=$1

scp ~/.ssh/id_rsa $x:/home/ubuntu/.ssh
scp chameleon_vimrc $x:/home/ubuntu/.vimrc
scp ~/.aws/config ~/.aws/credentials $x:/home/ubuntu/.aws/
scp build.sh $x:/home/ubuntu/
# 
# ssh aws 'git clone git@github.com:tapansriv/s3-column-cache.git'
