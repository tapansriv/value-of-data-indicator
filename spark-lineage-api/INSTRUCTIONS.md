# Instructions to Access Nodes, Build Libraries, and Run Experiments for Spark
A list of instructions for how to SSH onto chameleon nodes with sufficient disk
space to store data, build the custom parquet-java and spark builds, and run
overhead experiments for the spark-lineage value of data metric collector
against TPC-H and TPC-DS queries (and some custom queries written on the same
data models)

## Nodes
### Access
There are two nodes currently allocated on Chameleon that accept the
tapan-soham.pem private key at IP `129.114.108.68` and IP `129.114.108.156`. The
following is lines to put in your `.ssh/config` file that would enable you to
ssh onto these nodes via `ssh spark` or `ssh spark2`. Modify whatever you need,
including the IdentityFile path, to suit your setup.

```
Host spark
    User cc
    HostName 129.114.108.68
    HostKeyAlias spark
    IdentityFile ~/tapan-soham.pem

Host spark2
    User cc
    HostName 129.114.108.156
    HostKeyAlias spark2
    IdentityFile ~/tapan-soham.pem
```

### Format and Mount Disks
If you're using extra disks that are attached to the machine rather than the
default disk that's mounted to /, you can use these instructions to setup a
disk. 

To see what disks are available to be mounted, run 
`sudo lsblk`
Which should return something that looks like the following:
```
NAME                              MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
sda                                 8:0    0 372.6G  0 disk
├─sda1                              8:1    0   550M  0 part /boot/efi
├─sda2                              8:2    0     8M  0 part
└─sda3                              8:3    0 372.1G  0 part /
sdb                                 8:16   0   1.8T  0 disk
sdc                                 8:32   0   1.8T  0 disk
sdd                                 8:48   0   1.8T  0 disk 
sde                                 8:64   0   1.8T  0 disk 
sdf                                 8:80   0   1.8T  0 disk
sdg                                 8:96   0   1.8T  0 disk
sdh                                 8:112  0   1.8T  0 disk
sdi                                 8:128  0   1.8T  0 disk
sdj                                 8:144  0   1.8T  0 disk
└─sdj1                              8:145  0     1T  0 part
sdk                                 8:160  0   1.8T  0 disk
sdl                                 8:176  0   1.8T  0 disk
sdm                                 8:192  0   1.8T  0 disk
├─sdm1                              8:193  0   522G  0 part
├─sdm2                              8:194  0   522G  0 part
├─sdm3                              8:195  0   522G  0 part
└─sdm4                              8:196  0   522G  0 part
sdn                                 8:208  0   1.8T  0 disk
├─sdn1                              8:209  0   522G  0 part
├─sdn2                              8:210  0   522G  0 part
├─sdn3                              8:211  0   522G  0 part
└─sdn4                              8:212  0   522G  0 part
sdo                                 8:224  0   1.8T  0 disk
sdp                                 8:240  0   1.8T  0 disk
sdq                                65:0    0   1.8T  0 disk
```

`/dev/sda` is the disk that's mounted to /, and where things like the home
directory are stored. As you can see, in this example it's only got about 375G
of storage, whereas we have lots of 1.8TB disks that can be used.

We first want to format the disk (for ubuntu, we'll use ext4), then mount it to
a location in the filesystem. I'll use `/mnt/disks/psql` as the directory, but
it can be anywhere. Typically all mounted directories are under `/mnt`. 

```bash
sudo mkfs -t ext4 /dev/sdb # formats /dev/sdb as ext4
sudo mkdir -p /mnt/disks/psql
sudo mount /dev/sdb /mnt/disks/psql
sudo chown cc: /mnt/disks/psql # makes it so user CC owns the directory and all contents, even tho it was made by root
```

If you run `sudo lsblk` again you should see this mount reflected:
```
NAME                              MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
sda                                 8:0    0 372.6G  0 disk
├─sda1                              8:1    0   550M  0 part /boot/efi
├─sda2                              8:2    0     8M  0 part
└─sda3                              8:3    0 372.1G  0 part /
sdb                                 8:16   0   1.8T  0 disk /mnt/disks/psql
. . .d
```

## Build Libraries

### Repo links
To clone the custom `parquet-java` and `spark` repos, run the following: 

```bash
git clone git@github.com:tapansriv/parquet-java.git
cd parquet-java
git switch vod_rg

git clone git@github.com:tapansriv/spark.git
cd spark
git switch rowgroup-dev
```

You can use `git branch` to check current branch. 

### How to build each library
First build parquet-java, then spark (since spark depends on parquet-java). The
README_rg or README_rg.md files should have instructions, but they'll be written
here as well. 

Once cloned and branches are switched to, do the following for parquet-java: 


```
wget -nv http://archive.apache.org/dist/thrift/0.16.0/thrift-0.16.0.tar.gz
tar xzf thrift-0.16.0.tar.gz
cd thrift-0.16.0
chmod +x ./configure
./configure --disable-libs
sudo make install
cd ..
MAVEN_OPTS="--add-opens java.base/java.lang=ALL-UNNAMED" mvn clean install -pl parquet-hadoop -DskipTests
```
Maven opts because we compiled the Parquet-Hadoop library this way to enable reflection despite running on Java 17--possibly a hack, but working for now


To build Spark:
Run this to install Scala 2.13 (directions from [here](https://spark.apache.org/docs/3.5.0/building-spark.html#change-scala-version)).
```
curl -fL https://github.com/coursier/coursier/releases/latest/download/cs-x86_64-pc-linux.gz | gzip -d > cs && chmod +x cs && ./cs setup
cs install scala:2.13.16 && cs install scalac:2.13.16
```
In case there are issues, reference these links:
[here](https://www.scala-lang.org/download/2.13.16.html) and
[here](https://docs.scala-lang.org/getting-started/index.html#using-the-scala-installer-recommended-way).


Then need to make sure javac is also installed along with java 17. Run `sudo apt install openjdk-17-jdk-headless` to install javac in the correct folder as well.

You might need to run `sudo update-alternatives --config java` to set the Java
version to 17 from 21. 

Run `./dev/change-scala-version.sh 2.13`
Before running `./build/mvn -DskipTests -Pscala-2.13 clean install`


Finally, within the main `value-of-data-metric/spark-lineage-api` repo, run `./compile.sh` to compile all the different Lineage API versions and copy them to `$HOME`  

If you want to change how many iterations are run, look at the files within
`listener_versions_new` and change the 9 in the loop to whatever value (start
with 3) before running compile.

### How to clear old installations
All maven installs are installed under `$HOME/.m2/repository`. These will be
installed at `org/apache/parquet/parquet-hadoop` and `org/apache/spark/`. I'd
just delete both directories (maybe `org/apache/parquet` entirely) to clear out
the previous install. 

## How to Run Experiments
Within `spark-lineage-api/benchmarking` run the `run_test.sh` script, which will
launch all the listeners (already compiled in a previous step in the home
directory). Modify this file if you want to change what datasets are run (i.e.
tpcds, tpch) to like run tpcds on one node, tpch on another, etc. 


## Potential Roadblocks Running at 1TB
- OOM for some queries possibly on spark causing jars to crash. Need to monitor
  and at minimum exclude query from run
- Usage log size overfills disk (put on its own disk)


















