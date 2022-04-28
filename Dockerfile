FROM debian:bullseye

ENV DCM4CHE_VERSION=5.24.1
ENV DCM2NIIXTAG v1.0.20210317
ENV HEUDICONVTAG v0.5.4
ENV BIDSTAG 1.2.5
ENV PYDEFACETAG v1.1.0
ENV TAR2BIDSTAG v0.1.0

RUN apt-get update \
    && apt-get install -y -q --no-install-recommends \
        default-jre=2:1.11-72 \
        git=1:2.30.2-1 \
        git-annex=8.20210223-2 \
        python3=3.9.2-3 \
        python3-pip=20.3.4-4+deb11u1 \
        python3-setuptools=52.0.0-4 \
        python-is-python3=3.9.2-1 \
        ssh=1:8.4p1-5 \
        unzip=6.0-26 \
        wget=1.21-1+deb11u1 \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && pip install --upgrade --no-cache-dir pip==22.0.4 \
    && sed -i 's/TLSv1.1, //g' /etc/java-11-openjdk/security/java.security \
    && mkdir /apps

WORKDIR /apps/DicomRaw
RUN git clone https://gitlab.com/cfmm/DicomRaw . \
    && git checkout 00256d486fc790da4fa852c00cb27f42e77b1a99 \
    && pip install --no-cache-dir pydicom==1.4.2 zipstream==1.1.4

WORKDIR /apps/cfmm2tar
RUN git clone https://github.com/khanlab/cfmm2tar.git . \
    && git checkout v1.0.0 \
    && chmod a+x ./*.py \
    && bash install_dcm4che_ubuntu.sh /apps/dcm4che \
    && echo '1.3.12.2.1107.5.9.1:ImplicitVRLittleEndian;ExplicitVRLittleEndian' >> /apps/dcm4che/dcm4che-${DCM4CHE_VERSION}/etc/getscu/store-tcs.properties \
    && echo 'EnhancedMRImageStorage:ImplicitVRLittleEndian;ExplicitVRLittleEndian' >> /apps/dcm4che/dcm4che-${DCM4CHE_VERSION}/etc/getscu/store-tcs.properties \
    && sed -i -e 's/shell=True)/shell=True, universal_newlines=True)/g' /apps/cfmm2tar/Dcm4cheUtils.py \
    && sed -i -e 's/return tar_full_filenames + attached_tar_full_filenames/return list(tar_full_filenames) + attached_tar_full_filenames/g' /apps/cfmm2tar/DicomSorter.py \
    && sed -i -e 's/dataset\.PatientName/str(dataset\.PatientName)/g' /apps/cfmm2tar/sort_rules.py
ENV OTHER_OPTIONS='--tls-aes'

RUN apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
        ca-certificates=20210119 \
        git=1:2.30.2-1 \
        libopenblas-dev=0.3.13+ds-3 \
        libxml2-dev=2.9.10+dfsg-6.7+deb11u1 \
        locales=2.31-13+deb11u3 \
        nodejs=12.22.5~dfsg-2~11u1 \
        npm=7.5.2+ds-2 \
        parallel=20161222-1.1 \
        pigz=2.6-1 \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && mkdir /apps/dcm2niix \
    && wget -q -O /apps/dcm2niix/dcm2niix.zip https://github.com/rordenlab/dcm2niix/releases/download/${DCM2NIIXTAG}/dcm2niix_lnx.zip \
    && unzip /apps/dcm2niix/dcm2niix.zip -d /apps/dcm2niix \
    && rm /apps/dcm2niix/dcm2niix.zip \
    && pip install --no-cache-dir \
        heudiconv==${HEUDICONVTAG} \
        networkx==2.0 \
        pytest==3.6.0 \
    && npm install -g bids-validator@${BIDSTAG} \
    && echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen \
    && echo "LANG=en_US.UTF-8" > /etc/locale.conf \
    && echo "LC_ALL=en_US.UTF-8" >> /etc/locale.conf \
    && locale-gen en_US.UTF-8 \
    && git clone https://github.com/poldracklab/pydeface /apps/pydeface \
    && git -C /apps/pydeface checkout ${PYDEFACETAG} \
    && git clone https://github.com/khanlab/tar2bids.git /apps/tar2bids \
    && git -C /apps/tar2bids checkout ${TAR2BIDSTAG}

ENV FSLDIR /apps/fsl
ENV FSLOUTPUTTYPE NIFTI_GZ
RUN mkdir -p $FSLDIR/bin \
    && wget -q -O $FSLDIR/bin/flirt https://www.dropbox.com/s/3wf2i7eiosoi8or/flirt \
    && wget -q -O $FSLDIR/bin/fslorient https://www.dropbox.com/s/t4grjp9aixwm8q9/fslorient \
    && chmod a+x $FSLDIR/bin/*

WORKDIR /apps/pydeface
RUN python3 setup.py install

ENV PYTHONPATH $PYTHONPATH:/apps/tar2bids/heuristics
ENV LANGUAGE "en_US.UTF-8"
ENV LC_ALL "en_US.UTF-8"
ENV LANG "en_US.UTF-8"

WORKDIR /src
COPY . .

RUN pip install --no-cache-dir -r requirements.txt \
    && keytool -noprompt -importcert -trustcacerts -alias orthanc -file ./compose/orthanc-crt.pem -keystore /apps/dcm4che/dcm4che-5.24.1/etc/certs/newcacerts.p12 -storepass secret -v \
    && keytool -noprompt -importcert -trustcacerts -alias orthanc -file ./compose/orthanc-crt.pem -keystore /apps/dcm4che/dcm4che-5.24.1/etc/certs/newcacerts.jks -storepass secret -v \
    && keytool -noprompt -importcert -trustcacerts -alias mycert -file ./compose/dcm4che-crt.pem -keystore /apps/dcm4che/dcm4che-5.24.1/etc/certs/newkey.p12 -storepass secret -v \
    && keytool -noprompt -importcert -trustcacerts -alias mycert -file ./compose/dcm4che-crt.pem -keystore /apps/dcm4che/dcm4che-5.24.1/etc/certs/newkey.jks -storepass secret -v \
    && mv /apps/dcm4che/dcm4che-5.24.1/etc/certs/newcacerts.p12 /apps/dcm4che/dcm4che-5.24.1/etc/certs/cacerts.p12 \
    && mv /apps/dcm4che/dcm4che-5.24.1/etc/certs/newcacerts.jks /apps/dcm4che/dcm4che-5.24.1/etc/certs/cacerts.jks \
    && mv /apps/dcm4che/dcm4che-5.24.1/etc/certs/newkey.p12 /apps/dcm4che/dcm4che-5.24.1/etc/certs/key.p12 \
    && mv /apps/dcm4che/dcm4che-5.24.1/etc/certs/newkey.jks /apps/dcm4che/dcm4che-5.24.1/etc/certs/key.jks \
    && cat ./compose/orthanc-crt.pem >> /apps/dcm4che/dcm4che-5.24.1/etc/cacerts.pem \
#    && echo "Host ria" >> /etc/ssh/ssh_config \
#    && echo "    Port 2222" >> /etc/ssh/ssh_config \
    && echo "[ria]:2222 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDrYOPbWqP1my/WUP3KEX57u2PpUMgyLjUek5jKCXcAvDufE2oj/mO4rqSDlIGSgaxkStN+vaWDasTA1jHJsYOlUTqoiTx7oO3HetDClcIhqSjZtqEs2BVPBd3IoelAVC+JYLOOcea3Tvb+6rhnZMHgpyGmAqzZxuEiflAvcwAbBBXugok1hTbNJ8mUk6n23AFUHW3srfPuOV1Pi2CCyuHJHrAJIcUr5ZV3HWfF54s3MZXFq8mjiOULulQIyZHYMJ5MhcSY8qJKX61mikMYcoETa3/OuD3505HRxy3tcawV0epRyw3useOBr13gvKkregJakMeKWIb8rONWiubkYcsbFrMj108XRuNmwYQWN1YT7D4yOFuAw/4v0qx8bVZ2yp9cbIKSa8JD4c7EkUUdtop+wjM6NEpyvhFwD1V54/5gEaEtFCEvg4e6IUTZ0zHfac1Cx6uvms47iJ38+c5R+l9/F8z2/ieBV6C0QO6pOAHTqeeRm9dKNnIYt7087FVGb3E=" >> /etc/ssh/ssh_known_hosts \
    && git config --system user.name "Autobids Portal" \
    && git config --system user.email "autobids@dummy.com"

ENV PATH=/apps/tar2bids:$FSLDIR/bin:/apps/dcm2niix:/apps/dcm4che/dcm4che-${DCM4CHE_VERSION}/bin:/apps/DicomRaw:/apps/cfmm2tar:$PATH
ENV _JAVA_OPTIONS="-Xmx2048m"

CMD ["flask", "run", "--host=0.0.0.0"]
