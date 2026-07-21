#!/bin/bash

cp chameleon_vimrc ~/.vimrc
cd ~

# Clone custom spark and parquet java repos
git clone git@github.com:tapansriv/parquet-java.git
git clone git@github.com:tapansriv/spark.git

# Install Java 17 and Maven
sudo apt install openjdk-17-jdk-headless maven -y 


# Build custom parquet java reader class 
cd parquet-java
git switch vod_rg

# Parquet reader uses Thrift 0.16.0, which is not available via apt-get, so we build from source
wget -nv http://archive.apache.org/dist/thrift/0.16.0/thrift-0.16.0.tar.gz
tar xzf thrift-0.16.0.tar.gz
cd thrift-0.16.0
chmod +x ./configure
./configure --disable-libs
sudo make install
cd ..

# Build parquet-hadoop module only
MAVEN_OPTS="--add-opens java.base/java.lang=ALL-UNNAMED" mvn clean install -pl parquet-hadoop -DskipTests


# Build Spark with custom parquet-java just installed at ~/.m2/repository
cd ../spark
git switch rowgroup-dev

# Install Scala 2.13.16 using coursier
curl -fL https://github.com/coursier/coursier/releases/latest/download/cs-x86_64-pc-linux.gz | gzip -d > cs && chmod +x cs && ./cs setup -y 
source ~/.profile
cs install scala:2.13.16 && cs install scalac:2.13.16

# Change Spark to use Scala 2.13
./dev/change-scala-version.sh 2.13

# Install Spark with Scala 2.13
./build/mvn -DskipTests -Pscala-2.13 clean install
