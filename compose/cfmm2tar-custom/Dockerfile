FROM khanlab/cfmm2tar:v1.1.1

RUN echo '1.3.12.2.1107.5.9.1:ImplicitVRLittleEndian;ExplicitVRLittleEndian' >> "/opt/dcm4che-${DCM4CHE_VERSION}/etc/getscu/store-tcs.properties" \
    && echo 'EnhancedMRImageStorage:ImplicitVRLittleEndian;ExplicitVRLittleEndian' >> "/opt/dcm4che-${DCM4CHE_VERSION}/etc/getscu/store-tcs.properties" \
    && sed -i -e 's/shell=True)/shell=True, universal_newlines=True)/g' /apps/cfmm2tar/Dcm4cheUtils.py \
    && sed -i -e 's/return tar_full_filenames + attached_tar_full_filenames/return list(tar_full_filenames) + attached_tar_full_filenames/g' /apps/cfmm2tar/DicomSorter.py \
    && sed -i -e 's/dataset\.PatientName/str(dataset\.PatientName)/g' /apps/cfmm2tar/sort_rules.py

COPY . /opt/certs

WORKDIR /opt/certs

RUN keytool -noprompt -importcert -trustcacerts -alias orthanc -file ./orthanc-crt.pem -keystore /opt/dcm4che-5.24.1/etc/certs/newcacerts.p12 -storepass secret -v \
    && keytool -noprompt -importcert -trustcacerts -alias orthanc -file ./orthanc-crt.pem -keystore /opt/dcm4che-5.24.1/etc/certs/newcacerts.jks -storepass secret -v \
    && keytool -noprompt -importcert -trustcacerts -alias mycert -file ./dcm4che-crt.pem -keystore /opt/dcm4che-5.24.1/etc/certs/newkey.p12 -storepass secret -v \
    && keytool -noprompt -importcert -trustcacerts -alias mycert -file ./dcm4che-crt.pem -keystore /opt/dcm4che-5.24.1/etc/certs/newkey.jks -storepass secret -v \
    && mv /opt/dcm4che-5.24.1/etc/certs/newcacerts.p12 /opt/dcm4che-5.24.1/etc/certs/cacerts.p12 \
    && mv /opt/dcm4che-5.24.1/etc/certs/newcacerts.jks /opt/dcm4che-5.24.1/etc/certs/cacerts.jks \
    && mv /opt/dcm4che-5.24.1/etc/certs/newkey.p12 /opt/dcm4che-5.24.1/etc/certs/key.p12 \
    && mv /opt/dcm4che-5.24.1/etc/certs/newkey.jks /opt/dcm4che-5.24.1/etc/certs/key.jks \
    && cat ./orthanc-crt.pem >> /opt/dcm4che-5.24.1/etc/cacerts.pem \
    && echo "[ria]:2222 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDrYOPbWqP1my/WUP3KEX57u2PpUMgyLjUek5jKCXcAvDufE2oj/mO4rqSDlIGSgaxkStN+vaWDasTA1jHJsYOlUTqoiTx7oO3HetDClcIhqSjZtqEs2BVPBd3IoelAVC+JYLOOcea3Tvb+6rhnZMHgpyGmAqzZxuEiflAvcwAbBBXugok1hTbNJ8mUk6n23AFUHW3srfPuOV1Pi2CCyuHJHrAJIcUr5ZV3HWfF54s3MZXFq8mjiOULulQIyZHYMJ5MhcSY8qJKX61mikMYcoETa3/OuD3505HRxy3tcawV0epRyw3useOBr13gvKkregJakMeKWIb8rONWiubkYcsbFrMj108XRuNmwYQWN1YT7D4yOFuAw/4v0qx8bVZ2yp9cbIKSa8JD4c7EkUUdtop+wjM6NEpyvhFwD1V54/5gEaEtFCEvg4e6IUTZ0zHfac1Cx6uvms47iJ38+c5R+l9/F8z2/ieBV6C0QO6pOAHTqeeRm9dKNnIYt7087FVGb3E=" >> /etc/ssh/ssh_known_hosts \
    && echo "[ria]:2222 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC+xIp6UpeOg1k446jCi5A/qgj6tx/vczhapukCejDf1N9YgCEWBca+nRdGRL4+gjCoDxPqgURu8ua3HXIMYqt74Tc/5ZK0bP4/7746X5ZBRFpv92gYKOunQBMkcnt2XUUDJ7TCE1VDnRJJyEcnGrGvgZBua8yvuCX3vhxCP2ODWoj32JD+f40fFzEtObcrecDCdre4IGn/QSvFzyrtUj0nrO8iSOdq7kp0mJZTPLSC447IlCA/KDTAJ5MBCG/ViHAenb0e3hjWRsiAuh9XnhqzwLd/f/XqD1ABK5iPYCvYUi1bfEJKFVuVWqF+/4IdGrB98ukA6KyuNrNe3AGYcTo5nABPiQ2AAC9p+UroQQY2DzZJ1nRwLFKU9BJSgoscZsiNxDb/8RjR+z8jiLEdp8HqhUsDIDbVA6V2f8vUxiKM4oZ/J/1HMczuQ81gQLKGvbbEnw4EOrHJKPYWm0U6c8F1sFr35a3gHFzW+cbkiihS9oDnLffPui6/3ULpTyVmNV0=" >> /etc/ssh/ssh_known_hosts \
    && echo "[archive]:2222 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDY5Gal7/Z9LfGvPhLy4PMZDsmq7KqFeFajUtbkMf/1ISa/qhxZdidjB6cZeRIjuWxrmeMVGki5GSHjc3oKmJsf7cA6Rw2P7r09F+hXCuMja+svzhRPn3Tqn0ekV7XknZvcOP2iAOExWJm0WZ+KhcVN/ONERvzdHosFiOHvtva+tLw3LVrKlzVRIVv1fafTlJtjOiX0Z3JOsJvMtmqtxTBEIgfp4OogZWNWwCaeT+bSyhICcc/rwHrIQ3ieuTuX9KLIi/sT5H0a3NssqzSCQECTvnAk1/RN/oke/K+BcI3GALyc/d/669+k2YGR4fq+Sm2tWPiaO8QfqUlw2FE5JGXCzj0GydpVpN+eOaN7n9QiwvwNkzoYEKK8FTqGRvJjjCIxwIQn8Z3j2oIt6/waojGhfQjxGDgQ6uEQw03FAMf1LrJ0E5M1VhXasgBa9sUtFO0eQTP798HmOoU8V7juDHIJq5iLr4mdcN3r7csclJBulxgopt4nWTveguSSDVVq4o8=:" >> /etc/ssh/ssh_known_hosts \
    && echo "[archive]:2222 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBF+1JZEYWiq86LUdVvmdiw6NoQN2yeon+ioxkVutYp8wVv2SExRKDoB61eiKMTRR3A59ncCawYK1ziMFeLr6aXA=" >> /etc/ssh/ssh_known_hosts \
    && echo "[archive]:2222 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHkOjP+rdG2n1VikNnwhPVNQbuU8psJnaZWC2lVpsW9C" >> /etc/ssh/ssh_known_hosts
