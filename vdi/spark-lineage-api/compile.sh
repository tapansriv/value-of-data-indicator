VANILLA_JAR="$HOME/spark-vanilla.jar"
BARE_JAR="$HOME/spark-bare-listener.jar"
NOWRITE_JAR="$HOME/spark-query-api-no-write.jar"
FULL_JAR="$HOME/spark-lineage-api.jar"
REGISTER_JAR="$HOME/spark-listener-just-register.jar"
RG_JAR="$HOME/spark-rowgroup.jar"

BASEDIR="listener_versions_new"

VANILLA_FILE="$BASEDIR/LineageAPI_vanilla.scala"
BARE_FILE="$BASEDIR/LineageAPI_bare.scala"
NOWRITE_FILE="$BASEDIR/LineageAPI_nowrite.scala"
FULL_FILE="$BASEDIR/LineageAPI.scala"
REGISTER_FILE="$BASEDIR/LineageAPI_bare_just_register.scala"
RG_FILE="$BASEDIR/LineageAPI_rgs.scala"



cp $VANILLA_FILE src/main/scala/LineageAPI.scala
mvn clean package
cp target/spark-rowgroup-listener-1.0.0.jar $VANILLA_JAR

cp $BARE_FILE src/main/scala/LineageAPI.scala
mvn clean package
cp target/spark-rowgroup-listener-1.0.0.jar $BARE_JAR

cp $NOWRITE_FILE src/main/scala/LineageAPI.scala
mvn clean package
cp target/spark-rowgroup-listener-1.0.0.jar $NOWRITE_JAR

cp $FULL_FILE src/main/scala/LineageAPI.scala
mvn clean package
cp target/spark-rowgroup-listener-1.0.0.jar $FULL_JAR

cp $REGISTER_FILE src/main/scala/LineageAPI.scala
mvn clean package
cp target/spark-rowgroup-listener-1.0.0.jar $REGISTER_JAR

cp $RG_FILE src/main/scala/LineageAPI.scala
mvn clean package
cp target/spark-rowgroup-listener-1.0.0.jar $RG_JAR


