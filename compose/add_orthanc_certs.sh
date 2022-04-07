for f in $(find /apps/dcm4che/dcm4che-5.24.1/etc -name cacerts.jks -or -name cacerts.p12)
do
  keytool -noprompt -importcert -trustcacerts -alias orthanc -file ./compose/orthanc.crt -keystore "$f" -storepass secret -v
done
